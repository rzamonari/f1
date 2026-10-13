"""Catálogo dos endpoints da OpenF1 ingeridos pelo projeto.

Cada endpoint associa o nome na API (que também é o nome da tabela bruta) à
entidade de domínio e ao conversor do contrato de entrada.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from f1.domain.modelos import (
    CampeonatoEquipe,
    CampeonatoPiloto,
    Clima,
    ControleProva,
    DadosCarro,
    GridLargada,
    Intervalo,
    Localizacao,
    Meeting,
    Piloto,
    PitStop,
    Posicao,
    RadioEquipe,
    ResultadoSessao,
    Sessao,
    Stint,
    Ultrapassagem,
    Volta,
)
from f1.domain.validacao import Conversor, criar_conversor, desdobrar_fases_quali


@dataclass(frozen=True, slots=True)
class Endpoint:
    """Endpoint da OpenF1 e seu contrato.

    Attributes:
        nome: Caminho do endpoint na API e nome da tabela bruta.
        modelo: Entidade de domínio produzida pela validação.
        conversor: Converte um registro bruto em ``modelo``.
        so_corrida: O endpoint só tem dados em sessões do tipo ``Race``.
    """

    nome: str
    modelo: type
    conversor: Conversor[object]
    so_corrida: bool = False


def _endpoint(nome: str, modelo: type, *, so_corrida: bool = False) -> Endpoint:
    return Endpoint(nome, modelo, criar_conversor(modelo), so_corrida)


_CONVERSOR_RESULTADO = criar_conversor(ResultadoSessao)


def _converter_resultado_sessao(registro: Mapping[str, object]) -> object:
    return _CONVERSOR_RESULTADO(desdobrar_fases_quali(registro))


MEETINGS = _endpoint("meetings", Meeting)
SESSIONS = _endpoint("sessions", Sessao)
DRIVERS = _endpoint("drivers", Piloto)
CAR_DATA = _endpoint("car_data", DadosCarro)
LOCATION = _endpoint("location", Localizacao)

ENDPOINTS_CATALOGO = (MEETINGS, SESSIONS)

# Ordem de ingestão definida no plano: do mais essencial ao mais incompleto.
ENDPOINTS_SESSAO = (
    DRIVERS,
    _endpoint("laps", Volta),
    _endpoint("stints", Stint),
    _endpoint("pit", PitStop),
    Endpoint("session_result", ResultadoSessao, _converter_resultado_sessao),
    _endpoint("starting_grid", GridLargada),
    _endpoint("weather", Clima),
    _endpoint("race_control", ControleProva),
    _endpoint("position", Posicao),
    _endpoint("intervals", Intervalo, so_corrida=True),
    _endpoint("overtakes", Ultrapassagem, so_corrida=True),
    _endpoint("team_radio", RadioEquipe),
    _endpoint("championship_drivers", CampeonatoPiloto, so_corrida=True),
    _endpoint("championship_teams", CampeonatoEquipe, so_corrida=True),
)

ENDPOINTS_TELEMETRIA = (CAR_DATA, LOCATION)

TODOS_ENDPOINTS = ENDPOINTS_CATALOGO + ENDPOINTS_SESSAO + ENDPOINTS_TELEMETRIA
