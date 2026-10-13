"""Pipeline analítico: recalcula as tabelas derivadas de uma sessão a partir da camada bruta."""

import logging
import time
from dataclasses import dataclass

from f1.domain.analitico import EstrategiaPiloto, RitmoPiloto, TelemetriaVolta
from f1.domain.modelos import ControleProva, DadosCarro, PitStop, Stint, Volta
from f1.pipelines.portas import DestinoParticionado, LeitorParticionado
from f1.transformations.estrategia import montar_estrategia
from f1.transformations.telemetria import agregar_por_volta
from f1.transformations.voltas import resumir_ritmo

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResumoAnalitico:
    """Quantidade de linhas gravadas em cada tabela analítica da sessão."""

    session_key: int
    ritmo: int
    estrategia: int
    telemetria: int


def executar_analitico(
    session_key: int, fonte: LeitorParticionado, destino: DestinoParticionado
) -> ResumoAnalitico:
    """Recalcula ritmo, estratégia e telemetria por volta de uma sessão.

    A telemetria por volta só é calculada para pilotos com ``car_data`` gravado.
    As três tabelas são substituídas juntas, em uma transação.
    """
    inicio = time.perf_counter()
    particao = {"session_key": session_key}
    logger.info("analítico iniciado", extra={"pipeline": "analitico", **particao})

    voltas = fonte.ler(Volta, particao)
    if not voltas:
        logger.warning("sessão sem voltas na camada bruta", extra=particao)
    ritmo = resumir_ritmo(session_key, voltas, fonte.ler(ControleProva, particao))
    estrategia = montar_estrategia(
        session_key, fonte.ler(Stint, particao), fonte.ler(PitStop, particao)
    )
    telemetria: list[TelemetriaVolta] = []
    for piloto in sorted({v.driver_number for v in voltas}):
        amostras = fonte.ler(DadosCarro, {**particao, "driver_number": piloto})
        telemetria.extend(agregar_por_volta(session_key, piloto, amostras, voltas))

    destino.substituir_particao(
        particao,
        {RitmoPiloto: ritmo, EstrategiaPiloto: estrategia, TelemetriaVolta: telemetria},
    )
    resumo = ResumoAnalitico(session_key, len(ritmo), len(estrategia), len(telemetria))
    logger.info(
        "analítico concluído",
        extra={
            "pipeline": "analitico",
            **particao,
            "ritmo": resumo.ritmo,
            "estrategia": resumo.estrategia,
            "telemetria": resumo.telemetria,
            "duracao_s": round(time.perf_counter() - inicio, 3),
        },
    )
    return resumo
