"""Configuração de logging estruturado em JSON com identificador de execução."""

import io
import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

_id_execucao: ContextVar[str] = ContextVar("id_execucao", default="-")

_ATRIBUTOS_PADRAO = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


def definir_id_execucao(valor: str | None = None) -> str:
    """Define o identificador da execução corrente e o retorna."""
    id_execucao = valor or uuid.uuid4().hex
    _id_execucao.set(id_execucao)
    return id_execucao


class FiltroContexto(logging.Filter):
    """Adiciona o identificador de execução a todos os registros de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Enriquece o registro e permite sua emissão."""
        record.id_execucao = _id_execucao.get()
        return True


class FormatadorJson(logging.Formatter):
    """Formata cada registro como um objeto JSON em uma linha."""

    def format(self, record: logging.LogRecord) -> str:
        """Serializa o registro, incluindo campos de ``extra`` e stack trace."""
        evento: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }
        evento.update({k: v for k, v in vars(record).items() if k not in _ATRIBUTOS_PADRAO})
        if record.exc_info:
            evento["exception"] = self.formatException(record.exc_info)
        return json.dumps(evento, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO") -> None:
    """Configura o logger raiz. Deve ser chamada só no ponto de entrada."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        # No Windows o console usa cp1252 por padrão; os eventos JSON são sempre UTF-8.
        sys.stdout.reconfigure(encoding="utf-8")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatadorJson())
    handler.addFilter(FiltroContexto())
    raiz = logging.getLogger()
    raiz.handlers[:] = [handler]
    raiz.setLevel(nivel)
    # O httpx registra cada requisição em INFO; o cliente já registra o que importa.
    logging.getLogger("httpx").setLevel(logging.WARNING)
