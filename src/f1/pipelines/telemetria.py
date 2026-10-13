"""Pipeline de telemetria: ``car_data`` e ``location`` lidos em janelas, por piloto."""

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from itertools import chain

from f1.domain.consulta import igual
from f1.domain.endpoints import ENDPOINTS_TELEMETRIA
from f1.domain.modelos import Sessao
from f1.pipelines.ingestao import ContagemEndpoint, contar, validar_endpoint
from f1.pipelines.portas import DestinoParticionado, DestinoRejeitados, FonteOpenF1

logger = logging.getLogger(__name__)

# A telemetria começa antes de date_start (voltas até o grid) e termina depois de
# date_end (volta de desaceleração); a margem cobre esses trechos.
MARGEM_TELEMETRIA = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class ParametrosTelemetria:
    """Parâmetros da ingestão de telemetria."""

    limite_taxa_rejeicao: float
    tamanho_janela: timedelta
    margem: timedelta = MARGEM_TELEMETRIA


@dataclass(frozen=True, slots=True)
class ResumoTelemetria:
    """Contagens da telemetria de uma sessão, por piloto e endpoint."""

    session_key: int
    contagens: tuple[tuple[int, ContagemEndpoint], ...]


def executar_telemetria(
    sessao: Sessao,
    pilotos: Sequence[int],
    fonte: FonteOpenF1,
    destino: DestinoParticionado,
    quarentena: DestinoRejeitados,
    parametros: ParametrosTelemetria,
) -> ResumoTelemetria:
    """Ingere a telemetria de cada piloto (partição ``session_key`` + ``driver_number``).

    Cada piloto é gravado em uma transação própria, o que limita a memória a um
    piloto por vez. Um reprocessamento substitui só os pilotos executados.

    Raises:
        TaxaRejeicaoExcedidaError: Se a taxa de rejeição de um endpoint superar o limite.
        FonteIndisponivelError: Se a API continuar indisponível após os retries.
        RequisicaoRecusadaError: Se a API recusar a requisição.
    """
    inicio_execucao = time.perf_counter()
    chave = sessao.session_key
    inicio = sessao.date_start - parametros.margem
    fim = sessao.date_end + parametros.margem
    logger.info(
        "telemetria iniciada",
        extra={"pipeline": "telemetria", "session_key": chave, "pilotos": len(pilotos)},
    )
    contagens: list[tuple[int, ContagemEndpoint]] = []
    for piloto in pilotos:
        particao = {"session_key": chave, "driver_number": piloto}
        lotes: dict[type, Sequence[object]] = {}
        for endpoint in ENDPOINTS_TELEMETRIA:
            janelas = fonte.buscar_em_janelas(
                endpoint.nome,
                [igual("session_key", chave), igual("driver_number", piloto)],
                inicio,
                fim,
                parametros.tamanho_janela,
            )
            resultado = validar_endpoint(
                endpoint,
                chain.from_iterable(janelas),
                particao,
                quarentena,
                parametros.limite_taxa_rejeicao,
            )
            lotes[endpoint.modelo] = resultado.validos
            contagens.append((piloto, contar(endpoint, resultado)))
        destino.substituir_particao(particao, lotes)
        logger.info(
            "telemetria do piloto gravada",
            extra={
                "pipeline": "telemetria",
                **particao,
                "amostras": sum(len(v) for v in lotes.values()),
            },
        )
    logger.info(
        "telemetria concluída",
        extra={
            "pipeline": "telemetria",
            "session_key": chave,
            "validos": sum(c.validos for _, c in contagens),
            "rejeitados": sum(c.rejeitados for _, c in contagens),
            "duracao_s": round(time.perf_counter() - inicio_execucao, 3),
        },
    )
    return ResumoTelemetria(session_key=chave, contagens=tuple(contagens))
