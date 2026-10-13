from datetime import UTC, datetime
from decimal import Decimal

import pytest

from f1.domain.endpoints import ENDPOINTS_SESSAO, TODOS_ENDPOINTS
from f1.domain.modelos import Intervalo, Piloto, PitStop, ResultadoSessao, Stint, Volta
from f1.domain.tipos import GAP_LIDER, Composto, Gap
from f1.domain.validacao import (
    ContratoInvalidoError,
    converter_gap,
    criar_conversor,
    desdobrar_fases_quali,
    validar,
)

ENDPOINT = {e.nome: e for e in TODOS_ENDPOINTS}
AMOSTRA_POR_ENDPOINT = {
    "meetings": "meetings",
    "sessions": "sessions",
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
    "car_data": "car_data",
    "location": "location",
}

INTERVALO = {
    "date": "2024-09-22T11:07:02.573000+00:00",
    "session_key": 9606,
    "meeting_key": 1246,
    "driver_number": 4,
    "gap_to_leader": 1.5,
    "interval": 0.75,
}


def test_amostras_cobrem_todos_os_endpoints():
    assert set(AMOSTRA_POR_ENDPOINT) == set(ENDPOINT)


@pytest.mark.parametrize(("endpoint", "amostra"), sorted(AMOSTRA_POR_ENDPOINT.items()))
def test_validar_amostras_reais_da_openf1_sem_rejeicoes(amostras, endpoint, amostra):
    especificacao = ENDPOINT[endpoint]

    resultado = validar(amostras[amostra], especificacao.conversor)

    assert resultado.rejeitados == ()
    assert len(resultado.validos) == len(amostras[amostra]) > 0
    assert all(isinstance(v, especificacao.modelo) for v in resultado.validos)


def test_converter_volta_converte_tipos_e_datas_em_utc(amostras):
    volta = criar_conversor(Volta)(amostras["laps"][0])

    assert volta.lap_duration == Decimal("101.91")
    assert volta.date_start == datetime(2024, 4, 21, 7, 3, 36, 841000, tzinfo=UTC)
    assert volta.segments_sector_1 is not None
    assert volta.segments_sector_1[0] is None
    assert volta.is_pit_out_lap is False


def test_converter_data_sem_fuso_assume_utc():
    registro = {**INTERVALO, "date": "2024-09-22T11:07:02"}

    intervalo = criar_conversor(Intervalo)(registro)

    assert intervalo.date.tzinfo is UTC


def test_converter_data_com_outro_fuso_normaliza_para_utc():
    registro = {**INTERVALO, "date": "2024-09-22T14:07:02-03:00"}

    intervalo = criar_conversor(Intervalo)(registro)

    assert intervalo.date == datetime(2024, 9, 22, 17, 7, 2, tzinfo=UTC)


def test_converter_piloto_ignora_campo_depreciado_country_code(amostras):
    piloto = criar_conversor(Piloto)(amostras["drivers"][0])

    assert not hasattr(piloto, "country_code")


def test_converter_pit_sem_stop_duration_aceita_nulo(amostras):
    registro = {k: v for k, v in amostras["pit"][0].items() if k != "stop_duration"}

    pit = criar_conversor(PitStop)(registro)

    assert pit.stop_duration is None
    assert pit.lane_duration == Decimal("22.4")


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (1.5, Gap(segundos=Decimal("1.5"))),
        (0, GAP_LIDER),
        ("+1 LAP", Gap(voltas=1)),
        ("+3 LAPS", Gap(voltas=3)),
    ],
)
def test_converter_gap_valores_da_api(valor, esperado):
    assert converter_gap(valor) == esperado


@pytest.mark.parametrize("valor", ["+1 VOLTA", "DNF", True, [1.0]])
def test_converter_gap_invalido_lanca_erro(valor):
    with pytest.raises(ContratoInvalidoError):
        converter_gap(valor)


def test_converter_intervalo_nulo_representa_o_lider():
    registro = {**INTERVALO, "gap_to_leader": None, "interval": None}

    intervalo = criar_conversor(Intervalo)(registro)

    assert intervalo.gap_to_leader.eh_lider
    assert intervalo.interval.eh_lider


def test_converter_intervalo_retardatario_em_voltas():
    intervalo = criar_conversor(Intervalo)({**INTERVALO, "gap_to_leader": "+1 LAP"})

    assert intervalo.gap_to_leader == Gap(voltas=1)
    assert not intervalo.gap_to_leader.eh_lider


@pytest.mark.parametrize(
    ("sobrescrita", "mensagem"),
    [
        ({"driver_number": "4"}, "driver_number: esperado inteiro"),
        ({"driver_number": True}, "booleano"),
        ({"driver_number": 4.5}, "esperado inteiro"),
        ({"date": "22/09/2024"}, "data inválida"),
        ({"date": 20240922}, "esperado texto"),
        ({"gap_to_leader": "NaN"}, "gap inválido"),
        ({"interval": float("inf")}, "não finito"),
    ],
)
def test_converter_valores_fora_do_contrato_lanca_erro(sobrescrita, mensagem):
    with pytest.raises(ContratoInvalidoError, match=mensagem):
        criar_conversor(Intervalo)({**INTERVALO, **sobrescrita})


def test_converter_campo_obrigatorio_ausente_informa_campo():
    registro = {k: v for k, v in INTERVALO.items() if k != "driver_number"}

    with pytest.raises(ContratoInvalidoError, match="driver_number"):
        criar_conversor(Intervalo)(registro)


def test_converter_registro_que_nao_e_objeto_lanca_erro():
    with pytest.raises(ContratoInvalidoError, match="objeto JSON"):
        criar_conversor(Intervalo)(["não", "é", "objeto"])


@pytest.mark.parametrize(
    ("compound", "esperado"),
    [("SOFT", Composto.SOFT), (None, None), ("TEST_UNKNOWN", Composto.TEST_UNKNOWN)],
)
def test_converter_stint_compostos(amostras, compound, esperado):
    stint = criar_conversor(Stint)({**amostras["stints"][0], "compound": compound})

    assert stint.compound == esperado


def test_converter_stint_composto_desconhecido_lanca_erro(amostras):
    with pytest.raises(ContratoInvalidoError, match="Composto"):
        criar_conversor(Stint)({**amostras["stints"][0], "compound": "ULTRASOFT"})


def test_converter_lista_com_item_invalido_lanca_erro(amostras):
    with pytest.raises(ContratoInvalidoError, match="segments_sector_1"):
        criar_conversor(Volta)({**amostras["laps"][0], "segments_sector_1": [2049, "x"]})


def test_converter_lista_que_nao_e_lista_lanca_erro(amostras):
    with pytest.raises(ContratoInvalidoError, match="esperada lista"):
        criar_conversor(Volta)({**amostras["laps"][0], "segments_sector_1": 2049})


def test_converter_bool_com_valor_padrao_quando_nulo(amostras):
    volta = criar_conversor(Volta)({**amostras["laps"][0], "is_pit_out_lap": None})

    assert volta.is_pit_out_lap is False


def test_converter_bool_invalido_lanca_erro(amostras):
    with pytest.raises(ContratoInvalidoError, match="booleano"):
        criar_conversor(Volta)({**amostras["laps"][0], "is_pit_out_lap": "sim"})


def test_resultado_quali_desdobra_fases_q1_q2_q3(amostras):
    conversor = next(e.conversor for e in ENDPOINTS_SESSAO if e.nome == "session_result")

    registro = next(r for r in amostras["session_result_quali"] if r["position"] == 2)

    resultado = conversor(registro)

    assert isinstance(resultado, ResultadoSessao)
    assert resultado.duration is None
    assert resultado.duration_q1 is not None
    assert resultado.duration_q3 is not None
    assert resultado.gap_to_leader_q3 is not None
    assert resultado.gap_to_leader_q3.segundos == Decimal("0.203")


def test_resultado_corrida_mantem_duracao_escalar(amostras):
    conversor = next(e.conversor for e in ENDPOINTS_SESSAO if e.nome == "session_result")

    registro = next(r for r in amostras["session_result_race"] if r["position"] == 7)

    resultado = conversor(registro)

    assert resultado.duration == Decimal("6148.61")
    assert resultado.duration_q1 is None
    assert resultado.points == Decimal("6.0")


def test_desdobrar_fases_quali_eliminado_no_q1_tem_fases_nulas():
    registro = {"duration": [91.2, None, None], "gap_to_leader": [1.1, None, None]}

    desdobrado = desdobrar_fases_quali(registro)

    assert desdobrado["duration"] is None
    assert desdobrado["duration_q1"] == 91.2
    assert desdobrado["duration_q2"] is None
    assert desdobrado["gap_to_leader_q1"] == 1.1


def test_desdobrar_fases_quali_mais_de_tres_fases_lanca_erro():
    with pytest.raises(ContratoInvalidoError, match="três fases"):
        desdobrar_fases_quali({"duration": [1, 2, 3, 4]})


def test_validar_separa_validos_e_rejeitados_com_motivo():
    resultado = validar([INTERVALO, {**INTERVALO, "date": "x"}], criar_conversor(Intervalo))

    assert len(resultado.validos) == 1
    assert len(resultado.rejeitados) == 1
    assert "data inválida" in resultado.rejeitados[0].motivo
    assert resultado.taxa_rejeicao == 0.5


def test_validar_entrada_vazia_tem_taxa_zero():
    resultado = validar([], criar_conversor(Intervalo))

    assert resultado.validos == ()
    assert resultado.taxa_rejeicao == 0.0


def test_criar_conversor_tipo_sem_regra_e_erro_de_programacao():
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class ModeloInvalido:
        campo: complex

    with pytest.raises(TypeError, match="sem regra de conversão"):
        criar_conversor(ModeloInvalido)
