from datetime import timedelta
from decimal import Decimal

from f1.domain.analitico import EstrategiaPiloto, RitmoPiloto, TelemetriaVolta
from f1.domain.modelos import DadosCarro, Stint
from f1.domain.tipos import Composto
from f1.pipelines.analitico import executar_analitico

PARTICAO = {"session_key": 9673}


def _popular(banco, fabrica_volta):
    voltas = [
        fabrica_volta(lap_number=1, lap_duration=Decimal("100")),
        fabrica_volta(
            lap_number=2,
            date_start=fabrica_volta().date_start + timedelta(seconds=100),
            lap_duration=Decimal("98"),
        ),
    ]
    amostra = DadosCarro(
        9673, 1233, voltas[0].date_start + timedelta(seconds=5), 1, 300, 11000, 8, 100, 0, 12
    )
    banco.substituir_particao(PARTICAO, {Stint: [Stint(9673, 1233, 1, 1, Composto.SOFT, 1, 2, 0)]})
    banco.substituir_particao(PARTICAO, {type(voltas[0]): voltas})
    banco.substituir_particao({**PARTICAO, "driver_number": 1}, {DadosCarro: [amostra]})


def test_analitico_calcula_e_grava_as_tres_tabelas(banco, fabrica_volta):
    _popular(banco, fabrica_volta)

    resumo = executar_analitico(9673, banco, banco)

    assert (resumo.ritmo, resumo.estrategia, resumo.telemetria) == (1, 1, 1)
    ritmo = banco.ler(RitmoPiloto, PARTICAO)[0]
    assert ritmo.melhor_volta_s == Decimal("98")
    assert banco.ler(EstrategiaPiloto, PARTICAO)[0].compostos == ("SOFT",)
    assert banco.ler(TelemetriaVolta, PARTICAO)[0].drs_aberto_pct == 100.0


def test_analitico_reexecucao_produz_mesmo_estado(banco, fabrica_volta):
    _popular(banco, fabrica_volta)

    executar_analitico(9673, banco, banco)
    primeira = {m: list(r) for m, r in banco.tabelas.items()}
    executar_analitico(9673, banco, banco)

    assert banco.tabelas == primeira


def test_analitico_sessao_sem_dados_grava_particoes_vazias(banco, caplog):
    resumo = executar_analitico(1, banco, banco)

    assert (resumo.ritmo, resumo.estrategia, resumo.telemetria) == (0, 0, 0)
    assert "sessão sem voltas" in caplog.text
