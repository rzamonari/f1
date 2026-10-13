from datetime import timedelta
from pathlib import Path

import pytest

from f1.config.settings import (
    Ambiente,
    Configuracao,
    ConfiguracaoInvalidaError,
    carregar_configuracao,
)

MINIMO = {"F1_AMBIENTE": "dev", "F1_CAMINHO_BANCO": "dados/f1.duckdb"}


def test_carregar_configuracao_minima_usa_padroes():
    configuracao = carregar_configuracao(MINIMO)

    assert configuracao == Configuracao(
        ambiente=Ambiente.DEV, caminho_banco=Path("dados/f1.duckdb")
    )
    assert configuracao.api_base_url == "https://api.openf1.org/v1"
    assert configuracao.janela_telemetria == timedelta(minutes=10)


def test_carregar_configuracao_completa():
    env = {
        **MINIMO,
        "F1_AMBIENTE": "prd",
        "F1_API_BASE_URL": "https://exemplo.test/v1",
        "F1_TIMEOUT_S": "10",
        "F1_MAX_TENTATIVAS": "2",
        "F1_PAUSA_ENTRE_REQUISICOES_S": "0",
        "F1_JANELA_TELEMETRIA_MIN": "5",
        "F1_LIMITE_TAXA_REJEICAO": "0.1",
        "F1_MARGEM_APOS_SESSAO_MIN": "30",
        "F1_NIVEL_LOG": "debug",
    }

    configuracao = carregar_configuracao(env)

    assert configuracao.ambiente is Ambiente.PRD
    assert configuracao.timeout_s == 10.0
    assert configuracao.max_tentativas == 2
    assert configuracao.pausa_entre_requisicoes_s == 0.0
    assert configuracao.janela_telemetria == timedelta(minutes=5)
    assert configuracao.limite_taxa_rejeicao == 0.1
    assert configuracao.margem_apos_sessao == timedelta(minutes=30)
    assert configuracao.nivel_log == "DEBUG"


@pytest.mark.parametrize("ausente", ["F1_AMBIENTE", "F1_CAMINHO_BANCO"])
def test_carregar_configuracao_variavel_obrigatoria_ausente(ausente):
    env = {k: v for k, v in MINIMO.items() if k != ausente}

    with pytest.raises(ConfiguracaoInvalidaError, match=ausente):
        carregar_configuracao(env)


@pytest.mark.parametrize(
    ("variavel", "valor"),
    [
        ("F1_AMBIENTE", "producao"),
        ("F1_TIMEOUT_S", "rapido"),
        ("F1_TIMEOUT_S", "0"),
        ("F1_MAX_TENTATIVAS", "0"),
        ("F1_MAX_TENTATIVAS", "1.5"),
        ("F1_PAUSA_ENTRE_REQUISICOES_S", "-1"),
        ("F1_JANELA_TELEMETRIA_MIN", "0"),
        ("F1_LIMITE_TAXA_REJEICAO", "1.5"),
        ("F1_MARGEM_APOS_SESSAO_MIN", "-5"),
        ("F1_NIVEL_LOG", "VERBOSE"),
        ("F1_API_BASE_URL", "ftp://exemplo"),
    ],
)
def test_carregar_configuracao_valor_invalido_cita_so_o_nome(variavel, valor):
    with pytest.raises(ConfiguracaoInvalidaError, match=variavel) as erro:
        carregar_configuracao({**MINIMO, variavel: valor})

    assert valor not in str(erro.value)


def test_configuracao_nao_expoe_senha_no_repr():
    configuracao = carregar_configuracao(
        {**MINIMO, "F1_OPENF1_USUARIO": "usuario-ficticio", "F1_OPENF1_SENHA": "senha-ficticia"}
    )

    assert configuracao.openf1_senha == "senha-ficticia"
    assert "senha-ficticia" not in repr(configuracao)
    assert "usuario-ficticio" not in repr(configuracao)


def test_carregar_configuracao_le_os_environ_por_padrao(monkeypatch):
    for nome, valor in MINIMO.items():
        monkeypatch.setenv(nome, valor)

    assert carregar_configuracao().ambiente is Ambiente.DEV
