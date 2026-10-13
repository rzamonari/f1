"""CLI de ponta a ponta: DuckDB real em ``tmp_path`` e OpenF1 simulada (sem rede)."""

import logging
from datetime import UTC, datetime
from urllib.parse import unquote

import duckdb
import httpx
import pytest

from f1 import cli

pytestmark = pytest.mark.integration

AMOSTRA_POR_ENDPOINT = {
    "meetings": "meetings",
    "sessions": "sessions",
    "drivers": "drivers",
    "laps": "laps",
    "stints": "stints",
    "pit": "pit",
    "session_result": "session_result_race",
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


@pytest.fixture(autouse=True)
def raiz_restaurada():
    raiz = logging.getLogger()
    handlers, nivel = list(raiz.handlers), raiz.level
    yield
    raiz.handlers[:] = handlers
    raiz.setLevel(nivel)


@pytest.fixture
def banco(tmp_path, monkeypatch):
    caminho = tmp_path / "dados" / "f1.duckdb"
    monkeypatch.setenv("F1_AMBIENTE", "dev")
    monkeypatch.setenv("F1_CAMINHO_BANCO", str(caminho))
    monkeypatch.setenv("F1_PAUSA_ENTRE_REQUISICOES_S", "0")
    return caminho


def _dentro_da_janela(request: httpx.Request, registro: dict[str, object]) -> bool:
    """Aplica os filtros ``date>=`` e ``date<`` da query, como a API real."""
    instante = datetime.fromisoformat(str(registro.get("date")))
    for parte in request.url.query.decode().split("&"):
        texto = unquote(parte)
        for operador in (">=", "<"):
            prefixo = f"date{operador}"
            if texto.startswith(prefixo):
                limite = datetime.fromisoformat(texto.removeprefix(prefixo)).replace(tzinfo=UTC)
                if (operador == ">=" and instante < limite) or (
                    operador == "<" and instante >= limite
                ):
                    return False
    return True


@pytest.fixture
def openf1_simulada(amostras, monkeypatch):
    """Substitui o transporte do httpx: cada endpoint responde com a amostra da sessão 9673."""

    def responder(request: httpx.Request) -> httpx.Response:
        endpoint = request.url.path.rsplit("/", 1)[-1]
        registros = amostras.get(AMOSTRA_POR_ENDPOINT.get(endpoint, ""), [])
        if not registros:
            return httpx.Response(404, json={"detail": "No results found."})
        if endpoint in {"meetings", "sessions"}:
            return httpx.Response(200, json=registros)
        pilotos = {int(p) for p in request.url.params.get_list("driver_number")}
        return httpx.Response(
            200,
            json=[
                {**r, "session_key": 9673}
                for r in registros
                if (not pilotos or r.get("driver_number") in pilotos)
                and (endpoint not in {"car_data", "location"} or _dentro_da_janela(request, r))
            ],
        )

    cliente_original = httpx.Client

    def cliente_simulado(**kwargs):
        return cliente_original(transport=httpx.MockTransport(responder), **kwargs)

    monkeypatch.setattr(cli.httpx, "Client", cliente_simulado)


def _contar(caminho, tabela):
    with duckdb.connect(str(caminho), read_only=True) as conexao:
        return conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]  # noqa: S608 - nome fixo do teste


@pytest.mark.usefixtures("openf1_simulada")
def test_cli_catalogo_e_idempotente(banco):
    assert cli.main(["catalogo", "--ano", "2024"]) == 0
    assert cli.main(["catalogo", "--ano", "2024"]) == 0

    assert _contar(banco, "meetings") == 1
    assert _contar(banco, "sessions") == 1


@pytest.mark.usefixtures("openf1_simulada")
def test_cli_sessao_com_telemetria_e_analitico(banco):
    assert cli.main(["sessao", "--session-key", "9673", "--com-telemetria"]) == 0
    assert cli.main(["sessao", "--session-key", "9673", "--com-telemetria"]) == 0
    assert cli.main(["analitico", "--session-key", "9673"]) == 0

    assert _contar(banco, "laps") == 3
    assert _contar(banco, "starting_grid") == 0
    assert _contar(banco, "car_data") == 4
    assert _contar(banco, "quarentena") == 0
    assert _contar(banco, "ritmo_piloto") == 1
    assert _contar(banco, "estrategia_piloto") == 1


@pytest.mark.usefixtures("openf1_simulada")
def test_cli_sessao_inexistente_retorna_1(banco, amostras):
    amostras["sessions"] = []

    assert cli.main(["sessao", "--session-key", "1"]) == 1
