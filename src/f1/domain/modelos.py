"""Entidades da camada bruta, uma por endpoint da OpenF1.

Os nomes dos campos seguem os da API, para que a camada bruta seja rastreável até
a fonte. Campos depreciados (``country_code`` em ``drivers`` e ``pit_duration`` em
``pit``) não fazem parte do contrato. Datas são ``datetime`` em UTC; tempos em
segundos são ``Decimal``; ``X | None`` indica um campo que a API pode omitir.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from f1.domain.tipos import GAP_LIDER, Composto, Gap, TipoSessao


@dataclass(frozen=True, slots=True)
class Meeting:
    """Fim de semana de Grande Prêmio ou de testes."""

    meeting_key: int
    year: int
    meeting_name: str
    date_start: datetime
    meeting_official_name: str | None
    location: str | None
    country_name: str | None
    country_code: str | None
    circuit_key: int | None
    circuit_short_name: str | None
    circuit_type: str | None
    date_end: datetime | None
    gmt_offset: str | None
    is_cancelled: bool = False


@dataclass(frozen=True, slots=True)
class Sessao:
    """Sessão de um fim de semana (treino, classificação, sprint ou corrida)."""

    session_key: int
    meeting_key: int
    year: int
    session_name: str
    session_type: TipoSessao
    date_start: datetime
    date_end: datetime
    gmt_offset: str | None
    location: str | None
    country_name: str | None
    circuit_key: int | None
    circuit_short_name: str | None
    is_cancelled: bool = False


@dataclass(frozen=True, slots=True)
class Piloto:
    """Piloto inscrito em uma sessão."""

    session_key: int
    meeting_key: int
    driver_number: int
    broadcast_name: str | None
    full_name: str | None
    first_name: str | None
    last_name: str | None
    name_acronym: str | None
    team_name: str | None
    team_colour: str | None
    headshot_url: str | None


@dataclass(frozen=True, slots=True)
class Volta:
    """Volta de um piloto, com setores e speed traps."""

    session_key: int
    meeting_key: int
    driver_number: int
    lap_number: int
    date_start: datetime | None
    lap_duration: Decimal | None
    duration_sector_1: Decimal | None
    duration_sector_2: Decimal | None
    duration_sector_3: Decimal | None
    i1_speed: int | None
    i2_speed: int | None
    st_speed: int | None
    segments_sector_1: tuple[int | None, ...] | None
    segments_sector_2: tuple[int | None, ...] | None
    segments_sector_3: tuple[int | None, ...] | None
    is_pit_out_lap: bool = False


@dataclass(frozen=True, slots=True)
class Stint:
    """Período em que o piloto usou o mesmo jogo de pneus."""

    session_key: int
    meeting_key: int
    driver_number: int
    stint_number: int
    compound: Composto | None
    lap_start: int | None
    lap_end: int | None
    tyre_age_at_start: int | None


@dataclass(frozen=True, slots=True)
class PitStop:
    """Passagem pelo pit lane. ``stop_duration`` só existe a partir do GP dos EUA 2024."""

    session_key: int
    meeting_key: int
    driver_number: int
    date: datetime
    lap_number: int | None
    lane_duration: Decimal | None
    stop_duration: Decimal | None


@dataclass(frozen=True, slots=True)
class ResultadoSessao:
    """Resultado final de um piloto na sessão.

    Na classificação, a API devolve ``duration`` e ``gap_to_leader`` como listas
    Q1-Q3; elas são desdobradas nos campos ``*_q1``, ``*_q2`` e ``*_q3``.
    """

    session_key: int
    meeting_key: int
    driver_number: int
    position: int | None
    number_of_laps: int | None
    points: Decimal | None
    duration: Decimal | None
    gap_to_leader: Gap | None
    duration_q1: Decimal | None
    duration_q2: Decimal | None
    duration_q3: Decimal | None
    gap_to_leader_q1: Gap | None
    gap_to_leader_q2: Gap | None
    gap_to_leader_q3: Gap | None
    dnf: bool = False
    dns: bool = False
    dsq: bool = False


@dataclass(frozen=True, slots=True)
class GridLargada:
    """Posição de largada de um piloto."""

    session_key: int
    meeting_key: int
    driver_number: int
    position: int
    lap_duration: Decimal | None


@dataclass(frozen=True, slots=True)
class Clima:
    """Medição meteorológica da pista (aproximadamente uma por minuto)."""

    session_key: int
    meeting_key: int
    date: datetime
    air_temperature: float | None
    track_temperature: float | None
    humidity: float | None
    pressure: float | None
    rainfall: int | None
    wind_direction: int | None
    wind_speed: float | None


@dataclass(frozen=True, slots=True)
class ControleProva:
    """Mensagem da direção de prova (bandeiras, safety car, incidentes)."""

    session_key: int
    meeting_key: int
    date: datetime
    category: str
    message: str | None
    flag: str | None
    scope: str | None
    sector: int | None
    driver_number: int | None
    lap_number: int | None
    qualifying_phase: int | None


@dataclass(frozen=True, slots=True)
class Posicao:
    """Posição de um piloto a partir de um instante."""

    session_key: int
    meeting_key: int
    date: datetime
    driver_number: int
    position: int


@dataclass(frozen=True, slots=True)
class Intervalo:
    """Gap para o líder e para o carro à frente (só corridas)."""

    session_key: int
    meeting_key: int
    date: datetime
    driver_number: int
    gap_to_leader: Gap = GAP_LIDER
    interval: Gap = GAP_LIDER


@dataclass(frozen=True, slots=True)
class Ultrapassagem:
    """Troca de posição entre dois pilotos (só corridas; pode estar incompleta)."""

    session_key: int
    meeting_key: int
    date: datetime
    overtaking_driver_number: int
    overtaken_driver_number: int
    position: int


@dataclass(frozen=True, slots=True)
class RadioEquipe:
    """Mensagem de rádio entre piloto e equipe. Guardamos só a URL do MP3."""

    session_key: int
    meeting_key: int
    date: datetime
    driver_number: int
    recording_url: str


@dataclass(frozen=True, slots=True)
class CampeonatoPiloto:
    """Classificação do campeonato de pilotos após a corrida (beta)."""

    session_key: int
    meeting_key: int
    driver_number: int
    points_start: Decimal | None
    points_current: Decimal | None
    position_start: int | None
    position_current: int | None


@dataclass(frozen=True, slots=True)
class CampeonatoEquipe:
    """Classificação do campeonato de construtores após a corrida (beta)."""

    session_key: int
    meeting_key: int
    team_name: str
    points_start: Decimal | None
    points_current: Decimal | None
    position_start: int | None
    position_current: int | None


@dataclass(frozen=True, slots=True)
class DadosCarro:
    """Amostra de telemetria do carro (~3,7 Hz)."""

    session_key: int
    meeting_key: int
    date: datetime
    driver_number: int
    speed: int | None
    rpm: int | None
    n_gear: int | None
    throttle: int | None
    brake: int | None
    drs: int | None


@dataclass(frozen=True, slots=True)
class Localizacao:
    """Posição aproximada do carro na pista (~3,7 Hz)."""

    session_key: int
    meeting_key: int
    date: datetime
    driver_number: int
    x: int | None
    y: int | None
    z: int | None
