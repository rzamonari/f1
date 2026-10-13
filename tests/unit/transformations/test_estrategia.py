from datetime import UTC, datetime
from decimal import Decimal

import pytest

from f1.domain.analitico import EstrategiaPiloto
from f1.domain.modelos import PitStop, Stint
from f1.domain.tipos import Composto
from f1.transformations.estrategia import montar_estrategia, voltas_do_stint


def stint(
    numero: int, composto: Composto | None, inicio: int | None, fim: int | None, piloto: int = 1
):
    return Stint(9673, 1233, piloto, numero, composto, inicio, fim, 0)


def pit(volta: int, pit_lane: str | None, parado: str | None, piloto: int = 1):
    return PitStop(
        session_key=9673,
        meeting_key=1233,
        driver_number=piloto,
        date=datetime(2024, 4, 21, 7, volta, tzinfo=UTC),
        lap_number=volta,
        lane_duration=Decimal(pit_lane) if pit_lane else None,
        stop_duration=Decimal(parado) if parado else None,
    )


@pytest.mark.parametrize(
    ("inicio", "fim", "esperado"), [(1, 13, 13), (14, 14, 1), (None, 13, None), (1, None, None)]
)
def test_voltas_do_stint(inicio, fim, esperado):
    assert voltas_do_stint(stint(1, Composto.SOFT, inicio, fim)) == esperado


def test_montar_estrategia_ordena_stints_e_soma_pits():
    stints = [stint(2, Composto.HARD, 14, 56), stint(1, Composto.MEDIUM, 1, 13)]
    pits = [pit(13, "22.4", "2.5")]

    resultado = montar_estrategia(9673, stints, pits)

    assert resultado == [
        EstrategiaPiloto(
            session_key=9673,
            driver_number=1,
            compostos=("MEDIUM", "HARD"),
            voltas_por_stint=(13, 43),
            numero_paradas=1,
            tempo_total_pit_lane_s=Decimal("22.4"),
            tempo_total_parado_s=Decimal("2.5"),
        )
    ]


def test_montar_estrategia_tempo_parado_ausente_antes_de_2024_fica_nulo():
    resultado = montar_estrategia(
        9673, [stint(1, Composto.SOFT, 1, 10)], [pit(10, "21.0", None), pit(30, "20.0", None)]
    )

    assert resultado[0].tempo_total_parado_s is None
    assert resultado[0].tempo_total_pit_lane_s == Decimal("41.0")
    assert resultado[0].numero_paradas == 2


def test_montar_estrategia_composto_nulo_vira_unknown():
    resultado = montar_estrategia(9673, [stint(1, None, None, None)], [])

    assert resultado[0].compostos == ("UNKNOWN",)
    assert resultado[0].voltas_por_stint == (None,)
    assert resultado[0].numero_paradas == 0


def test_montar_estrategia_inclui_piloto_so_com_pit():
    resultado = montar_estrategia(
        9673, [stint(1, Composto.SOFT, 1, 5, piloto=1)], [pit(3, "20", None, piloto=44)]
    )

    assert [(r.driver_number, r.compostos) for r in resultado] == [(1, ("SOFT",)), (44, ())]


def test_montar_estrategia_entrada_vazia():
    assert montar_estrategia(9673, [], []) == []
