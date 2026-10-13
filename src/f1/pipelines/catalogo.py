"""Pipeline do catálogo: meetings e sessões de um ano."""

import logging
import time
from dataclasses import dataclass

from f1.domain.consulta import igual
from f1.domain.endpoints import MEETINGS, SESSIONS
from f1.domain.modelos import Meeting, Sessao
from f1.pipelines.ingestao import ContagemEndpoint, contar, validar_endpoint
from f1.pipelines.portas import DestinoParticionado, DestinoRejeitados, FonteOpenF1

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResumoCatalogo:
    """Resultado da ingestão do catálogo de um ano."""

    ano: int
    meetings: tuple[Meeting, ...]
    sessoes: tuple[Sessao, ...]
    contagens: tuple[ContagemEndpoint, ...]


def executar_catalogo(
    ano: int,
    fonte: FonteOpenF1,
    destino: DestinoParticionado,
    quarentena: DestinoRejeitados,
    limite_taxa_rejeicao: float,
) -> ResumoCatalogo:
    """Extrai, valida e grava ``meetings`` e ``sessions`` de um ano (partição ``year``).

    Raises:
        TaxaRejeicaoExcedidaError: Se a taxa de rejeição de um endpoint superar o limite.
        FonteIndisponivelError: Se a API continuar indisponível após os retries.
        RequisicaoRecusadaError: Se a API recusar a requisição.
    """
    inicio = time.perf_counter()
    particao = {"year": ano}
    logger.info("catálogo iniciado", extra={"pipeline": "catalogo", "ano": ano})

    resultado_meetings = validar_endpoint(
        MEETINGS,
        fonte.buscar(MEETINGS.nome, [igual("year", ano)]),
        particao,
        quarentena,
        limite_taxa_rejeicao,
    )
    resultado_sessoes = validar_endpoint(
        SESSIONS,
        fonte.buscar(SESSIONS.nome, [igual("year", ano)]),
        particao,
        quarentena,
        limite_taxa_rejeicao,
    )
    destino.substituir_particao(
        particao,
        {Meeting: resultado_meetings.validos, Sessao: resultado_sessoes.validos},
    )

    resumo = ResumoCatalogo(
        ano=ano,
        meetings=resultado_meetings.validos,
        sessoes=resultado_sessoes.validos,
        contagens=(contar(MEETINGS, resultado_meetings), contar(SESSIONS, resultado_sessoes)),
    )
    logger.info(
        "catálogo concluído",
        extra={
            "pipeline": "catalogo",
            "ano": ano,
            "meetings": len(resumo.meetings),
            "sessoes": len(resumo.sessoes),
            "rejeitados": sum(c.rejeitados for c in resumo.contagens),
            "duracao_s": round(time.perf_counter() - inicio, 3),
        },
    )
    return resumo
