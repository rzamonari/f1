"""Camada analítica no DuckDB: tabelas derivadas das tabelas brutas, por sessão."""

from f1.domain.analitico import EstrategiaPiloto, RitmoPiloto, TelemetriaVolta
from f1.repositories.duckdb_base import AbrirConexao, RepositorioDuckDB

TABELAS_ANALITICAS: dict[type, str] = {
    RitmoPiloto: "ritmo_piloto",
    EstrategiaPiloto: "estrategia_piloto",
    TelemetriaVolta: "telemetria_volta",
}


class RepositorioAnaliticoDuckDB(RepositorioDuckDB):
    """Tabelas analíticas, recalculadas por inteiro a cada execução, por ``session_key``."""

    def __init__(self, abrir_conexao: AbrirConexao) -> None:
        super().__init__(abrir_conexao, TABELAS_ANALITICAS)
