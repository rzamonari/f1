"""Estratégia por piloto: sequência de compostos, duração dos stints e pit stops."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from decimal import Decimal

from f1.domain.analitico import EstrategiaPiloto
from f1.domain.modelos import PitStop, Stint
from f1.domain.tipos import Composto


def voltas_do_stint(stint: Stint) -> int | None:
    """Número de voltas do stint, ou ``None`` se a API não informou o intervalo."""
    if stint.lap_start is None or stint.lap_end is None:
        return None
    return stint.lap_end - stint.lap_start + 1


def _somar(valores: Iterable[Decimal | None]) -> Decimal | None:
    informados = [v for v in valores if v is not None]
    return sum(informados, Decimal(0)) if informados else None


def _estrategia_piloto(
    session_key: int, driver_number: int, stints: Sequence[Stint], pits: Sequence[PitStop]
) -> EstrategiaPiloto:
    ordenados = sorted(stints, key=lambda s: s.stint_number)
    return EstrategiaPiloto(
        session_key=session_key,
        driver_number=driver_number,
        compostos=tuple(str(s.compound or Composto.UNKNOWN) for s in ordenados),
        voltas_por_stint=tuple(voltas_do_stint(s) for s in ordenados),
        numero_paradas=len(pits),
        tempo_total_pit_lane_s=_somar(p.lane_duration for p in pits),
        tempo_total_parado_s=_somar(p.stop_duration for p in pits),
    )


def montar_estrategia(
    session_key: int, stints: Iterable[Stint], pits: Iterable[PitStop]
) -> list[EstrategiaPiloto]:
    """Monta a estratégia de cada piloto com stint ou pit stop, ordenada pelo número."""
    stints_por_piloto: dict[int, list[Stint]] = defaultdict(list)
    pits_por_piloto: dict[int, list[PitStop]] = defaultdict(list)
    for stint in stints:
        stints_por_piloto[stint.driver_number].append(stint)
    for pit in pits:
        pits_por_piloto[pit.driver_number].append(pit)
    pilotos = sorted(stints_por_piloto.keys() | pits_por_piloto.keys())
    return [
        _estrategia_piloto(session_key, n, stints_por_piloto[n], pits_por_piloto[n])
        for n in pilotos
    ]
