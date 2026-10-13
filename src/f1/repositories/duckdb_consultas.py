"""Consultas de leitura sobre o DuckDB, usadas pelo dashboard."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import duckdb

from f1.domain.tipos import TipoSessao

LIMITE_VOLTAS_PADRAO = 5


@dataclass(frozen=True, slots=True)
class SessaoDoCircuito:
    """Sessão de um fim de semana, com os dados do circuito para exibição."""

    session_key: int
    session_name: str
    meeting_name: str
    location: str | None
    country_name: str | None
    date_start: datetime
    voltas_ingeridas: int


@dataclass(frozen=True, slots=True)
class VoltaRapida:
    """Uma das voltas mais rápidas de uma sessão."""

    session_key: int
    posicao: int
    driver_number: int
    name_acronym: str | None
    full_name: str | None
    team_name: str | None
    team_colour: str | None
    lap_number: int
    lap_duration: Decimal


class ConsultasDuckDB:
    """Consultas somente leitura. A conexão é injetada e não é fechada aqui."""

    def __init__(self, conexao: duckdb.DuckDBPyConnection) -> None:
        self._conexao = conexao

    def anos_disponiveis(self) -> list[int]:
        """Anos com catálogo ingerido, do mais recente ao mais antigo."""
        if not self._tabela_existe("sessions"):
            return []
        linhas = self._conexao.execute("SELECT DISTINCT year FROM sessions ORDER BY year DESC")
        return [ano for (ano,) in linhas.fetchall()]

    def sessoes(self, ano: int, tipo: TipoSessao) -> list[SessaoDoCircuito]:
        """Sessões não canceladas do ano e tipo, em ordem cronológica."""
        if not self._tabela_existe("laps"):
            return []
        linhas = self._conexao.execute(
            """
            SELECT s.session_key, s.session_name, m.meeting_name, s.location, s.country_name,
                   s.date_start, COUNT(l.lap_number) AS voltas
            FROM sessions s
            JOIN meetings m ON m.meeting_key = s.meeting_key AND m.year = s.year
            LEFT JOIN laps l ON l.session_key = s.session_key
            WHERE s.year = ? AND s.session_type = ? AND NOT s.is_cancelled
            GROUP BY ALL
            ORDER BY s.date_start
            """,
            [ano, str(tipo)],
        ).fetchall()
        return [
            SessaoDoCircuito(
                session_key=chave,
                session_name=nome,
                meeting_name=meeting,
                location=local,
                country_name=pais,
                date_start=inicio.replace(tzinfo=UTC),
                voltas_ingeridas=voltas,
            )
            for chave, nome, meeting, local, pais, inicio, voltas in linhas
        ]

    def voltas_mais_rapidas(
        self, session_keys: list[int], limite: int = LIMITE_VOLTAS_PADRAO
    ) -> dict[int, list[VoltaRapida]]:
        """As ``limite`` voltas mais rápidas de cada sessão, com dados do piloto.

        Empates no tempo são desfeitos pelo número da volta e depois pelo piloto.
        """
        if not session_keys:
            return {}
        linhas = self._conexao.execute(
            """
            SELECT l.session_key,
                   ROW_NUMBER() OVER (
                       PARTITION BY l.session_key
                       ORDER BY l.lap_duration, l.lap_number, l.driver_number
                   ) AS posicao,
                   l.driver_number, d.name_acronym, d.full_name, d.team_name, d.team_colour,
                   l.lap_number, l.lap_duration
            FROM laps l
            LEFT JOIN drivers d
                ON d.session_key = l.session_key AND d.driver_number = l.driver_number
            WHERE l.session_key IN (SELECT UNNEST(?::INTEGER[])) AND l.lap_duration IS NOT NULL
            QUALIFY posicao <= ?
            ORDER BY l.session_key, posicao
            """,
            [session_keys, limite],
        ).fetchall()
        resultado: dict[int, list[VoltaRapida]] = {chave: [] for chave in session_keys}
        for linha in linhas:
            resultado[linha[0]].append(VoltaRapida(*linha))
        return resultado

    def _tabela_existe(self, nome: str) -> bool:
        linha = self._conexao.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [nome]
        ).fetchone()
        return bool(linha and linha[0])
