import pytest

from f1.domain.erros import TaxaRejeicaoExcedidaError
from f1.domain.modelos import Meeting, Sessao
from f1.pipelines.catalogo import executar_catalogo


def test_catalogo_grava_meetings_e_sessoes_na_particao_do_ano(
    amostras, criar_fonte, banco, quarentena
):
    fonte = criar_fonte({"meetings": amostras["meetings"], "sessions": amostras["sessions"]})

    resumo = executar_catalogo(2024, fonte, banco, quarentena, limite_taxa_rejeicao=0.05)

    assert len(resumo.meetings) == 1
    assert len(resumo.sessoes) == 1
    assert [type(m) for m in banco.ler(Meeting, {"year": 2024})] == [Meeting]
    assert [s.session_key for s in banco.ler(Sessao, {"year": 2024})] == [9673]
    assert [c.endpoint for c in resumo.contagens] == ["meetings", "sessions"]
    assert fonte.chamadas[0][0] == "meetings"


def test_catalogo_reexecucao_produz_mesmo_estado(amostras, criar_fonte, banco, quarentena):
    fonte = criar_fonte({"meetings": amostras["meetings"], "sessions": amostras["sessions"]})

    executar_catalogo(2024, fonte, banco, quarentena, limite_taxa_rejeicao=0.05)
    primeira = {m: list(r) for m, r in banco.tabelas.items()}
    executar_catalogo(2024, fonte, banco, quarentena, limite_taxa_rejeicao=0.05)

    assert banco.tabelas == primeira


def test_catalogo_rejeitados_vao_para_quarentena_e_seguem(amostras, criar_fonte, banco, quarentena):
    invalida = {**amostras["sessions"][0], "session_type": "Desconhecido"}
    fonte = criar_fonte(
        {"meetings": amostras["meetings"], "sessions": [*amostras["sessions"], invalida]}
    )

    resumo = executar_catalogo(2024, fonte, banco, quarentena, limite_taxa_rejeicao=0.6)

    assert len(resumo.sessoes) == 1
    assert len(quarentena.particoes[("sessions", (("year", 2024),))]) == 1


def test_catalogo_taxa_rejeicao_acima_do_limite_interrompe_sem_gravar(
    amostras, criar_fonte, banco, quarentena
):
    invalida = {**amostras["sessions"][0], "date_start": "ontem"}
    fonte = criar_fonte({"meetings": amostras["meetings"], "sessions": [invalida]})

    with pytest.raises(TaxaRejeicaoExcedidaError, match="sessions"):
        executar_catalogo(2024, fonte, banco, quarentena, limite_taxa_rejeicao=0.05)

    assert banco.escritas == 0
    assert quarentena.total == 1
