"""Tipos de valor do domínio de Fórmula 1."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class TipoSessao(StrEnum):
    """Tipo de sessão, conforme o campo ``session_type`` da OpenF1.

    Sprints aparecem como ``Race`` e Sprint Qualifying/Shootout como ``Qualifying``.
    """

    PRACTICE = "Practice"
    QUALIFYING = "Qualifying"
    RACE = "Race"


class Composto(StrEnum):
    """Composto de pneu informado em ``stints``."""

    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"
    UNKNOWN = "UNKNOWN"
    TEST_UNKNOWN = "TEST_UNKNOWN"


@dataclass(frozen=True, slots=True)
class Gap:
    """Distância para outro carro: em segundos **ou** em voltas de atraso.

    A OpenF1 informa um número (segundos), um texto ``"+N LAP(S)"`` (voltas de
    atraso) ou ``null`` (o próprio líder). O líder é representado por zero segundos.
    """

    segundos: Decimal | None = None
    voltas: int | None = None

    def __post_init__(self) -> None:
        if (self.segundos is None) == (self.voltas is None):
            raise ValueError("Gap exige exatamente um entre segundos e voltas")

    @property
    def eh_lider(self) -> bool:
        """Indica se o gap representa o próprio líder (ou o carro de referência)."""
        return self.segundos == 0


GAP_LIDER = Gap(segundos=Decimal(0))
