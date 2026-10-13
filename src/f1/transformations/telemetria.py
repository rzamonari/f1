"""Agregação da telemetria do carro (``car_data``) por volta."""

from bisect import bisect_right
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from f1.domain.analitico import TelemetriaVolta
from f1.domain.modelos import DadosCarro, Volta

DRS_ABERTO = frozenset({10, 12, 14})
ACELERADOR_PLENO_PCT = 99


@dataclass(frozen=True, slots=True)
class IntervaloVolta:
    """Instante de início (inclusivo) e fim (exclusivo) de uma volta."""

    lap_number: int
    inicio: datetime
    fim: datetime


@dataclass(slots=True)
class _Acumulador:
    amostras: int = 0
    velocidades: list[int] = field(default_factory=list)
    aceleradores: list[int] = field(default_factory=list)
    acelerador_pleno: int = 0
    freio: int = 0
    drs_aberto: int = 0

    def adicionar(self, amostra: DadosCarro) -> None:
        self.amostras += 1
        if amostra.speed is not None:
            self.velocidades.append(amostra.speed)
        if amostra.throttle is not None:
            self.aceleradores.append(amostra.throttle)
            self.acelerador_pleno += amostra.throttle >= ACELERADOR_PLENO_PCT
        self.freio += bool(amostra.brake)
        self.drs_aberto += amostra.drs in DRS_ABERTO


def intervalos_das_voltas(voltas: Iterable[Volta]) -> list[IntervaloVolta]:
    """Delimita cada volta pelo início da volta seguinte.

    A última volta termina em ``date_start + lap_duration``; sem duração, ela é
    descartada, para não atribuir a ela a volta de desaceleração.
    """
    marcos = sorted(
        ((v.lap_number, v.date_start, v.lap_duration) for v in voltas if v.date_start is not None),
        key=lambda marco: (marco[0], marco[1]),
    )
    intervalos: list[IntervaloVolta] = []
    for posicao, (volta, inicio, duracao) in enumerate(marcos):
        if posicao + 1 < len(marcos):
            fim = marcos[posicao + 1][1]
        elif duracao is not None:
            fim = inicio + timedelta(seconds=float(duracao))
        else:
            continue
        intervalos.append(IntervaloVolta(volta, inicio, fim))
    return intervalos


def _pct(parte: int, total: int) -> float:
    return round(100 * parte / total, 2) if total else 0.0


def _media(valores: Sequence[int]) -> float | None:
    return round(sum(valores) / len(valores), 2) if valores else None


def agregar_por_volta(
    session_key: int, driver_number: int, amostras: Iterable[DadosCarro], voltas: Iterable[Volta]
) -> list[TelemetriaVolta]:
    """Agrega as amostras de um piloto nas voltas em que foram coletadas.

    Amostras fora de qualquer volta (antes da largada ou depois da bandeirada) são
    ignoradas. Voltas sem amostras não aparecem no resultado.

    Args:
        session_key: Sessão das amostras.
        driver_number: Piloto das amostras; amostras e voltas de outros pilotos são ignoradas.
        amostras: Telemetria do carro, em qualquer ordem.
        voltas: Voltas da sessão.
    """
    intervalos = intervalos_das_voltas(v for v in voltas if v.driver_number == driver_number)
    inicios = [i.inicio for i in intervalos]
    acumuladores: dict[int, _Acumulador] = {}
    for amostra in amostras:
        if amostra.driver_number != driver_number:
            continue
        posicao = bisect_right(inicios, amostra.date) - 1
        if posicao < 0 or amostra.date >= intervalos[posicao].fim:
            continue
        volta = intervalos[posicao].lap_number
        acumuladores.setdefault(volta, _Acumulador()).adicionar(amostra)
    return [
        TelemetriaVolta(
            session_key=session_key,
            driver_number=driver_number,
            lap_number=volta,
            amostras=acc.amostras,
            velocidade_maxima=max(acc.velocidades, default=None),
            velocidade_media=_media(acc.velocidades),
            acelerador_medio_pct=_media(acc.aceleradores),
            acelerador_pleno_pct=_pct(acc.acelerador_pleno, acc.amostras),
            freio_acionado_pct=_pct(acc.freio, acc.amostras),
            drs_aberto_pct=_pct(acc.drs_aberto, acc.amostras),
        )
        for volta, acc in sorted(acumuladores.items())
    ]
