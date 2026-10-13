"""Ponto de entrada de linha de comando: monta as dependências e chama os pipelines."""

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from f1.config.settings import Configuracao, ConfiguracaoInvalidaError, carregar_configuracao
from f1.domain.tipos import TipoSessao
from f1.integrations.openf1 import ClienteOpenF1
from f1.observability.logging import configurar_logging, definir_id_execucao
from f1.pipelines.analitico import executar_analitico
from f1.pipelines.catalogo import executar_catalogo
from f1.pipelines.sessao import (
    ParametrosSessao,
    executar_sessao,
    obter_sessao,
    resolver_session_key,
)
from f1.pipelines.telemetria import ParametrosTelemetria, executar_telemetria
from f1.pipelines.temporada import DestinosTemporada, executar_temporada
from f1.repositories.duckdb_analitico import RepositorioAnaliticoDuckDB
from f1.repositories.duckdb_base import AbrirConexao, conexao_sob_demanda
from f1.repositories.duckdb_bruto import RepositorioBrutoDuckDB
from f1.repositories.duckdb_quarentena import RepositorioQuarentenaDuckDB

logger = logging.getLogger(__name__)

TIMEOUT_CONEXAO_S = 5.0


@dataclass(frozen=True, slots=True)
class Repositorios:
    """Repositórios concretos sobre a mesma conexão DuckDB."""

    bruto: RepositorioBrutoDuckDB
    analitico: RepositorioAnaliticoDuckDB
    quarentena: RepositorioQuarentenaDuckDB

    @classmethod
    def criar(cls, abrir_conexao: AbrirConexao, id_execucao: str) -> "Repositorios":
        """Instancia os repositórios e garante que as tabelas existam."""
        repositorios = cls(
            bruto=RepositorioBrutoDuckDB(abrir_conexao),
            analitico=RepositorioAnaliticoDuckDB(abrir_conexao),
            quarentena=RepositorioQuarentenaDuckDB(abrir_conexao, id_execucao),
        )
        repositorios.bruto.criar_tabelas()
        repositorios.analitico.criar_tabelas()
        repositorios.quarentena.criar_tabela()
        return repositorios


def criar_parser() -> argparse.ArgumentParser:
    """Define os subcomandos e argumentos da CLI."""
    parser = argparse.ArgumentParser(prog="f1", description="Pipeline de dados da OpenF1.")
    comandos = parser.add_subparsers(dest="comando", required=True)

    catalogo = comandos.add_parser("catalogo", help="meetings e sessões de um ano")
    catalogo.add_argument("--ano", type=int, required=True)

    sessao = comandos.add_parser("sessao", help="endpoints leves de uma sessão")
    sessao.add_argument(
        "--session-key", required=True, help="número da sessão ou 'latest' (resolvido no início)"
    )
    sessao.add_argument(
        "--com-telemetria", action="store_true", help="também ingere car_data e location"
    )

    temporada = comandos.add_parser("temporada", help="catálogo + todas as sessões de um tipo")
    temporada.add_argument("--ano", type=int, required=True)
    temporada.add_argument(
        "--tipo", type=TipoSessao, choices=list(TipoSessao), default=TipoSessao.RACE
    )

    analitico = comandos.add_parser("analitico", help="recalcula as tabelas derivadas")
    analitico.add_argument("--session-key", type=int, required=True)
    return parser


def _parametros_sessao(configuracao: Configuracao) -> ParametrosSessao:
    return ParametrosSessao(
        limite_taxa_rejeicao=configuracao.limite_taxa_rejeicao,
        margem_apos_sessao=configuracao.margem_apos_sessao,
        agora=lambda: datetime.now(UTC),
    )


def _comando_catalogo(
    args: argparse.Namespace, configuracao: Configuracao, fonte: ClienteOpenF1, repos: Repositorios
) -> bool:
    executar_catalogo(
        args.ano, fonte, repos.bruto, repos.quarentena, configuracao.limite_taxa_rejeicao
    )
    return True


def _comando_sessao(
    args: argparse.Namespace, configuracao: Configuracao, fonte: ClienteOpenF1, repos: Repositorios
) -> bool:
    sessao = obter_sessao(resolver_session_key(args.session_key, fonte), fonte)
    resumo = executar_sessao(
        sessao, fonte, repos.bruto, repos.quarentena, _parametros_sessao(configuracao)
    )
    if args.com_telemetria:
        executar_telemetria(
            sessao,
            resumo.pilotos,
            fonte,
            repos.bruto,
            repos.quarentena,
            ParametrosTelemetria(
                limite_taxa_rejeicao=configuracao.limite_taxa_rejeicao,
                tamanho_janela=configuracao.janela_telemetria,
            ),
        )
    return True


def _comando_temporada(
    args: argparse.Namespace, configuracao: Configuracao, fonte: ClienteOpenF1, repos: Repositorios
) -> bool:
    resumo = executar_temporada(
        args.ano,
        args.tipo,
        fonte,
        DestinosTemporada(repos.bruto, repos.bruto, repos.analitico, repos.quarentena),
        _parametros_sessao(configuracao),
    )
    return not resumo.falhas


type Comando = Callable[[argparse.Namespace, Configuracao, ClienteOpenF1, Repositorios], bool]

COMANDOS_COM_API: dict[str, Comando] = {
    "catalogo": _comando_catalogo,
    "sessao": _comando_sessao,
    "temporada": _comando_temporada,
}


def _executar(args: argparse.Namespace, configuracao: Configuracao, id_execucao: str) -> bool:
    """Abre banco e cliente HTTP, executa o comando e devolve se terminou sem falhas."""
    configuracao.caminho_banco.parent.mkdir(parents=True, exist_ok=True)
    # Uma conexão por escrita: o arquivo fica livre (para o dashboard, por exemplo)
    # enquanto a CLI consulta a API.
    repos = Repositorios.criar(conexao_sob_demanda(configuracao.caminho_banco), id_execucao)
    if args.comando == "analitico":
        executar_analitico(args.session_key, repos.bruto, repos.analitico)
        return True
    with httpx.Client(
        base_url=configuracao.api_base_url,
        timeout=httpx.Timeout(configuracao.timeout_s, connect=TIMEOUT_CONEXAO_S),
    ) as cliente_http:
        fonte = ClienteOpenF1(
            cliente_http,
            max_tentativas=configuracao.max_tentativas,
            pausa_entre_requisicoes_s=configuracao.pausa_entre_requisicoes_s,
        )
        return COMANDOS_COM_API[args.comando](args, configuracao, fonte, repos)


def main(argv: Sequence[str] | None = None) -> int:
    """Executa o subcomando informado. Retorna 0 em sucesso e 1 em falha."""
    args = criar_parser().parse_args(argv)
    configurar_logging()
    try:
        configuracao = carregar_configuracao()
    except ConfiguracaoInvalidaError:
        logger.exception("configuração inválida")
        return 1
    configurar_logging(configuracao.nivel_log)
    id_execucao = definir_id_execucao()
    logger.info(
        "execução iniciada",
        extra={"comando": args.comando, "ambiente": str(configuracao.ambiente)},
    )
    try:
        sucesso = _executar(args, configuracao, id_execucao)
    except Exception:
        # Único ponto onde a captura ampla é permitida: registra com stack trace e
        # devolve código de erro ao agendador.
        logger.exception("execução falhou", extra={"comando": args.comando})
        return 1
    logger.info("execução concluída", extra={"comando": args.comando, "sucesso": sucesso})
    return 0 if sucesso else 1


if __name__ == "__main__":
    sys.exit(main())
