import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from f1.domain.modelos import Sessao, Volta
from f1.domain.tipos import TipoSessao

FIXTURES = Path(__file__).parent / "fixtures"


class FonteFake:
    """Fonte em memória: devolve as respostas configuradas por endpoint."""

    def __init__(
        self,
        respostas: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
        filtrar_por_igualdade: bool = False,
    ):
        self.respostas = dict(respostas or {})
        self.filtrar_por_igualdade = filtrar_por_igualdade
        self.chamadas: list[tuple[str, tuple[object, ...]]] = []

    def _registros(self, endpoint, filtros):
        registros = [dict(r) for r in self.respostas.get(endpoint, [])]
        if not self.filtrar_por_igualdade:
            return registros
        return [r for r in registros if all(r.get(f.campo) == f.valor for f in filtros)]

    def buscar(self, endpoint, filtros):
        self.chamadas.append((endpoint, tuple(filtros)))
        return self._registros(endpoint, filtros)

    def buscar_em_janelas(self, endpoint, filtros, inicio, fim, tamanho_janela):
        self.chamadas.append((endpoint, tuple(filtros)))
        registros = self._registros(endpoint, filtros)
        metade = len(registros) // 2
        yield registros[:metade]
        yield registros[metade:]


class BancoFake:
    """Destino e leitor em memória que respeita a semântica de partição."""

    def __init__(self):
        self.tabelas: dict[type, list[object]] = {}
        self.escritas = 0

    def substituir_particao(self, particao, lotes):
        self.escritas += 1
        for modelo, registros in lotes.items():
            mantidos = [r for r in self.tabelas.get(modelo, []) if not self._pertence(r, particao)]
            self.tabelas[modelo] = mantidos + list(registros)

    def ler(self, modelo, particao):
        return [r for r in self.tabelas.get(modelo, []) if self._pertence(r, particao)]

    @staticmethod
    def _pertence(registro, particao):
        return all(getattr(registro, k) == v for k, v in particao.items())


class QuarentenaFake:
    def __init__(self):
        self.particoes: dict[tuple[str, tuple[tuple[str, int], ...]], list[object]] = {}

    def registrar(self, endpoint, particao, rejeitados):
        self.particoes[(endpoint, tuple(particao.items()))] = list(rejeitados)

    @property
    def total(self):
        return sum(len(v) for v in self.particoes.values())


@pytest.fixture
def amostras() -> dict[str, list[dict[str, object]]]:
    """Respostas reais e reduzidas da OpenF1 (dados públicos)."""
    with (FIXTURES / "openf1_amostras.json").open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


@pytest.fixture
def banco() -> BancoFake:
    return BancoFake()


@pytest.fixture
def quarentena() -> QuarentenaFake:
    return QuarentenaFake()


@pytest.fixture
def criar_fonte():
    return FonteFake


INICIO_SESSAO = datetime(2024, 4, 21, 7, 0, tzinfo=UTC)


@pytest.fixture
def fabrica_sessao():
    def _criar(**sobrescritas: object) -> Sessao:
        sessao = Sessao(
            session_key=9673,
            meeting_key=1233,
            year=2024,
            session_name="Race",
            session_type=TipoSessao.RACE,
            date_start=INICIO_SESSAO,
            date_end=INICIO_SESSAO + timedelta(hours=2),
            gmt_offset="08:00:00",
            location="Shanghai",
            country_name="China",
            circuit_key=49,
            circuit_short_name="Shanghai",
        )
        return replace(sessao, **sobrescritas)

    return _criar


@pytest.fixture
def fabrica_volta():
    def _criar(**sobrescritas: object) -> Volta:
        volta = Volta(
            session_key=9673,
            meeting_key=1233,
            driver_number=1,
            lap_number=1,
            date_start=INICIO_SESSAO,
            lap_duration=Decimal("100.000"),
            duration_sector_1=None,
            duration_sector_2=None,
            duration_sector_3=None,
            i1_speed=None,
            i2_speed=None,
            st_speed=None,
            segments_sector_1=None,
            segments_sector_2=None,
            segments_sector_3=None,
        )
        return replace(volta, **sobrescritas)

    return _criar
