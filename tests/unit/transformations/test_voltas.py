from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from f1.domain.analitico import RitmoPiloto
from f1.domain.modelos import ControleProva
from f1.transformations.voltas import (
    eh_volta_representativa,
    resumir_ritmo,
    voltas_neutralizadas,
)

BASE = datetime(2024, 4, 21, 7, 0, tzinfo=UTC)


def mensagem(minuto: int, volta: int | None, texto: str, categoria: str = "SafetyCar"):
    return ControleProva(
        session_key=9673,
        meeting_key=1233,
        date=BASE + timedelta(minutes=minuto),
        category=categoria,
        message=texto,
        flag=None,
        scope=None,
        sector=None,
        driver_number=None,
        lap_number=volta,
        qualifying_phase=None,
    )


def test_voltas_neutralizadas_safety_car_inclui_inicio_e_fim():
    mensagens = [mensagem(1, 7, "SAFETY CAR DEPLOYED"), mensagem(5, 9, "SAFETY CAR IN THIS LAP")]

    assert voltas_neutralizadas(mensagens, ultima_volta=50) == {7, 8, 9}


def test_voltas_neutralizadas_vsc_convertido_em_sc_mantem_inicio_do_vsc():
    # Caso real (China 2024): VSC na volta 22 vira SC na 23, sem mensagem de VSC ENDING.
    mensagens = [
        mensagem(1, 22, "VIRTUAL SAFETY CAR DEPLOYED"),
        mensagem(2, 23, "SAFETY CAR DEPLOYED"),
        mensagem(3, 26, "SAFETY CAR IN THIS LAP"),
        mensagem(4, 27, "SAFETY CAR DEPLOYED"),
        mensagem(5, 31, "SAFETY CAR IN THIS LAP"),
    ]

    assert voltas_neutralizadas(mensagens, ultima_volta=56) == set(range(22, 32))


def test_voltas_neutralizadas_ordena_mensagens_pela_data():
    mensagens = [
        mensagem(5, 12, "VIRTUAL SAFETY CAR ENDING"),
        mensagem(1, 11, "VIRTUAL SAFETY CAR DEPLOYED"),
    ]

    assert voltas_neutralizadas(mensagens, ultima_volta=50) == {11, 12}


def test_voltas_neutralizadas_periodo_aberto_vai_ate_a_ultima_volta():
    assert voltas_neutralizadas([mensagem(1, 48, "SAFETY CAR DEPLOYED")], ultima_volta=50) == {
        48,
        49,
        50,
    }


@pytest.mark.parametrize(
    "mensagens",
    [
        [mensagem(1, 5, "SAFETY CAR DEPLOYED", categoria="Flag")],
        [mensagem(1, None, "SAFETY CAR DEPLOYED")],
        [mensagem(1, 5, "SAFETY CAR IN THIS LAP")],
        [],
    ],
    ids=["outra-categoria", "sem-volta", "fim-sem-inicio", "vazio"],
)
def test_voltas_neutralizadas_ignora_mensagens_irrelevantes(mensagens):
    assert voltas_neutralizadas(mensagens, ultima_volta=50) == frozenset()


@pytest.mark.parametrize(
    ("sobrescritas", "esperado"),
    [
        ({"lap_number": 2}, True),
        ({"lap_number": 2, "lap_duration": None}, False),
        ({"lap_number": 2, "is_pit_out_lap": True}, False),
        ({"lap_number": 8}, False),
    ],
    ids=["valida", "sem-tempo", "saida-pit", "sob-sc"],
)
def test_eh_volta_representativa(fabrica_volta, sobrescritas, esperado):
    assert eh_volta_representativa(fabrica_volta(**sobrescritas), frozenset({8})) is esperado


def test_resumir_ritmo_exclui_pit_out_e_sc_da_media(fabrica_volta):
    voltas = [
        fabrica_volta(lap_number=1, lap_duration=Decimal("100"), is_pit_out_lap=False),
        fabrica_volta(lap_number=2, lap_duration=Decimal("90"), is_pit_out_lap=False),
        fabrica_volta(lap_number=3, lap_duration=Decimal("120"), is_pit_out_lap=True),
        fabrica_volta(lap_number=4, lap_duration=Decimal("130")),
        fabrica_volta(lap_number=5, lap_duration=None),
    ]
    mensagens = [mensagem(1, 4, "SAFETY CAR DEPLOYED"), mensagem(2, 4, "SAFETY CAR IN THIS LAP")]

    resultado = resumir_ritmo(9673, voltas, mensagens)

    assert resultado == [
        RitmoPiloto(
            session_key=9673,
            driver_number=1,
            voltas_totais=5,
            voltas_validas=2,
            melhor_volta_s=Decimal("90"),
            numero_melhor_volta=2,
            ritmo_medio_s=Decimal("95.000"),
        )
    ]


def test_resumir_ritmo_um_resultado_por_piloto_ordenado(fabrica_volta):
    voltas = [fabrica_volta(driver_number=44), fabrica_volta(driver_number=1)]

    resultado = resumir_ritmo(9673, voltas, [])

    assert [r.driver_number for r in resultado] == [1, 44]


def test_resumir_ritmo_piloto_sem_voltas_cronometradas(fabrica_volta):
    resultado = resumir_ritmo(9673, [fabrica_volta(lap_duration=None)], [])

    assert resultado[0].melhor_volta_s is None
    assert resultado[0].ritmo_medio_s is None
    assert resultado[0].voltas_validas == 0


def test_resumir_ritmo_entrada_vazia():
    assert resumir_ritmo(9673, [], []) == []
