from datetime import timedelta

import pytest

from f1.domain.endpoints import ENDPOINTS_SESSAO
from f1.domain.erros import SessaoIndisponivelError, TaxaRejeicaoExcedidaError
from f1.domain.modelos import Intervalo, Piloto, Volta
from f1.domain.tipos import TipoSessao
from f1.pipelines.sessao import (
    ParametrosSessao,
    executar_sessao,
    obter_sessao,
    resolver_session_key,
    verificar_disponibilidade,
)

AMOSTRA_POR_ENDPOINT = {
    "drivers": "drivers",
    "laps": "laps",
    "stints": "stints",
    "pit": "pit",
    "session_result": "session_result_race",
    "starting_grid": "starting_grid",
    "weather": "weather",
    "race_control": "race_control_sc",
    "position": "position",
    "intervals": "intervals",
    "overtakes": "overtakes",
    "team_radio": "team_radio",
    "championship_drivers": "championship_drivers",
    "championship_teams": "championship_teams",
}


@pytest.fixture
def respostas(amostras):
    # Algumas amostras vêm de outras sessões; todas passam a pertencer à sessão 9673.
    return {
        endpoint: [{**r, "session_key": 9673} for r in amostras[chave]]
        for endpoint, chave in AMOSTRA_POR_ENDPOINT.items()
    }


def parametros(sessao, depois_do_fim=timedelta(hours=2), margem=timedelta(hours=1), limite=0.05):
    return ParametrosSessao(
        limite_taxa_rejeicao=limite,
        margem_apos_sessao=margem,
        agora=lambda: sessao.date_end + depois_do_fim,
    )


def test_executar_sessao_grava_todos_os_endpoints_na_particao(
    respostas, criar_fonte, banco, quarentena, fabrica_sessao
):
    sessao = fabrica_sessao()

    resumo = executar_sessao(sessao, criar_fonte(respostas), banco, quarentena, parametros(sessao))

    assert [c.endpoint for c in resumo.contagens] == [e.nome for e in ENDPOINTS_SESSAO]
    assert all(c.rejeitados == 0 for c in resumo.contagens)
    assert resumo.pilotos == (1, 4)
    assert len(banco.ler(Volta, {"session_key": 9673})) == 3
    assert banco.escritas == 1


def test_executar_sessao_reexecucao_produz_mesmo_estado(
    respostas, criar_fonte, banco, quarentena, fabrica_sessao
):
    sessao = fabrica_sessao()
    fonte = criar_fonte(respostas)

    executar_sessao(sessao, fonte, banco, quarentena, parametros(sessao))
    primeira = {m: list(r) for m, r in banco.tabelas.items()}
    executar_sessao(sessao, fonte, banco, quarentena, parametros(sessao))

    assert banco.tabelas == primeira


@pytest.mark.parametrize("tipo", [TipoSessao.PRACTICE, TipoSessao.QUALIFYING])
def test_executar_sessao_pula_endpoints_so_de_corrida(
    respostas, criar_fonte, banco, quarentena, fabrica_sessao, tipo
):
    sessao = fabrica_sessao(session_type=tipo)
    fonte = criar_fonte(respostas)

    resumo = executar_sessao(sessao, fonte, banco, quarentena, parametros(sessao))

    consultados = {endpoint for endpoint, _ in fonte.chamadas}
    so_corrida = {e.nome for e in ENDPOINTS_SESSAO if e.so_corrida}
    assert consultados.isdisjoint(so_corrida)
    assert {c.endpoint for c in resumo.contagens}.isdisjoint(so_corrida)
    assert banco.ler(Intervalo, {"session_key": 9673}) == []


def test_executar_sessao_endpoint_vazio_segue_com_aviso(
    respostas, criar_fonte, banco, quarentena, fabrica_sessao, caplog
):
    sessao = fabrica_sessao()
    respostas["team_radio"] = []

    resumo = executar_sessao(sessao, criar_fonte(respostas), banco, quarentena, parametros(sessao))

    contagem = next(c for c in resumo.contagens if c.endpoint == "team_radio")
    assert contagem.lidos == 0
    assert "endpoint sem dados para a partição" in caplog.text


def test_executar_sessao_taxa_rejeicao_alta_interrompe_sem_gravar_nada(
    respostas, criar_fonte, banco, quarentena, fabrica_sessao
):
    sessao = fabrica_sessao()
    respostas["laps"] = [{**v, "lap_number": "um"} for v in respostas["laps"]]

    with pytest.raises(TaxaRejeicaoExcedidaError, match="laps"):
        executar_sessao(sessao, criar_fonte(respostas), banco, quarentena, parametros(sessao))

    assert banco.escritas == 0
    assert len(quarentena.particoes[("laps", (("session_key", 9673),))]) == 3


def test_executar_sessao_rejeita_registro_de_outra_sessao(
    respostas, criar_fonte, banco, quarentena, fabrica_sessao
):
    sessao = fabrica_sessao()
    respostas["laps"] = [*respostas["laps"], {**respostas["laps"][0], "session_key": 1}]

    executar_sessao(
        sessao, criar_fonte(respostas), banco, quarentena, parametros(sessao, limite=0.5)
    )

    rejeitados = quarentena.particoes[("laps", (("session_key", 9673),))]
    assert [r.motivo for r in rejeitados] == ["session_key=1 fora da partição session_key=9673"]
    assert len(banco.ler(Volta, {"session_key": 9673})) == 3


def test_executar_sessao_quarentena_e_limpa_no_reprocessamento(
    respostas, criar_fonte, banco, quarentena, fabrica_sessao
):
    sessao = fabrica_sessao()
    com_rejeicao = {**respostas, "laps": [*respostas["laps"], {"lap_number": "x"}]}
    executar_sessao(
        sessao, criar_fonte(com_rejeicao), banco, quarentena, parametros(sessao, limite=0.5)
    )

    executar_sessao(sessao, criar_fonte(respostas), banco, quarentena, parametros(sessao))

    assert quarentena.total == 0


def test_executar_sessao_cancelada_nao_consulta_a_api(
    criar_fonte, banco, quarentena, fabrica_sessao
):
    sessao = fabrica_sessao(is_cancelled=True)
    fonte = criar_fonte()

    with pytest.raises(SessaoIndisponivelError, match="cancelada"):
        executar_sessao(sessao, fonte, banco, quarentena, parametros(sessao))

    assert fonte.chamadas == []


@pytest.mark.parametrize(
    ("depois_do_fim", "disponivel"),
    [(timedelta(minutes=59), False), (timedelta(minutes=60), True), (timedelta(days=1), True)],
)
def test_verificar_disponibilidade_respeita_margem_apos_a_sessao(
    fabrica_sessao, depois_do_fim, disponivel
):
    sessao = fabrica_sessao()
    params = parametros(sessao, depois_do_fim=depois_do_fim, margem=timedelta(minutes=60))

    if disponivel:
        verificar_disponibilidade(sessao, params)
    else:
        with pytest.raises(SessaoIndisponivelError, match="só pode ser ingerida após"):
            verificar_disponibilidade(sessao, params)


def test_obter_sessao_valida_metadados(amostras, criar_fonte):
    sessao = obter_sessao(9673, criar_fonte({"sessions": amostras["sessions"]}))

    assert sessao.session_key == 9673
    assert sessao.session_type is TipoSessao.RACE


@pytest.mark.parametrize("registros", [[], [{"session_key": "x"}]], ids=["inexistente", "invalida"])
def test_obter_sessao_inexistente_ou_invalida(criar_fonte, registros):
    with pytest.raises(SessaoIndisponivelError, match="9999"):
        obter_sessao(9999, criar_fonte({"sessions": registros}))


def test_resolver_session_key_numero_nao_consulta_api(criar_fonte):
    fonte = criar_fonte()

    assert resolver_session_key("9159", fonte) == 9159
    assert fonte.chamadas == []


def test_resolver_session_key_latest_resolve_antes_da_execucao(amostras, criar_fonte):
    fonte = criar_fonte({"sessions": amostras["sessions"]})

    assert resolver_session_key("latest", fonte) == 9673
    assert fonte.chamadas[0][1][0].valor == "latest"


@pytest.mark.parametrize(
    "registros", [[], [{"session_key": 1}, {"session_key": 2}], [{"session_key": "x"}]]
)
def test_resolver_session_key_latest_sem_resposta_unica(criar_fonte, registros):
    with pytest.raises(SessaoIndisponivelError):
        resolver_session_key("latest", criar_fonte({"sessions": registros}))


def test_resolver_session_key_texto_invalido(criar_fonte):
    with pytest.raises(ValueError, match="invalid literal"):
        resolver_session_key("ontem", criar_fonte())


def test_resumo_lista_pilotos_da_sessao(respostas, criar_fonte, banco, quarentena, fabrica_sessao):
    sessao = fabrica_sessao()

    executar_sessao(sessao, criar_fonte(respostas), banco, quarentena, parametros(sessao))

    assert {p.name_acronym for p in banco.ler(Piloto, {"session_key": 9673})} == {"VER", "NOR"}
