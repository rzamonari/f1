"""Entidades da camada analítica, derivadas das tabelas brutas de uma sessão."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RitmoPiloto:
    """Ritmo de um piloto na sessão.

    ``ritmo_medio_s`` considera só voltas válidas: com tempo, fora da volta de saída
    do pit e fora de períodos de safety car ou virtual safety car.
    """

    session_key: int
    driver_number: int
    voltas_totais: int
    voltas_validas: int
    melhor_volta_s: Decimal | None
    numero_melhor_volta: int | None
    ritmo_medio_s: Decimal | None


@dataclass(frozen=True, slots=True)
class EstrategiaPiloto:
    """Estratégia de pneus e de pit stops de um piloto na sessão.

    As tuplas seguem a ordem dos stints. ``voltas_por_stint`` tem ``None`` quando a
    API não informa o intervalo de voltas do stint. Os tempos de pit somam só as
    paradas com o tempo informado e ficam nulos quando nenhuma tem.
    """

    session_key: int
    driver_number: int
    compostos: tuple[str, ...]
    voltas_por_stint: tuple[int | None, ...]
    numero_paradas: int
    tempo_total_pit_lane_s: Decimal | None
    tempo_total_parado_s: Decimal | None


@dataclass(frozen=True, slots=True)
class TelemetriaVolta:
    """Agregados de telemetria do carro em uma volta."""

    session_key: int
    driver_number: int
    lap_number: int
    amostras: int
    velocidade_maxima: int | None
    velocidade_media: float | None
    acelerador_medio_pct: float | None
    acelerador_pleno_pct: float
    freio_acionado_pct: float
    drs_aberto_pct: float
