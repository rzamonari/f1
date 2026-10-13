"""Teste de fumaça contra a API real da OpenF1.

Acessa a rede, por isso só roda com ``F1_TESTES_REDE=1``: fica fora da CI e serve
para detectar mudanças de contrato da API.
"""

import os

import httpx
import pytest

from f1.domain.consulta import igual
from f1.domain.endpoints import ENDPOINTS_SESSAO, SESSIONS
from f1.domain.validacao import validar
from f1.integrations.openf1 import ClienteOpenF1

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("F1_TESTES_REDE") != "1", reason="acessa a API real; defina F1_TESTES_REDE=1"
    ),
]

SESSAO_REFERENCIA = 9606  # Corrida de Singapura 2024


@pytest.fixture(scope="module")
def cliente():
    with httpx.Client(base_url="https://api.openf1.org/v1", timeout=30) as http:
        yield ClienteOpenF1(http, pausa_entre_requisicoes_s=0.5)


def test_api_real_sessao_valida_sem_rejeicoes(cliente):
    resultado = validar(
        cliente.buscar("sessions", [igual("session_key", SESSAO_REFERENCIA)]), SESSIONS.conversor
    )

    assert len(resultado.validos) == 1
    assert resultado.rejeitados == ()


@pytest.mark.parametrize("endpoint", ENDPOINTS_SESSAO, ids=lambda e: e.nome)
def test_api_real_endpoints_de_sessao_respeitam_o_contrato(cliente, endpoint):
    resultado = validar(
        cliente.buscar(endpoint.nome, [igual("session_key", SESSAO_REFERENCIA)]), endpoint.conversor
    )

    assert resultado.rejeitados == ()
