import logging

import pytest

from f1 import cli
from f1.domain.tipos import TipoSessao


@pytest.fixture(autouse=True)
def raiz_restaurada():
    raiz = logging.getLogger()
    handlers, nivel = list(raiz.handlers), raiz.level
    yield
    raiz.handlers[:] = handlers
    raiz.setLevel(nivel)


@pytest.mark.parametrize(
    ("argv", "esperado"),
    [
        (["catalogo", "--ano", "2024"], {"comando": "catalogo", "ano": 2024}),
        (["sessao", "--session-key", "latest"], {"session_key": "latest", "com_telemetria": False}),
        (["sessao", "--session-key", "9159", "--com-telemetria"], {"com_telemetria": True}),
        (["temporada", "--ano", "2024"], {"tipo": TipoSessao.RACE}),
        (["temporada", "--ano", "2024", "--tipo", "Qualifying"], {"tipo": TipoSessao.QUALIFYING}),
        (["analitico", "--session-key", "9159"], {"session_key": 9159}),
    ],
)
def test_criar_parser_subcomandos(argv, esperado):
    args = vars(cli.criar_parser().parse_args(argv))

    assert esperado.items() <= args.items()


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["catalogo"],
        ["temporada", "--ano", "2024", "--tipo", "Sprint"],
        ["analitico", "--session-key", "x"],
    ],
)
def test_criar_parser_argumentos_invalidos(argv):
    with pytest.raises(SystemExit):
        cli.criar_parser().parse_args(argv)


def test_main_configuracao_invalida_retorna_1_sem_executar(monkeypatch):
    monkeypatch.delenv("F1_AMBIENTE", raising=False)
    monkeypatch.delenv("F1_CAMINHO_BANCO", raising=False)
    executados: list[object] = []
    monkeypatch.setattr(cli, "_executar", lambda *args: executados.append(args))

    assert cli.main(["catalogo", "--ano", "2024"]) == 1
    assert executados == []


@pytest.mark.parametrize(("sucesso", "codigo"), [(True, 0), (False, 1)])
def test_main_traduz_resultado_em_codigo_de_saida(monkeypatch, sucesso, codigo):
    monkeypatch.setenv("F1_AMBIENTE", "dev")
    monkeypatch.setenv("F1_CAMINHO_BANCO", "nao-usado.duckdb")
    monkeypatch.setattr(cli, "_executar", lambda *args: sucesso)

    assert cli.main(["catalogo", "--ano", "2024"]) == codigo


def test_main_excecao_inesperada_retorna_1_e_registra(monkeypatch, capsys):
    monkeypatch.setenv("F1_AMBIENTE", "dev")
    monkeypatch.setenv("F1_CAMINHO_BANCO", "nao-usado.duckdb")

    def falhar(*args):
        raise RuntimeError("banco indisponível")

    monkeypatch.setattr(cli, "_executar", falhar)

    assert cli.main(["catalogo", "--ano", "2024"]) == 1
    assert "banco indisponível" in capsys.readouterr().out
