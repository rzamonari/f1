"""Ritmo por piloto: melhor volta e média das voltas representativas."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from decimal import Decimal

from f1.domain.analitico import RitmoPiloto
from f1.domain.modelos import ControleProva, Volta

CATEGORIA_SAFETY_CAR = "SafetyCar"
_PRECISAO = Decimal("0.001")


def voltas_neutralizadas(mensagens: Iterable[ControleProva], ultima_volta: int) -> frozenset[int]:
    """Identifica as voltas disputadas sob safety car (SC) ou virtual safety car (VSC).

    Um período começa na volta da mensagem ``... DEPLOYED`` e termina, inclusive, na
    volta de ``... IN THIS LAP`` (SC) ou ``... ENDING`` (VSC). Um período sem
    encerramento vai até ``ultima_volta``. Mensagens sem volta são ignoradas.

    Args:
        mensagens: Mensagens de ``race_control`` da sessão, em qualquer ordem.
        ultima_volta: Maior número de volta da sessão.
    """
    relevantes = sorted(
        (
            m
            for m in mensagens
            if m.category == CATEGORIA_SAFETY_CAR and m.lap_number is not None and m.message
        ),
        key=lambda m: m.date,
    )
    neutralizadas: set[int] = set()
    inicio: int | None = None
    for mensagem in relevantes:
        texto = (mensagem.message or "").upper()
        volta = mensagem.lap_number or 0
        if "DEPLOYED" in texto:
            inicio = volta if inicio is None else inicio
        elif ("IN THIS LAP" in texto or "ENDING" in texto) and inicio is not None:
            neutralizadas.update(range(inicio, volta + 1))
            inicio = None
    if inicio is not None:
        neutralizadas.update(range(inicio, ultima_volta + 1))
    return frozenset(neutralizadas)


def eh_volta_representativa(volta: Volta, neutralizadas: frozenset[int]) -> bool:
    """Volta com tempo, que não é saída de pit e não foi disputada sob SC/VSC."""
    return (
        volta.lap_duration is not None
        and not volta.is_pit_out_lap
        and volta.lap_number not in neutralizadas
    )


def _resumir_piloto(
    session_key: int, driver_number: int, voltas: Sequence[Volta], neutralizadas: frozenset[int]
) -> RitmoPiloto:
    cronometradas = [v for v in voltas if v.lap_duration is not None]
    validas = [v.lap_duration for v in voltas if eh_volta_representativa(v, neutralizadas)]
    melhor = min(cronometradas, key=lambda v: v.lap_duration or 0, default=None)
    media = (
        (sum(d for d in validas if d is not None) / len(validas)).quantize(_PRECISAO)
        if validas
        else None
    )
    return RitmoPiloto(
        session_key=session_key,
        driver_number=driver_number,
        voltas_totais=len(voltas),
        voltas_validas=len(validas),
        melhor_volta_s=melhor.lap_duration if melhor else None,
        numero_melhor_volta=melhor.lap_number if melhor else None,
        ritmo_medio_s=media,
    )


def resumir_ritmo(
    session_key: int, voltas: Iterable[Volta], mensagens: Iterable[ControleProva]
) -> list[RitmoPiloto]:
    """Calcula o ritmo de cada piloto da sessão, ordenado pelo número do piloto."""
    por_piloto: dict[int, list[Volta]] = defaultdict(list)
    for volta in voltas:
        por_piloto[volta.driver_number].append(volta)
    ultima_volta = max(
        (v.lap_number for lista in por_piloto.values() for v in lista),
        default=0,
    )
    neutralizadas = voltas_neutralizadas(mensagens, ultima_volta)
    return [
        _resumir_piloto(session_key, numero, por_piloto[numero], neutralizadas)
        for numero in sorted(por_piloto)
    ]
