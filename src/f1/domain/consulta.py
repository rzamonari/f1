"""Contrato de consulta à OpenF1, compartilhado entre pipelines e integrações."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

type ValorFiltro = str | int | float | datetime


class Operador(StrEnum):
    """Operadores aceitos pela OpenF1 no nome do parâmetro (ex.: ``speed>=315``)."""

    IGUAL = "="
    MAIOR = ">"
    MENOR = "<"
    MAIOR_OU_IGUAL = ">="
    MENOR_OU_IGUAL = "<="


@dataclass(frozen=True, slots=True)
class Filtro:
    """Filtro de consulta. Uma sequência em ``valor`` repete o parâmetro (OU lógico)."""

    campo: str
    operador: Operador
    valor: ValorFiltro | Sequence[ValorFiltro]


def igual(campo: str, valor: ValorFiltro | Sequence[ValorFiltro]) -> Filtro:
    """Atalho para o filtro de igualdade, o mais comum."""
    return Filtro(campo, Operador.IGUAL, valor)
