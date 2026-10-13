"""Camada bruta no DuckDB: uma tabela por endpoint da OpenF1."""

from f1.domain.endpoints import TODOS_ENDPOINTS
from f1.repositories.duckdb_base import AbrirConexao, RepositorioDuckDB

TABELAS_BRUTAS: dict[type, str] = {e.modelo: e.nome for e in TODOS_ENDPOINTS}


class RepositorioBrutoDuckDB(RepositorioDuckDB):
    """Tabelas brutas, com o nome do endpoint e os campos da API.

    Partições: ``year`` para ``meetings``/``sessions``, ``session_key`` para os
    endpoints de sessão e ``session_key`` + ``driver_number`` para a telemetria.
    """

    def __init__(self, abrir_conexao: AbrirConexao) -> None:
        super().__init__(abrir_conexao, TABELAS_BRUTAS)
