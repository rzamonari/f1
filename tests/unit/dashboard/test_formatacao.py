from datetime import UTC, datetime
from decimal import Decimal

import pytest

from f1.dashboard.formatacao import formatar_diferenca, formatar_tempo_volta, titulo_da_sessao
from f1.repositories.duckdb_consultas import SessaoDoCircuito


@pytest.mark.parametrize(
    ("segundos", "esperado"),
    [
        (Decimal("94.486"), "1:34.486"),
        (Decimal("59.9995"), "1:00.000"),
        (Decimal("65.1"), "1:05.100"),
        (Decimal("125.007"), "2:05.007"),
        (Decimal("0.5"), "0:00.500"),
    ],
)
def test_formatar_tempo_volta(segundos, esperado):
    assert formatar_tempo_volta(segundos) == esperado


@pytest.mark.parametrize(
    ("segundos", "esperado"),
    [(Decimal("94.609"), "+0.123"), (Decimal("94.486"), ""), (Decimal("96"), "+1.514")],
)
def test_formatar_diferenca_para_a_volta_mais_rapida(segundos, esperado):
    assert formatar_diferenca(segundos, Decimal("94.486")) == esperado


def _sessao(**sobrescritas):
    campos = {
        "session_key": 9606,
        "session_name": "Race",
        "meeting_name": "Singapore Grand Prix",
        "location": "Marina Bay",
        "country_name": "Singapore",
        "date_start": datetime(2024, 9, 22, 12, tzinfo=UTC),
        "voltas_ingeridas": 0,
    }
    return SessaoDoCircuito(**{**campos, **sobrescritas})


@pytest.mark.parametrize(
    ("sobrescritas", "esperado"),
    [
        ({}, "🏁 Singapore Grand Prix — Marina Bay, Singapore"),
        ({"session_name": "Sprint"}, "🏁 Singapore Grand Prix — Marina Bay, Singapore (Sprint)"),
        ({"location": None, "country_name": None}, "🏁 Singapore Grand Prix"),
    ],
)
def test_titulo_da_sessao(sobrescritas, esperado):
    assert titulo_da_sessao(_sessao(**sobrescritas), "Race") == esperado
