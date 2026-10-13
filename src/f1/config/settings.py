"""Carregamento e validação da configuração a partir de variáveis de ambiente."""

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from pathlib import Path

PREFIXO = "F1_"
OBRIGATORIAS = ("AMBIENTE", "CAMINHO_BANCO")
NIVEIS_LOG = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class Ambiente(StrEnum):
    """Ambientes de execução suportados."""

    DEV = "dev"
    HML = "hml"
    PRD = "prd"


class ConfiguracaoInvalidaError(RuntimeError):
    """A configuração do ambiente está ausente ou inválida."""


@dataclass(frozen=True, slots=True)
class Configuracao:
    """Configuração imutável da aplicação. Ver ``docs/configuration.md``."""

    ambiente: Ambiente
    caminho_banco: Path
    api_base_url: str = "https://api.openf1.org/v1"
    timeout_s: float = 30.0
    max_tentativas: int = 4
    pausa_entre_requisicoes_s: float = 0.5
    janela_telemetria: timedelta = timedelta(minutes=10)
    limite_taxa_rejeicao: float = 0.05
    margem_apos_sessao: timedelta = timedelta(minutes=60)
    nivel_log: str = "INFO"
    # Reservados para o cliente autenticado de tempo real (evolução futura).
    openf1_usuario: str | None = field(default=None, repr=False)
    openf1_senha: str | None = field(default=None, repr=False)


def _ler[T](origem: Mapping[str, str], nome: str, converter: Callable[[str], T], padrao: T) -> T:
    bruto = origem.get(PREFIXO + nome)
    if bruto is None or bruto == "":
        return padrao
    try:
        return converter(bruto)
    except ValueError as exc:
        # Cita só o nome da variável, nunca o valor (que pode ser sensível).
        raise ConfiguracaoInvalidaError(f"valor inválido em {PREFIXO}{nome}") from exc


def _minutos(texto: str) -> timedelta:
    return timedelta(minutes=float(texto))


def _exigir(condicao: bool, nome: str, regra: str) -> None:
    if not condicao:
        raise ConfiguracaoInvalidaError(f"{PREFIXO}{nome} {regra}")


def carregar_configuracao(env: Mapping[str, str] | None = None) -> Configuracao:
    """Lê e valida a configuração.

    Args:
        env: Variáveis de ambiente; usa ``os.environ`` quando omitido (útil para testes).

    Raises:
        ConfiguracaoInvalidaError: Se faltar variável obrigatória ou algum valor for inválido.
    """
    origem = os.environ if env is None else env
    faltantes = [PREFIXO + nome for nome in OBRIGATORIAS if not origem.get(PREFIXO + nome)]
    if faltantes:
        raise ConfiguracaoInvalidaError(f"variáveis obrigatórias ausentes: {', '.join(faltantes)}")
    padrao = Configuracao(ambiente=Ambiente.DEV, caminho_banco=Path())
    configuracao = Configuracao(
        ambiente=_ler(origem, "AMBIENTE", Ambiente, Ambiente.DEV),
        caminho_banco=Path(origem[PREFIXO + "CAMINHO_BANCO"]),
        api_base_url=_ler(origem, "API_BASE_URL", str, padrao.api_base_url),
        timeout_s=_ler(origem, "TIMEOUT_S", float, padrao.timeout_s),
        max_tentativas=_ler(origem, "MAX_TENTATIVAS", int, padrao.max_tentativas),
        pausa_entre_requisicoes_s=_ler(
            origem, "PAUSA_ENTRE_REQUISICOES_S", float, padrao.pausa_entre_requisicoes_s
        ),
        janela_telemetria=_ler(origem, "JANELA_TELEMETRIA_MIN", _minutos, padrao.janela_telemetria),
        limite_taxa_rejeicao=_ler(
            origem, "LIMITE_TAXA_REJEICAO", float, padrao.limite_taxa_rejeicao
        ),
        margem_apos_sessao=_ler(
            origem, "MARGEM_APOS_SESSAO_MIN", _minutos, padrao.margem_apos_sessao
        ),
        nivel_log=_ler(origem, "NIVEL_LOG", str.upper, padrao.nivel_log),
        openf1_usuario=origem.get(PREFIXO + "OPENF1_USUARIO") or None,
        openf1_senha=origem.get(PREFIXO + "OPENF1_SENHA") or None,
    )
    _validar(configuracao)
    return configuracao


def _validar(configuracao: Configuracao) -> None:
    _exigir(configuracao.timeout_s > 0, "TIMEOUT_S", "deve ser positivo")
    _exigir(configuracao.max_tentativas >= 1, "MAX_TENTATIVAS", "deve ser >= 1")
    _exigir(
        configuracao.pausa_entre_requisicoes_s >= 0,
        "PAUSA_ENTRE_REQUISICOES_S",
        "não pode ser negativa",
    )
    _exigir(
        configuracao.janela_telemetria > timedelta(0), "JANELA_TELEMETRIA_MIN", "deve ser positiva"
    )
    _exigir(
        0 <= configuracao.limite_taxa_rejeicao <= 1,
        "LIMITE_TAXA_REJEICAO",
        "deve estar entre 0 e 1",
    )
    _exigir(
        configuracao.margem_apos_sessao >= timedelta(0),
        "MARGEM_APOS_SESSAO_MIN",
        "não pode ser negativa",
    )
    _exigir(
        configuracao.nivel_log in NIVEIS_LOG, "NIVEL_LOG", f"deve ser um de {sorted(NIVEIS_LOG)}"
    )
    _exigir(
        configuracao.api_base_url.startswith(("https://", "http://")),
        "API_BASE_URL",
        "deve começar com http:// ou https://",
    )
