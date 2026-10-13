"""Base dos repositórios DuckDB: schema derivado das entidades e substituição de partições.

O schema de cada tabela é derivado das anotações da ``dataclass``. Um ``Gap`` vira
duas colunas (``<campo>_segundos`` e ``<campo>_voltas``). Datas são gravadas como
``TIMESTAMP`` em UTC (sem fuso, por contrato) e voltam como ``datetime`` em UTC.

A carga em lote passa por um arquivo JSON Lines temporário lido com ``read_json``:
no DuckDB, essa via é ordens de grandeza mais rápida que ``executemany`` ou listas
passadas como parâmetro, e dispensa pandas/pyarrow.
"""

import json
import logging
import tempfile
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

import duckdb

from f1.domain.tipos import Gap
from f1.domain.validacao import desembrulhar_opcional

logger = logging.getLogger(__name__)

TIPOS_SQL: Mapping[object, str] = {
    int: "INTEGER",
    Decimal: "DECIMAL(18, 3)",
    float: "DOUBLE",
    str: "VARCHAR",
    bool: "BOOLEAN",
    datetime: "TIMESTAMP",
}


def tipo_sql(tipo: object) -> str:
    """Traduz um tipo Python anotado em uma entidade para o tipo de coluna do DuckDB.

    Raises:
        TypeError: Se o tipo não tiver mapeamento (erro de programação).
    """
    tipo, _ = desembrulhar_opcional(tipo)
    if tipo in TIPOS_SQL:
        return TIPOS_SQL[tipo]
    if isinstance(tipo, type) and issubclass(tipo, StrEnum):
        return "VARCHAR"
    if get_origin(tipo) is tuple:
        return f"{tipo_sql(get_args(tipo)[0])}[]"
    raise TypeError(f"tipo sem mapeamento para o DuckDB: {tipo!r}")


@dataclass(frozen=True, slots=True)
class Coluna:
    """Coluna de uma tabela e o campo da entidade que a origina."""

    nome: str
    tipo_sql: str
    campo: str
    tipo_campo: object
    parte_gap: str | None = None


def _para_json(valor: object) -> object:
    if isinstance(valor, datetime):
        return valor.astimezone(UTC).replace(tzinfo=None).isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, tuple):
        return [_para_json(item) for item in valor]
    return valor


def _do_banco(valor: object, tipo: object) -> object:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=UTC)
    if isinstance(tipo, type) and issubclass(tipo, StrEnum):
        return tipo(valor)
    if isinstance(valor, list):
        return tuple(valor)
    return valor


class TabelaDuckDB:
    """Tabela do DuckDB associada a uma entidade de domínio."""

    def __init__(self, nome: str, modelo: type) -> None:
        self.nome = nome
        self.modelo = modelo
        dicas = get_type_hints(modelo)
        colunas: list[Coluna] = []
        for campo in fields(modelo):
            tipo, _ = desembrulhar_opcional(dicas[campo.name])
            if tipo is Gap:
                colunas.append(
                    Coluna(f"{campo.name}_segundos", "DECIMAL(18, 3)", campo.name, tipo, "segundos")
                )
                colunas.append(
                    Coluna(f"{campo.name}_voltas", "INTEGER", campo.name, tipo, "voltas")
                )
            else:
                colunas.append(Coluna(campo.name, tipo_sql(tipo), campo.name, tipo))
        self.colunas = tuple(colunas)

    @property
    def nomes_colunas(self) -> tuple[str, ...]:
        """Nomes das colunas, na ordem dos campos da entidade."""
        return tuple(c.nome for c in self.colunas)

    def ddl(self) -> list[str]:
        """Comandos idempotentes que criam a tabela e acrescentam colunas novas.

        A evolução de schema é só aditiva: um campo novo na entidade vira uma coluna
        nula nas linhas antigas. Remover ou mudar o tipo de um campo exige migração
        manual.
        """
        definicoes = ", ".join(f"{c.nome} {c.tipo_sql}" for c in self.colunas)
        return [
            f"CREATE TABLE IF NOT EXISTS {self.nome} ({definicoes})",
            *(
                f"ALTER TABLE {self.nome} ADD COLUMN IF NOT EXISTS {c.nome} {c.tipo_sql}"
                for c in self.colunas
            ),
        ]

    def para_linha(self, entidade: object) -> dict[str, object]:
        """Converte uma entidade em uma linha serializável em JSON."""
        linha: dict[str, object] = {}
        for coluna in self.colunas:
            valor = getattr(entidade, coluna.campo)
            if coluna.parte_gap is not None:
                valor = getattr(valor, coluna.parte_gap) if valor is not None else None
            linha[coluna.nome] = _para_json(valor)
        return linha

    def da_linha(self, linha: Sequence[object]) -> object:
        """Reconstrói a entidade a partir de uma linha lida na ordem de ``nomes_colunas``."""
        valores: dict[str, object] = {}
        gaps: dict[str, dict[str, object]] = {}
        for coluna, valor in zip(self.colunas, linha, strict=True):
            if coluna.parte_gap is not None:
                gaps.setdefault(coluna.campo, {})[coluna.parte_gap] = valor
            else:
                valores[coluna.campo] = _do_banco(valor, coluna.tipo_campo)
        for campo, partes in gaps.items():
            informadas = {k: v for k, v in partes.items() if v is not None}
            valores[campo] = Gap(**informadas) if informadas else None
        return self.modelo(**valores)


def inserir_jsonl(
    conexao: duckdb.DuckDBPyConnection,
    tabela: str,
    colunas: Sequence[tuple[str, str]],
    linhas: Iterable[Mapping[str, object]],
    diretorio: Path,
) -> int:
    """Insere linhas em ``tabela`` por meio de um arquivo JSON Lines em ``diretorio``.

    Args:
        conexao: Conexão; a transação é responsabilidade do chamador.
        tabela: Nome da tabela (vindo do catálogo do projeto, nunca de entrada externa).
        colunas: Pares ``(nome, tipo_sql)`` das colunas a preencher.
        linhas: Linhas já serializáveis em JSON.
        diretorio: Diretório temporário onde o arquivo é criado.

    Returns:
        Quantidade de linhas inseridas.
    """
    arquivo = diretorio / f"{tabela}.jsonl"
    quantidade = 0
    with arquivo.open("w", encoding="utf-8") as saida:
        for linha in linhas:
            saida.write(json.dumps(linha, ensure_ascii=False))
            saida.write("\n")
            quantidade += 1
    if quantidade == 0:
        return 0
    nomes = ", ".join(nome for nome, _ in colunas)
    estrutura = ", ".join(f"'{nome}': '{tipo}'" for nome, tipo in colunas)
    conexao.execute(
        f"INSERT INTO {tabela} ({nomes}) SELECT {nomes} FROM read_json("  # noqa: S608 - identificadores do catálogo interno; o caminho vai como parâmetro
        f"?, format = 'newline_delimited', columns = {{{estrutura}}})",
        [str(arquivo)],
    )
    return quantidade


type AbrirConexao = Callable[[], AbstractContextManager[duckdb.DuckDBPyConnection]]


def conexao_sob_demanda(
    caminho: Path,
    tentativas: int = 10,
    espera_s: float = 1.0,
    dormir: Callable[[float], None] = time.sleep,
) -> AbrirConexao:
    """Abre uma conexão nova a cada operação e a fecha ao final.

    O DuckDB bloqueia o arquivo para outros processos enquanto há uma conexão
    aberta. Abrir só durante cada operação deixa o banco livre para o dashboard
    enquanto a CLI consulta a API. Se outro processo estiver com o arquivo aberto
    naquele instante, a abertura é repetida algumas vezes antes de falhar.

    Raises:
        duckdb.IOException: Se o arquivo continuar bloqueado após as tentativas.
    """

    def abrir() -> duckdb.DuckDBPyConnection:
        for tentativa in range(1, tentativas + 1):
            try:
                return duckdb.connect(str(caminho))
            except duckdb.IOException:
                if tentativa == tentativas:
                    raise
                logger.warning(
                    "banco em uso por outro processo; nova tentativa agendada",
                    extra={"tentativa": tentativa, "espera_s": espera_s},
                )
                dormir(espera_s)
        raise ValueError("tentativas deve ser >= 1")

    return abrir


def conexao_fixa(conexao: duckdb.DuckDBPyConnection) -> AbrirConexao:
    """Reaproveita uma conexão já aberta, que continua sendo de quem a criou."""
    return lambda: nullcontext(conexao)


@contextmanager
def transacao(conexao: duckdb.DuckDBPyConnection) -> Iterator[None]:
    """Executa o bloco em uma transação: commit no sucesso, rollback em qualquer falha."""
    conexao.begin()
    try:
        yield
    except BaseException:
        conexao.rollback()
        raise
    conexao.commit()


class RepositorioDuckDB:
    """Repositório de tabelas indexadas pela entidade que armazenam.

    Cada partição (por exemplo, ``{"session_key": 9159}``) é substituída por inteiro
    em uma única transação: reprocessar produz o mesmo estado final, e leitores
    nunca veem a partição pela metade.
    """

    def __init__(self, abrir_conexao: AbrirConexao, tabelas: Mapping[type, str]) -> None:
        self._abrir_conexao = abrir_conexao
        self._tabelas = {modelo: TabelaDuckDB(nome, modelo) for modelo, nome in tabelas.items()}

    def criar_tabelas(self) -> None:
        """Cria as tabelas que ainda não existem e acrescenta colunas novas."""
        with self._abrir_conexao() as conexao, transacao(conexao):
            for tabela in self._tabelas.values():
                for comando in tabela.ddl():
                    conexao.execute(comando)

    def substituir_particao(
        self, particao: Mapping[str, int], lotes: Mapping[type, Sequence[object]]
    ) -> None:
        """Substitui a partição de cada tabela em ``lotes`` em uma única transação.

        Um lote vazio limpa a partição da tabela correspondente.

        Args:
            particao: Colunas e valores que identificam a partição.
            lotes: Entidades por tipo; o tipo define a tabela.

        Raises:
            KeyError: Se um tipo não pertencer a este repositório.
            ValueError: Se uma coluna da partição não existir na tabela.
            duckdb.Error: Se a escrita falhar; nenhuma alteração é mantida.
        """
        alvos = [(self._tabela(modelo), registros) for modelo, registros in lotes.items()]
        with tempfile.TemporaryDirectory(prefix="f1-carga-") as temporario:
            diretorio = Path(temporario)
            with self._abrir_conexao() as conexao, transacao(conexao):
                for tabela, registros in alvos:
                    filtro, valores = self._filtro(tabela, particao)
                    conexao.execute(f"DELETE FROM {tabela.nome} WHERE {filtro}", valores)  # noqa: S608 - identificadores validados contra o schema; valores parametrizados
                    inserir_jsonl(
                        conexao,
                        tabela.nome,
                        [(c.nome, c.tipo_sql) for c in tabela.colunas],
                        (tabela.para_linha(r) for r in registros),
                        diretorio,
                    )

    def ler[T](self, modelo: type[T], particao: Mapping[str, int]) -> list[T]:
        """Lê as entidades de uma partição.

        Raises:
            KeyError: Se o tipo não pertencer a este repositório.
            ValueError: Se uma coluna da partição não existir na tabela.
        """
        tabela = self._tabela(modelo)
        filtro, valores = self._filtro(tabela, particao)
        colunas = ", ".join(tabela.nomes_colunas)
        with self._abrir_conexao() as conexao:
            linhas = conexao.execute(
                f"SELECT {colunas} FROM {tabela.nome} WHERE {filtro}",  # noqa: S608 - identificadores validados contra o schema; valores parametrizados
                valores,
            ).fetchall()
        return [tabela.da_linha(linha) for linha in linhas]

    def _tabela(self, modelo: type) -> TabelaDuckDB:
        try:
            return self._tabelas[modelo]
        except KeyError as exc:
            raise KeyError(f"{modelo.__name__} não pertence a este repositório") from exc

    @staticmethod
    def _filtro(tabela: TabelaDuckDB, particao: Mapping[str, int]) -> tuple[str, list[int]]:
        if not particao:
            raise ValueError("a partição precisa de pelo menos uma coluna")
        desconhecidas = set(particao) - set(tabela.nomes_colunas)
        if desconhecidas:
            raise ValueError(
                f"colunas de partição inexistentes em {tabela.nome}: {sorted(desconhecidas)}"
            )
        return " AND ".join(f"{coluna} = ?" for coluna in particao), list(particao.values())
