from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
from streamlit.testing.v1 import AppTest

from f1.domain.endpoints import TODOS_ENDPOINTS
from f1.domain.modelos import Meeting, Piloto, Sessao, Volta
from f1.domain.tipos import TipoSessao
from f1.domain.validacao import validar
from f1.repositories.duckdb_base import conexao_sob_demanda
from f1.repositories.duckdb_bruto import RepositorioBrutoDuckDB
from f1.repositories.duckdb_consultas import ConsultasDuckDB

pytestmark = pytest.mark.integration

APP = Path(__file__).parents[3] / "src" / "f1" / "dashboard" / "app.py"
ENDPOINT = {e.nome: e for e in TODOS_ENDPOINTS}


def _converter(amostras, endpoint, chave=None):
    return list(validar(amostras[chave or endpoint], ENDPOINT[endpoint].conversor).validos)


@pytest.fixture
def caminho_banco(tmp_path, amostras):
    """Banco com a corrida 9673 (6 voltas de 2 pilotos) e uma sprint 2 sem voltas."""
    caminho = tmp_path / "f1.duckdb"
    corrida = _converter(amostras, "sessions")[0]
    sprint = replace(
        corrida, session_key=2, session_name="Sprint", date_start=corrida.date_start.replace(day=20)
    )
    voltas = _converter(amostras, "laps")
    voltas += [
        replace(v, driver_number=4, lap_duration=v.lap_duration - Decimal(1)) for v in voltas
    ]
    repositorio = RepositorioBrutoDuckDB(conexao_sob_demanda(caminho))
    repositorio.criar_tabelas()
    repositorio.substituir_particao(
        {"year": 2024}, {Meeting: _converter(amostras, "meetings"), Sessao: [corrida, sprint]}
    )
    repositorio.substituir_particao(
        {"session_key": 9673}, {Volta: voltas, Piloto: _converter(amostras, "drivers")}
    )
    return caminho


def test_consultas_voltas_mais_rapidas_limita_e_ordena(caminho_banco):
    with duckdb.connect(str(caminho_banco), read_only=True) as conexao:
        consultas = ConsultasDuckDB(conexao)
        sessoes = consultas.sessoes(2024, TipoSessao.RACE)
        voltas = consultas.voltas_mais_rapidas([s.session_key for s in sessoes], limite=5)

    assert [s.session_key for s in sessoes] == [2, 9673]
    assert voltas[2] == []
    rapidas = voltas[9673]
    assert [v.posicao for v in rapidas] == [1, 2, 3, 4, 5]
    assert [v.lap_duration for v in rapidas] == sorted(v.lap_duration for v in rapidas)
    assert rapidas[0].name_acronym == "NOR"


def test_consultas_banco_sem_tabelas(tmp_path):
    with duckdb.connect(str(tmp_path / "vazio.duckdb")) as conexao:
        consultas = ConsultasDuckDB(conexao)

        assert consultas.anos_disponiveis() == []
        assert consultas.sessoes(2024, TipoSessao.RACE) == []
        assert consultas.voltas_mais_rapidas([]) == {}


@pytest.fixture
def ambiente(monkeypatch, caminho_banco):
    monkeypatch.setenv("F1_AMBIENTE", "dev")
    monkeypatch.setenv("F1_CAMINHO_BANCO", str(caminho_banco))


@pytest.mark.usefixtures("ambiente")
def test_dashboard_mostra_um_bloco_por_circuito_com_as_voltas():
    app = AppTest.from_file(str(APP)).run(timeout=30)

    assert not app.exception
    assert app.title[0].value == "🏎️ F1 — 5 Voltas Mais Rápidas por Circuito"
    assert [e.label for e in app.expander] == [
        "🏁 Chinese Grand Prix — Shanghai, China (Sprint)",
        "🏁 Chinese Grand Prix — Shanghai, China",
    ]
    assert "sessao --session-key 2" in app.info[0].value
    tabela = app.dataframe[0].value
    assert len(tabela) == 5
    assert tabela["Pos"].tolist() == [1, 2, 3, 4, 5]


@pytest.mark.usefixtures("ambiente")
def test_dashboard_filtro_sem_sessoes_informa():
    app = AppTest.from_file(str(APP)).run(timeout=30)

    app.sidebar.selectbox[1].select(TipoSessao.QUALIFYING).run(timeout=30)

    assert not app.expander
    assert "Nenhuma sessão" in app.info[0].value


def test_dashboard_sem_banco_orienta_a_ingestao(monkeypatch, tmp_path):
    monkeypatch.setenv("F1_AMBIENTE", "dev")
    monkeypatch.setenv("F1_CAMINHO_BANCO", str(tmp_path / "inexistente.duckdb"))

    app = AppTest.from_file(str(APP)).run(timeout=30)

    assert "f1 catalogo" in app.warning[0].value
