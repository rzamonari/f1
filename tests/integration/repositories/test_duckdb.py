import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import duckdb
import pytest

from f1.domain.analitico import EstrategiaPiloto, RitmoPiloto
from f1.domain.endpoints import ENDPOINTS_CATALOGO, ENDPOINTS_TELEMETRIA, TODOS_ENDPOINTS
from f1.domain.modelos import Piloto, Volta
from f1.domain.validacao import RegistroRejeitado, validar
from f1.repositories.duckdb_analitico import RepositorioAnaliticoDuckDB
from f1.repositories.duckdb_base import conexao_fixa
from f1.repositories.duckdb_bruto import RepositorioBrutoDuckDB
from f1.repositories.duckdb_quarentena import RepositorioQuarentenaDuckDB

pytestmark = pytest.mark.integration

AMOSTRA_POR_ENDPOINT = {
    "meetings": "meetings",
    "sessions": "sessions",
    "drivers": "drivers",
    "laps": "laps",
    "stints": "stints",
    "pit": "pit",
    "session_result": "session_result_quali",
    "starting_grid": "starting_grid",
    "weather": "weather",
    "race_control": "race_control_sc",
    "position": "position",
    "intervals": "intervals",
    "overtakes": "overtakes",
    "team_radio": "team_radio",
    "championship_drivers": "championship_drivers",
    "championship_teams": "championship_teams",
    "car_data": "car_data",
    "location": "location",
}


@pytest.fixture
def conexao(tmp_path):
    with duckdb.connect(str(tmp_path / "teste.duckdb")) as conexao:
        yield conexao


@pytest.fixture
def bruto(conexao):
    repositorio = RepositorioBrutoDuckDB(conexao_fixa(conexao))
    repositorio.criar_tabelas()
    return repositorio


def _particao(endpoint, entidade):
    if endpoint in ENDPOINTS_CATALOGO:
        return {"year": entidade.year}
    if endpoint in ENDPOINTS_TELEMETRIA:
        return {"session_key": entidade.session_key, "driver_number": entidade.driver_number}
    return {"session_key": entidade.session_key}


@pytest.mark.parametrize("endpoint", TODOS_ENDPOINTS, ids=lambda e: e.nome)
def test_bruto_ida_e_volta_preserva_entidades(bruto, amostras, endpoint):
    entidades = validar(amostras[AMOSTRA_POR_ENDPOINT[endpoint.nome]], endpoint.conversor).validos
    particao = _particao(endpoint, entidades[0])

    bruto.substituir_particao(particao, {endpoint.modelo: entidades})

    lidas = bruto.ler(endpoint.modelo, particao)

    assert len(lidas) == len(entidades)
    assert set(lidas) == set(entidades)


def test_bruto_substituir_particao_e_idempotente(bruto, conexao, amostras):
    endpoint = next(e for e in TODOS_ENDPOINTS if e.nome == "laps")
    voltas = validar(amostras["laps"], endpoint.conversor).validos

    bruto.substituir_particao({"session_key": 9673}, {Volta: voltas})
    bruto.substituir_particao({"session_key": 9673}, {Volta: voltas})

    assert conexao.execute("SELECT COUNT(*) FROM laps").fetchone() == (3,)


def test_bruto_substituir_particao_nao_afeta_outras_particoes(bruto, amostras):
    endpoint = next(e for e in TODOS_ENDPOINTS if e.nome == "laps")
    voltas = validar(amostras["laps"], endpoint.conversor).validos
    de_outra_sessao = [replace(v, session_key=1) for v in voltas]

    bruto.substituir_particao({"session_key": 1}, {Volta: de_outra_sessao})
    bruto.substituir_particao({"session_key": 9673}, {Volta: voltas})
    bruto.substituir_particao({"session_key": 9673}, {Volta: []})

    assert len(bruto.ler(Volta, {"session_key": 1})) == 3
    assert bruto.ler(Volta, {"session_key": 9673}) == []


def test_bruto_falha_na_escrita_desfaz_toda_a_transacao(bruto, amostras):
    pilotos = validar(amostras["drivers"], TODOS_ENDPOINTS[2].conversor).validos
    voltas = validar(
        amostras["laps"], next(e for e in TODOS_ENDPOINTS if e.nome == "laps").conversor
    ).validos
    bruto.substituir_particao({"session_key": 9673}, {Piloto: pilotos})
    volta_invalida = replace(voltas[0], lap_duration=Decimal("1e30"))  # não cabe em DECIMAL(18, 3)

    with pytest.raises(duckdb.Error):
        bruto.substituir_particao({"session_key": 9673}, {Piloto: [], Volta: [volta_invalida]})

    assert len(bruto.ler(Piloto, {"session_key": 9673})) == 2
    assert bruto.ler(Volta, {"session_key": 9673}) == []


def test_criar_tabelas_acrescenta_coluna_nova_em_tabela_existente(conexao, amostras):
    conexao.execute("CREATE TABLE session_result (session_key INTEGER, driver_number INTEGER)")
    conexao.execute("INSERT INTO session_result VALUES (9606, 1)")

    RepositorioBrutoDuckDB(conexao_fixa(conexao)).criar_tabelas()

    assert conexao.execute("SELECT points, dnf FROM session_result").fetchall() == [(None, None)]


def test_bruto_particao_com_coluna_inexistente_e_recusada(bruto):
    with pytest.raises(ValueError, match="inexistentes"):
        bruto.substituir_particao({"sessao": 1}, {Volta: []})


def test_bruto_tipo_de_outro_repositorio_e_recusado(bruto):
    with pytest.raises(KeyError, match="RitmoPiloto"):
        bruto.ler(RitmoPiloto, {"session_key": 1})


def test_bruto_datas_gravadas_em_utc(bruto, conexao, amostras):
    endpoint = next(e for e in TODOS_ENDPOINTS if e.nome == "laps")
    bruto.substituir_particao(
        {"session_key": 9673}, {Volta: validar(amostras["laps"], endpoint.conversor).validos}
    )

    menor = conexao.execute("SELECT MIN(date_start) FROM laps").fetchone()[0]

    assert menor == datetime(2024, 4, 21, 7, 3, 36, 841000, tzinfo=UTC).replace(tzinfo=None)
    assert bruto.ler(Volta, {"session_key": 9673})[0].date_start.tzinfo is UTC


def test_analitico_grava_tuplas_como_listas(conexao):
    repositorio = RepositorioAnaliticoDuckDB(conexao_fixa(conexao))
    repositorio.criar_tabelas()
    estrategia = EstrategiaPiloto(9673, 1, ("MEDIUM", "HARD"), (13, None), 1, Decimal("22.4"), None)

    repositorio.substituir_particao({"session_key": 9673}, {EstrategiaPiloto: [estrategia]})

    assert repositorio.ler(EstrategiaPiloto, {"session_key": 9673}) == [estrategia]
    assert conexao.execute("SELECT voltas_por_stint FROM estrategia_piloto").fetchone() == (
        [13, None],
    )


def test_quarentena_substitui_rejeitados_da_mesma_particao(conexao):
    agora = datetime(2026, 10, 13, 3, 0, tzinfo=UTC)
    quarentena = RepositorioQuarentenaDuckDB(conexao_fixa(conexao), "exec-1", agora=lambda: agora)
    quarentena.criar_tabela()
    rejeitado = RegistroRejeitado(
        {"lap_number": "x", "nome": "Ação"}, "lap_number: esperado inteiro"
    )

    quarentena.registrar("laps", {"session_key": 9673}, [rejeitado, rejeitado])
    quarentena.registrar("laps", {"session_key": 9673}, [rejeitado])
    quarentena.registrar("laps", {"session_key": 1}, [rejeitado])

    linhas = conexao.execute(
        "SELECT id_execucao, particao, registro, motivo, registrado_em FROM quarentena "
        "WHERE particao = 'session_key=9673'"
    ).fetchall()
    assert len(linhas) == 1
    id_execucao, particao, registro, motivo, registrado_em = linhas[0]
    assert (id_execucao, particao, motivo) == (
        "exec-1",
        "session_key=9673",
        "lap_number: esperado inteiro",
    )
    assert json.loads(registro) == {"lap_number": "x", "nome": "Ação"}
    assert registrado_em == agora.replace(tzinfo=None)


def test_quarentena_lista_vazia_limpa_a_particao(conexao):
    quarentena = RepositorioQuarentenaDuckDB(conexao_fixa(conexao), "exec-1")
    quarentena.criar_tabela()
    quarentena.registrar("laps", {"session_key": 9673}, [RegistroRejeitado({}, "motivo")])

    quarentena.registrar("laps", {"session_key": 9673}, [])

    assert conexao.execute("SELECT COUNT(*) FROM quarentena").fetchone() == (0,)
