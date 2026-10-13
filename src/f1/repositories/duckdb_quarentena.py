"""Quarentena no DuckDB: registros rejeitados pela validação, com o motivo."""

import json
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from f1.domain.validacao import RegistroRejeitado
from f1.repositories.duckdb_base import AbrirConexao, inserir_jsonl, transacao

TABELA = "quarentena"
COLUNAS = (
    ("id_execucao", "VARCHAR"),
    ("endpoint", "VARCHAR"),
    ("particao", "VARCHAR"),
    ("registro", "VARCHAR"),
    ("motivo", "VARCHAR"),
    ("registrado_em", "TIMESTAMP"),
)


def descrever_particao(particao: Mapping[str, int]) -> str:
    """Representa a partição como texto estável, por exemplo ``session_key=9159``."""
    return "/".join(f"{coluna}={valor}" for coluna, valor in particao.items())


class RepositorioQuarentenaDuckDB:
    """Grava rejeitados substituindo os do mesmo endpoint e partição (idempotente).

    Os registros da OpenF1 são dados públicos de pilotos e equipes, sem dados
    pessoais sensíveis; por isso são gravados sem mascaramento.
    """

    def __init__(
        self,
        abrir_conexao: AbrirConexao,
        id_execucao: str,
        agora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._abrir_conexao = abrir_conexao
        self._id_execucao = id_execucao
        self._agora = agora

    def criar_tabela(self) -> None:
        """Cria a tabela de quarentena, se ainda não existir."""
        definicoes = ", ".join(f"{nome} {tipo}" for nome, tipo in COLUNAS)
        with self._abrir_conexao() as conexao:
            conexao.execute(f"CREATE TABLE IF NOT EXISTS {TABELA} ({definicoes})")

    def registrar(
        self, endpoint: str, particao: Mapping[str, int], rejeitados: Sequence[RegistroRejeitado]
    ) -> None:
        """Substitui os rejeitados do endpoint na partição. Uma sequência vazia limpa a partição."""
        descricao = descrever_particao(particao)
        instante = self._agora().astimezone(UTC).replace(tzinfo=None).isoformat()
        linhas = (
            {
                "id_execucao": self._id_execucao,
                "endpoint": endpoint,
                "particao": descricao,
                "registro": json.dumps(dict(r.registro), ensure_ascii=False, default=str),
                "motivo": r.motivo,
                "registrado_em": instante,
            }
            for r in rejeitados
        )
        with (
            tempfile.TemporaryDirectory(prefix="f1-quarentena-") as temporario,
            self._abrir_conexao() as conexao,
            transacao(conexao),
        ):
            conexao.execute(
                f"DELETE FROM {TABELA} WHERE endpoint = ? AND particao = ?",  # noqa: S608 - nome de tabela constante; valores parametrizados
                [endpoint, descricao],
            )
            inserir_jsonl(conexao, TABELA, COLUNAS, linhas, Path(temporario))
