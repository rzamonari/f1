import json
import logging

import pytest

from f1.observability.logging import (
    FiltroContexto,
    FormatadorJson,
    configurar_logging,
    definir_id_execucao,
)


def _registro(mensagem: str = "pipeline concluído", **extra: object) -> logging.LogRecord:
    registro = logging.makeLogRecord({"name": "f1.teste", "levelname": "INFO", "msg": mensagem})
    for chave, valor in extra.items():
        setattr(registro, chave, valor)
    return registro


def test_formatador_json_inclui_extra_e_id_execucao():
    definir_id_execucao("exec-123")
    registro = _registro(lidos=10)
    FiltroContexto().filter(registro)

    evento = json.loads(FormatadorJson().format(registro))

    assert evento["mensagem"] == "pipeline concluído"
    assert evento["lidos"] == 10
    assert evento["id_execucao"] == "exec-123"
    assert evento["nivel"] == "INFO"


def test_formatador_json_inclui_stack_trace():
    try:
        raise ValueError("falhou")
    except ValueError:
        registro = logging.makeLogRecord({"msg": "erro", "exc_info": __import__("sys").exc_info()})

    evento = json.loads(FormatadorJson().format(registro))

    assert "ValueError: falhou" in evento["exception"]


def test_definir_id_execucao_gera_identificador_quando_omitido():
    assert len(definir_id_execucao()) == 32


@pytest.fixture
def raiz_restaurada():
    raiz = logging.getLogger()
    handlers, nivel = list(raiz.handlers), raiz.level
    yield raiz
    raiz.handlers[:] = handlers
    raiz.setLevel(nivel)


def test_configurar_logging_substitui_handlers_e_define_nivel(raiz_restaurada, capsys):
    configurar_logging("WARNING")

    logging.getLogger("f1.teste").warning("aviso", extra={"endpoint": "laps"})

    assert raiz_restaurada.level == logging.WARNING
    assert len(raiz_restaurada.handlers) == 1
    evento = json.loads(capsys.readouterr().out.strip())
    assert evento["endpoint"] == "laps"
