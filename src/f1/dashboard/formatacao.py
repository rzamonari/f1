"""Formatação de valores para exibição no dashboard."""

from decimal import Decimal

from f1.repositories.duckdb_consultas import SessaoDoCircuito

ROTULOS_TIPO = {"Race": "Corrida", "Qualifying": "Classificação", "Practice": "Treino"}


def formatar_tempo_volta(segundos: Decimal) -> str:
    """Formata um tempo de volta como ``m:ss.mmm`` (ex.: ``1:34.486``)."""
    milissegundos = int((segundos * 1000).to_integral_value())
    minutos, resto = divmod(milissegundos, 60_000)
    return f"{minutos}:{resto // 1000:02d}.{resto % 1000:03d}"


def formatar_diferenca(segundos: Decimal, referencia: Decimal) -> str:
    """Diferença para a volta mais rápida (``+0.123``); vazio para a própria referência."""
    diferenca = segundos - referencia
    return f"+{diferenca:.3f}" if diferenca > 0 else ""


def titulo_da_sessao(sessao: SessaoDoCircuito, nome_padrao: str) -> str:
    """Título do circuito; o nome da sessão aparece quando difere do tipo (ex.: Sprint)."""
    local = ", ".join(p for p in (sessao.location, sessao.country_name) if p)
    titulo = f"🏁 {sessao.meeting_name} — {local}" if local else f"🏁 {sessao.meeting_name}"
    if sessao.session_name != nome_padrao:
        titulo += f" ({sessao.session_name})"
    return titulo
