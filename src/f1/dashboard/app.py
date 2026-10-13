"""Dashboard: as 5 voltas mais rápidas de cada circuito.

Execução: ``poetry run streamlit run src/f1/dashboard/app.py``. Os dados vêm do
DuckDB alimentado pela CLI ``f1``; o dashboard não chama a API.
"""

import duckdb
import streamlit as st

from f1.config.settings import ConfiguracaoInvalidaError, carregar_configuracao
from f1.dashboard.formatacao import (
    ROTULOS_TIPO,
    formatar_diferenca,
    formatar_tempo_volta,
    titulo_da_sessao,
)
from f1.domain.tipos import TipoSessao
from f1.repositories.duckdb_consultas import ConsultasDuckDB, SessaoDoCircuito, VoltaRapida

ORDEM_TIPOS = (TipoSessao.RACE, TipoSessao.QUALIFYING, TipoSessao.PRACTICE)


def _tabela(voltas: list[VoltaRapida]) -> list[dict[str, object]]:
    referencia = voltas[0].lap_duration
    return [
        {
            "Pos": v.posicao,
            "Piloto": v.full_name or v.name_acronym or f"#{v.driver_number}",
            "Nº": v.driver_number,
            "Equipe": v.team_name or "—",
            "Volta": v.lap_number,
            "Tempo": formatar_tempo_volta(v.lap_duration),
            "Dif.": formatar_diferenca(v.lap_duration, referencia),
        }
        for v in voltas
    ]


def _mostrar_sessao(sessao: SessaoDoCircuito, voltas: list[VoltaRapida], tipo: TipoSessao) -> None:
    with st.expander(titulo_da_sessao(sessao, str(tipo))):
        if voltas:
            st.dataframe(_tabela(voltas), hide_index=True, width="stretch")
        else:
            st.info(
                "Voltas desta sessão ainda não ingeridas. Rode: "
                f"`poetry run f1 sessao --session-key {sessao.session_key}`"
            )


def main() -> None:
    """Renderiza a página."""
    st.set_page_config(page_title="F1 Fastest Laps", page_icon="🏎️", layout="wide")
    try:
        configuracao = carregar_configuracao()
    except ConfiguracaoInvalidaError as exc:
        st.error(f"Configuração inválida: {exc}. Defina F1_AMBIENTE e F1_CAMINHO_BANCO.")
        return
    if not configuracao.caminho_banco.exists():
        st.warning(
            f"Banco não encontrado em `{configuracao.caminho_banco}`. "
            "Rode primeiro: `poetry run f1 catalogo --ano 2024`"
        )
        return

    # Conexão curta e só leitura: não bloqueia a CLI quando ela precisar gravar.
    try:
        conexao = duckdb.connect(str(configuracao.caminho_banco), read_only=True)
    except duckdb.IOException:
        # No Windows, o DuckDB bloqueia o arquivo enquanto a CLI grava.
        st.warning("O banco está em uso por uma ingestão em andamento. Tente de novo em instantes.")
        st.button("Tentar novamente")
        return
    with conexao:
        consultas = ConsultasDuckDB(conexao)
        anos = consultas.anos_disponiveis()
        st.sidebar.header("Filtros")
        if not anos:
            st.warning("Catálogo vazio. Rode: `poetry run f1 catalogo --ano 2024`")
            return
        ano = st.sidebar.selectbox("Ano", anos)
        tipo = st.sidebar.selectbox(
            "Tipo de Sessão", ORDEM_TIPOS, format_func=lambda t: ROTULOS_TIPO[str(t)]
        )
        sessoes = consultas.sessoes(ano, tipo)
        voltas = consultas.voltas_mais_rapidas([s.session_key for s in sessoes])

    st.title("🏎️ F1 — 5 Voltas Mais Rápidas por Circuito")
    if not sessoes:
        st.info(f"Nenhuma sessão do tipo {ROTULOS_TIPO[str(tipo)]} no catálogo de {ano}.")
        return
    ingeridas = sum(1 for s in sessoes if voltas[s.session_key])
    st.caption(f"{ingeridas} de {len(sessoes)} sessões com voltas ingeridas.")
    for sessao in sessoes:
        _mostrar_sessao(sessao, voltas[sessao.session_key], tipo)


if __name__ == "__main__":
    main()
