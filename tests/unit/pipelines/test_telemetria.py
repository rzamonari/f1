from datetime import timedelta

import pytest

from f1.domain.erros import TaxaRejeicaoExcedidaError
from f1.domain.modelos import DadosCarro, Localizacao
from f1.pipelines.telemetria import ParametrosTelemetria, executar_telemetria

PARAMETROS = ParametrosTelemetria(limite_taxa_rejeicao=0.05, tamanho_janela=timedelta(minutes=10))


def test_telemetria_grava_cada_piloto_em_sua_particao(
    amostras, criar_fonte, banco, quarentena, fabrica_sessao
):
    fonte = criar_fonte({"car_data": amostras["car_data"], "location": amostras["location"]})

    resumo = executar_telemetria(fabrica_sessao(), [1], fonte, banco, quarentena, PARAMETROS)

    particao = {"session_key": 9673, "driver_number": 1}
    assert len(banco.ler(DadosCarro, particao)) == 4
    assert len(banco.ler(Localizacao, particao)) == 3
    assert [(p, c.endpoint, c.validos) for p, c in resumo.contagens] == [
        (1, "car_data", 4),
        (1, "location", 3),
    ]


def test_telemetria_consulta_por_sessao_e_piloto(
    amostras, criar_fonte, banco, quarentena, fabrica_sessao
):
    fonte = criar_fonte(
        {"car_data": amostras["car_data"], "location": amostras["location"]},
        filtrar_por_igualdade=True,
    )

    executar_telemetria(fabrica_sessao(), [1, 4], fonte, banco, quarentena, PARAMETROS)

    filtros = [{(f.campo, f.valor) for f in filtros} for _, filtros in fonte.chamadas]
    assert filtros[0] == {("session_key", 9673), ("driver_number", 1)}
    assert filtros[-1] == {("session_key", 9673), ("driver_number", 4)}
    assert banco.escritas == 2


def test_telemetria_reexecucao_produz_mesmo_estado(
    amostras, criar_fonte, banco, quarentena, fabrica_sessao
):
    fonte = criar_fonte({"car_data": amostras["car_data"], "location": amostras["location"]})

    executar_telemetria(fabrica_sessao(), [1], fonte, banco, quarentena, PARAMETROS)
    primeira = {m: list(r) for m, r in banco.tabelas.items()}
    executar_telemetria(fabrica_sessao(), [1], fonte, banco, quarentena, PARAMETROS)

    assert banco.tabelas == primeira


def test_telemetria_taxa_rejeicao_alta_interrompe_antes_de_gravar_o_piloto(
    amostras, criar_fonte, banco, quarentena, fabrica_sessao
):
    invalidos = [{**r, "speed": "rápido"} for r in amostras["car_data"]]
    fonte = criar_fonte({"car_data": invalidos, "location": amostras["location"]})

    with pytest.raises(TaxaRejeicaoExcedidaError, match="car_data"):
        executar_telemetria(fabrica_sessao(), [1], fonte, banco, quarentena, PARAMETROS)

    assert banco.escritas == 0
    assert quarentena.total == 4
