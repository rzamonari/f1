"""Exceções de domínio que o chamador precisa distinguir.

``IngestaoError`` agrupa as falhas que interrompem a ingestão de **uma** partição
(sessão ou ano) sem indicar problema sistêmico. O comando ``temporada`` isola essas
falhas por sessão; qualquer outra exceção interrompe a execução inteira.
"""


class IngestaoError(RuntimeError):
    """Falha que interrompe a ingestão de uma partição."""


class FonteIndisponivelError(IngestaoError):
    """A API permaneceu indisponível após todas as tentativas."""


class RequisicaoRecusadaError(IngestaoError):
    """A API recusou a requisição com um erro definitivo (4xx), sem retry."""


class TaxaRejeicaoExcedidaError(IngestaoError):
    """A proporção de registros rejeitados ultrapassou o limite (provável mudança de schema)."""


class SessaoIndisponivelError(IngestaoError):
    """A sessão não existe, foi cancelada ou ainda não pode ser ingerida."""
