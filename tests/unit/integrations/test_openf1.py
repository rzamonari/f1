from datetime import UTC, datetime, timedelta, timezone
from itertools import pairwise

import httpx
import pytest

from f1.domain.consulta import Filtro, Operador, igual
from f1.domain.erros import FonteIndisponivelError, RequisicaoRecusadaError
from f1.integrations.openf1 import (
    ClienteOpenF1,
    dividir_em_janelas,
    formatar_valor,
    montar_query,
)

BASE_URL = "https://api.openf1.org/v1"


def _cliente(handler) -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, transport=httpx.MockTransport(handler))


def _sem_espera(_: float) -> None:
    return None


@pytest.mark.parametrize(
    ("filtros", "esperado"),
    [
        ([igual("session_key", 9159)], "session_key=9159"),
        ([Filtro("speed", Operador.MAIOR_OU_IGUAL, 315)], "speed%3E=315"),
        ([Filtro("interval", Operador.MENOR, 0.005)], "interval%3C0.005"),
        ([igual("driver_number", [4, 81])], "driver_number=4&driver_number=81"),
        ([igual("flag", "BLACK AND WHITE")], "flag=BLACK%20AND%20WHITE"),
        ([igual("session_key", "latest"), igual("year", 2024)], "session_key=latest&year=2024"),
    ],
)
def test_montar_query_operador_no_nome_do_parametro(filtros, esperado):
    assert montar_query(filtros).replace(">", "%3E").replace("<", "%3C") == esperado


def test_montar_query_mantem_operador_sem_codificar():
    assert montar_query([Filtro("speed", Operador.MAIOR_OU_IGUAL, 315)]) == "speed>=315"


def test_formatar_valor_data_vira_iso_utc_sem_fuso():
    fuso = timezone(timedelta(hours=-3))

    assert formatar_valor(datetime(2024, 1, 1, 9, 30, tzinfo=fuso)) == "2024-01-01T12:30:00"


def test_buscar_envia_filtros_na_url_e_devolve_lista():
    urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return httpx.Response(200, json=[{"session_key": 9159}])

    with _cliente(handler) as http:
        registros = ClienteOpenF1(http).buscar(
            "car_data", [igual("session_key", 9159), Filtro("speed", Operador.MAIOR_OU_IGUAL, 315)]
        )

    assert registros == [{"session_key": 9159}]
    assert urls[0].startswith(f"{BASE_URL}/car_data?session_key=9159&speed")
    assert urls[0].endswith("=315")


def test_buscar_sem_filtros_usa_so_o_endpoint():
    urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return httpx.Response(200, json=[])

    with _cliente(handler) as http:
        ClienteOpenF1(http).buscar("meetings", [])

    assert urls == [f"{BASE_URL}/meetings"]


def test_buscar_404_sem_resultados_devolve_lista_vazia():
    resposta = httpx.Response(404, json={"detail": "No results found."})

    with _cliente(lambda request: resposta) as http:
        assert ClienteOpenF1(http).buscar("starting_grid", [igual("session_key", 1)]) == []


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(404, json={"detail": "Not Found"}),
        httpx.Response(404, text="<html>não encontrado</html>"),
        httpx.Response(400, json={"detail": "bad request"}),
        httpx.Response(401),
    ],
    ids=["404-outro", "404-html", "400", "401"],
)
def test_buscar_erro_definitivo_nao_repete_e_preserva_causa(resposta):
    chamadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas.append(request)
        return resposta

    with _cliente(handler) as http, pytest.raises(RequisicaoRecusadaError) as erro:
        ClienteOpenF1(http, dormir=_sem_espera).buscar("laps", [igual("session_key", 1)])

    assert len(chamadas) == 1
    assert isinstance(erro.value.__cause__, httpx.HTTPStatusError)
    assert "/laps" in str(erro.value)


def test_buscar_resposta_que_nao_e_lista_e_recusada():
    with (
        _cliente(lambda request: httpx.Response(200, json={"inesperado": True})) as http,
        pytest.raises(RequisicaoRecusadaError, match="esperada lista"),
    ):
        ClienteOpenF1(http).buscar("laps", [])


def test_buscar_repete_falha_transitoria_com_backoff_exponencial():
    respostas = iter([httpx.Response(503), httpx.Response(502), httpx.Response(200, json=[])])
    esperas: list[float] = []

    with _cliente(lambda request: next(respostas)) as http:
        cliente = ClienteOpenF1(http, backoff_base_s=2.0, dormir=esperas.append)
        assert cliente.buscar("laps", []) == []

    assert esperas == [2.0, 4.0]


def test_buscar_respeita_retry_after_quando_maior_que_o_backoff():
    respostas = iter(
        [httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json=[])]
    )
    esperas: list[float] = []

    with _cliente(lambda request: next(respostas)) as http:
        ClienteOpenF1(http, backoff_base_s=1.0, dormir=esperas.append).buscar("laps", [])

    assert esperas == [7.0]


def test_buscar_ignora_retry_after_invalido():
    respostas = iter(
        [
            httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}),
            httpx.Response(200, json=[]),
        ]
    )
    esperas: list[float] = []

    with _cliente(lambda request: next(respostas)) as http:
        ClienteOpenF1(http, backoff_base_s=1.0, dormir=esperas.append).buscar("laps", [])

    assert esperas == [1.0]


def test_buscar_repete_erro_de_transporte():
    tentativas = iter([httpx.ConnectTimeout("timeout"), None])

    def handler(request: httpx.Request) -> httpx.Response:
        erro = next(tentativas)
        if erro is not None:
            raise erro
        return httpx.Response(200, json=[{"ok": 1}])

    with _cliente(handler) as http:
        assert ClienteOpenF1(http, dormir=_sem_espera).buscar("laps", []) == [{"ok": 1}]


def test_buscar_esgota_tentativas_e_preserva_causa():
    with _cliente(lambda request: httpx.Response(503)) as http:
        cliente = ClienteOpenF1(http, max_tentativas=3, dormir=_sem_espera)
        with pytest.raises(FonteIndisponivelError, match="3 tentativas") as erro:
            cliente.buscar("laps", [])

    assert isinstance(erro.value.__cause__, httpx.HTTPStatusError)


def test_buscar_pausa_entre_requisicoes():
    esperas: list[float] = []

    with _cliente(lambda request: httpx.Response(200, json=[])) as http:
        ClienteOpenF1(http, pausa_entre_requisicoes_s=0.5, dormir=esperas.append).buscar("laps", [])

    assert esperas == [0.5]


def test_cliente_max_tentativas_invalido():
    with (
        _cliente(lambda request: httpx.Response(200, json=[])) as http,
        pytest.raises(ValueError, match="max_tentativas"),
    ):
        ClienteOpenF1(http, max_tentativas=0)


def test_dividir_em_janelas_cobre_intervalo_sem_lacunas_nem_sobreposicao():
    inicio = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    fim = inicio + timedelta(minutes=25)

    janelas = list(dividir_em_janelas(inicio, fim, timedelta(minutes=10)))

    assert janelas[0][0] == inicio
    assert janelas[-1][1] == fim
    assert all(a[1] == b[0] for a, b in pairwise(janelas))
    assert [b - a for a, b in janelas] == [timedelta(minutes=10)] * 2 + [timedelta(minutes=5)]


def test_dividir_em_janelas_intervalo_vazio_nao_gera_janelas():
    instante = datetime(2024, 1, 1, tzinfo=UTC)

    assert list(dividir_em_janelas(instante, instante, timedelta(minutes=1))) == []


def test_dividir_em_janelas_tamanho_invalido():
    instante = datetime(2024, 1, 1, tzinfo=UTC)

    with pytest.raises(ValueError, match="positivo"):
        list(dividir_em_janelas(instante, instante, timedelta(0)))


def test_buscar_em_janelas_gera_um_lote_por_janela_com_filtros_de_data():
    consultas: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        consultas.append(request.url.query.decode())
        return httpx.Response(200, json=[{"n": len(consultas)}])

    inicio = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    with _cliente(handler) as http:
        lotes = list(
            ClienteOpenF1(http).buscar_em_janelas(
                "car_data",
                [igual("session_key", 1)],
                inicio,
                inicio + timedelta(minutes=20),
                timedelta(minutes=10),
            )
        )

    assert lotes == [[{"n": 1}], [{"n": 2}]]
    assert "date%3E=2024-01-01T12%3A00%3A00" in consultas[0].replace(">", "%3E")
    assert "date%3C2024-01-01T12%3A10%3A00" in consultas[0].replace("<", "%3C")
    assert "date%3E=2024-01-01T12%3A10%3A00" in consultas[1].replace(">", "%3E")
