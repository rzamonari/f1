from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from f1.domain.erros import FonteIndisponivelError
from f1.domain.tipos import TipoSessao
from f1.pipelines.sessao import ParametrosSessao
from f1.pipelines.temporada import DestinosTemporada, executar_temporada

AGORA = datetime(2026, 10, 13, tzinfo=UTC)
PARAMETROS = ParametrosSessao(
    limite_taxa_rejeicao=0.05, margem_apos_sessao=timedelta(hours=1), agora=lambda: AGORA
)


class FonteComFalha:
    """Delega para a fonte fake, mas falha nas consultas de uma sessão específica."""

    def __init__(self, fonte, session_key_com_falha):
        self._fonte = fonte
        self._falha = session_key_com_falha

    def buscar(self, endpoint, filtros):
        if any(f.campo == "session_key" and f.valor == self._falha for f in filtros):
            raise FonteIndisponivelError("API fora do ar")
        return self._fonte.buscar(endpoint, filtros)

    def buscar_em_janelas(self, *args):
        return self._fonte.buscar_em_janelas(*args)


@pytest.fixture
def sessoes_brutas(amostras):
    base = amostras["sessions"][0]
    return [
        base,
        {
            **base,
            "session_key": 2,
            "date_start": "2024-05-01T10:00:00+00:00",
            "date_end": "2024-05-01T12:00:00+00:00",
        },
        {**base, "session_key": 3, "is_cancelled": True},
        {**base, "session_key": 4, "date_end": "2026-10-13T00:30:00+00:00"},
        {**base, "session_key": 5, "session_type": "Qualifying"},
    ]


def _destinos(banco, quarentena):
    return DestinosTemporada(banco, banco, banco, quarentena)


def test_temporada_processa_sessoes_do_tipo_e_pula_indisponiveis(
    amostras, sessoes_brutas, criar_fonte, banco, quarentena
):
    fonte = criar_fonte({"meetings": amostras["meetings"], "sessions": sessoes_brutas})

    resumo = executar_temporada(
        2024, TipoSessao.RACE, fonte, _destinos(banco, quarentena), PARAMETROS
    )

    assert resumo.processadas == (9673, 2)
    assert resumo.puladas == (3, 4)
    assert resumo.falhas == ()


def test_temporada_isola_falha_de_uma_sessao_e_segue(
    amostras, sessoes_brutas, criar_fonte, banco, quarentena
):
    fonte = FonteComFalha(
        criar_fonte({"meetings": amostras["meetings"], "sessions": sessoes_brutas}),
        session_key_com_falha=9673,
    )

    resumo = executar_temporada(
        2024, TipoSessao.RACE, fonte, _destinos(banco, quarentena), PARAMETROS
    )

    assert resumo.processadas == (2,)
    assert [f.session_key for f in resumo.falhas] == [9673]
    assert "fora do ar" in resumo.falhas[0].motivo


def test_temporada_filtra_pelo_tipo(amostras, sessoes_brutas, criar_fonte, banco, quarentena):
    fonte = criar_fonte({"meetings": amostras["meetings"], "sessions": sessoes_brutas})

    resumo = executar_temporada(
        2024, TipoSessao.QUALIFYING, fonte, _destinos(banco, quarentena), replace(PARAMETROS)
    )

    assert resumo.processadas == (5,)
