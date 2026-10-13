"""Pipeline de sessão: todos os endpoints leves de uma ``session_key``."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from f1.domain.consulta import igual
from f1.domain.endpoints import ENDPOINTS_SESSAO, SESSIONS
from f1.domain.erros import SessaoIndisponivelError
from f1.domain.modelos import Piloto, Sessao
from f1.domain.tipos import TipoSessao
from f1.domain.validacao import validar
from f1.pipelines.ingestao import ContagemEndpoint, contar, validar_endpoint
from f1.pipelines.portas import DestinoParticionado, DestinoRejeitados, FonteOpenF1

logger = logging.getLogger(__name__)

SESSAO_MAIS_RECENTE = "latest"


@dataclass(frozen=True, slots=True)
class ParametrosSessao:
    """Parâmetros da ingestão de sessões.

    Attributes:
        limite_taxa_rejeicao: Proporção máxima de rejeitados por endpoint.
        margem_apos_sessao: Espera após ``date_end`` antes de ingerir, porque
            ``session_result`` e ``starting_grid`` saem minutos depois da sessão.
        agora: Relógio injetado, que devolve o instante atual em UTC.
    """

    limite_taxa_rejeicao: float
    margem_apos_sessao: timedelta
    agora: Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class ResumoSessao:
    """Resultado da ingestão de uma sessão."""

    sessao: Sessao
    contagens: tuple[ContagemEndpoint, ...]
    pilotos: tuple[int, ...]


def resolver_session_key(valor: str, fonte: FonteOpenF1) -> int:
    """Converte o argumento da CLI em uma ``session_key`` concreta.

    ``latest`` é resolvido na API **antes** da execução e registrado no log, para que
    a execução sempre tenha uma partição explícita.

    Raises:
        ValueError: Se ``valor`` não for inteiro nem ``latest``.
        SessaoIndisponivelError: Se a API não informar a sessão mais recente.
    """
    if valor != SESSAO_MAIS_RECENTE:
        return int(valor)
    registros = fonte.buscar(SESSIONS.nome, [igual("session_key", SESSAO_MAIS_RECENTE)])
    chaves = {r.get("session_key") for r in registros}
    if len(chaves) != 1 or not isinstance(chave := chaves.pop(), int):
        raise SessaoIndisponivelError("a OpenF1 não informou a sessão mais recente")
    logger.info("sessão mais recente resolvida", extra={"session_key": chave})
    return chave


def obter_sessao(session_key: int, fonte: FonteOpenF1) -> Sessao:
    """Busca e valida os metadados de uma sessão.

    Raises:
        SessaoIndisponivelError: Se a sessão não existir ou vier fora do contrato.
    """
    resultado = validar(
        fonte.buscar(SESSIONS.nome, [igual("session_key", session_key)]), SESSIONS.conversor
    )
    if len(resultado.validos) != 1:
        motivos = [r.motivo for r in resultado.rejeitados]
        raise SessaoIndisponivelError(
            f"sessão {session_key} não encontrada ou inválida (rejeições: {motivos})"
        )
    sessao = resultado.validos[0]
    if not isinstance(sessao, Sessao):
        raise TypeError("conversor de sessions devolveu tipo inesperado")
    return sessao


def verificar_disponibilidade(sessao: Sessao, parametros: ParametrosSessao) -> None:
    """Garante que a sessão pode ser ingerida agora.

    Raises:
        SessaoIndisponivelError: Se a sessão foi cancelada ou ainda não passou da margem.
    """
    if sessao.is_cancelled:
        raise SessaoIndisponivelError(f"sessão {sessao.session_key} cancelada")
    liberada_em = sessao.date_end + parametros.margem_apos_sessao
    if parametros.agora() < liberada_em:
        raise SessaoIndisponivelError(
            f"sessão {sessao.session_key} só pode ser ingerida após {liberada_em.isoformat()}"
        )


def executar_sessao(
    sessao: Sessao,
    fonte: FonteOpenF1,
    destino: DestinoParticionado,
    quarentena: DestinoRejeitados,
    parametros: ParametrosSessao,
) -> ResumoSessao:
    """Extrai, valida e grava os endpoints leves de uma sessão (partição ``session_key``).

    Todos os endpoints são validados antes da escrita, que acontece em uma única
    transação: a sessão nunca fica gravada pela metade. Endpoints só de corrida
    são pulados nas demais sessões, e a partição deles é limpa.

    Raises:
        SessaoIndisponivelError: Se a sessão foi cancelada ou ainda não encerrou.
        TaxaRejeicaoExcedidaError: Se a taxa de rejeição de um endpoint superar o limite.
        FonteIndisponivelError: Se a API continuar indisponível após os retries.
        RequisicaoRecusadaError: Se a API recusar a requisição.
    """
    verificar_disponibilidade(sessao, parametros)
    inicio = time.perf_counter()
    chave = sessao.session_key
    particao = {"session_key": chave}
    contexto = {"pipeline": "sessao", "session_key": chave, "tipo": str(sessao.session_type)}
    logger.info("sessão iniciada", extra=contexto)

    lotes: dict[type, tuple[object, ...]] = {}
    contagens: list[ContagemEndpoint] = []
    for endpoint in ENDPOINTS_SESSAO:
        if endpoint.so_corrida and sessao.session_type is not TipoSessao.RACE:
            logger.info(
                "endpoint só de corrida pulado", extra={**contexto, "endpoint": endpoint.nome}
            )
            lotes[endpoint.modelo] = ()
            continue
        registros = fonte.buscar(endpoint.nome, [igual("session_key", chave)])
        resultado = validar_endpoint(
            endpoint, registros, particao, quarentena, parametros.limite_taxa_rejeicao
        )
        lotes[endpoint.modelo] = resultado.validos
        contagens.append(contar(endpoint, resultado))

    destino.substituir_particao(particao, lotes)

    pilotos = tuple(sorted({p.driver_number for p in lotes[Piloto] if isinstance(p, Piloto)}))
    logger.info(
        "sessão concluída",
        extra={
            **contexto,
            "lidos": sum(c.lidos for c in contagens),
            "validos": sum(c.validos for c in contagens),
            "rejeitados": sum(c.rejeitados for c in contagens),
            "pilotos": len(pilotos),
            "duracao_s": round(time.perf_counter() - inicio, 3),
        },
    )
    return ResumoSessao(sessao=sessao, contagens=tuple(contagens), pilotos=pilotos)
