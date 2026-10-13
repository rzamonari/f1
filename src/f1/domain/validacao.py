"""Validação do contrato de entrada: registros brutos da OpenF1 → entidades de domínio.

O conversor de cada entidade é derivado das anotações de tipo dos campos da
``dataclass``. Cada tipo tem uma regra de conversão estrita (por exemplo, um ``int``
não aceita texto). Campos ``X | None`` aceitam ausência; campos com valor padrão usam
o padrão quando a API omite o campo ou envia ``null``; os demais são obrigatórios.
"""

import re
import types
from collections.abc import Callable, Iterable, Mapping
from dataclasses import MISSING, dataclass, fields
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import get_args, get_origin, get_type_hints

from f1.domain.tipos import Gap

_PADRAO_VOLTAS_ATRAS = re.compile(r"^\+(\d+) LAPS?$")
_FASES_QUALI = ("q1", "q2", "q3")


class ContratoInvalidoError(ValueError):
    """Registro não atende ao contrato de entrada."""


@dataclass(frozen=True, slots=True)
class RegistroRejeitado:
    """Registro de entrada recusado e o motivo da recusa."""

    registro: Mapping[str, object]
    motivo: str


@dataclass(frozen=True, slots=True)
class ResultadoValidacao[T]:
    """Separação entre entidades válidas e registros rejeitados."""

    validos: tuple[T, ...]
    rejeitados: tuple[RegistroRejeitado, ...]

    @property
    def taxa_rejeicao(self) -> float:
        """Proporção de rejeitados sobre o total lido (0 quando não há registros)."""
        total = len(self.validos) + len(self.rejeitados)
        return len(self.rejeitados) / total if total else 0.0


type Conversor[T] = Callable[[Mapping[str, object]], T]


def desembrulhar_opcional(tipo: object) -> tuple[object, bool]:
    """Separa ``X | None`` em ``(X, True)``; outros tipos voltam como ``(tipo, False)``."""
    if isinstance(tipo, types.UnionType):
        argumentos = [arg for arg in get_args(tipo) if arg is not type(None)]
        if len(argumentos) == 1:
            return argumentos[0], True
    return tipo, False


def _inteiro(valor: object) -> int:
    if isinstance(valor, bool):
        raise ContratoInvalidoError(f"esperado inteiro, recebido booleano {valor!r}")
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    raise ContratoInvalidoError(f"esperado inteiro, recebido {valor!r}")


def _decimal(valor: object) -> Decimal:
    if isinstance(valor, bool) or not isinstance(valor, int | float | str):
        raise ContratoInvalidoError(f"esperado número, recebido {valor!r}")
    try:
        numero = Decimal(str(valor))
    except InvalidOperation as exc:
        raise ContratoInvalidoError(f"esperado número, recebido {valor!r}") from exc
    if not numero.is_finite():
        raise ContratoInvalidoError(f"número não finito: {valor!r}")
    return numero


def _real(valor: object) -> float:
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        raise ContratoInvalidoError(f"esperado número, recebido {valor!r}")
    return float(valor)


def _texto(valor: object) -> str:
    if not isinstance(valor, str):
        raise ContratoInvalidoError(f"esperado texto, recebido {valor!r}")
    return valor


def _booleano(valor: object) -> bool:
    if not isinstance(valor, bool):
        raise ContratoInvalidoError(f"esperado booleano, recebido {valor!r}")
    return valor


def _data_hora(valor: object) -> datetime:
    """Converte ISO 8601 para ``datetime`` em UTC (sem fuso, assume UTC, como a API)."""
    texto = _texto(valor)
    try:
        instante = datetime.fromisoformat(texto)
    except ValueError as exc:
        raise ContratoInvalidoError(f"data inválida: {texto!r}") from exc
    if instante.tzinfo is None:
        return instante.replace(tzinfo=UTC)
    return instante.astimezone(UTC)


def converter_gap(valor: object) -> Gap:
    """Converte um gap da OpenF1: número de segundos ou ``"+N LAP(S)"``."""
    if isinstance(valor, str):
        correspondencia = _PADRAO_VOLTAS_ATRAS.match(valor.strip())
        if correspondencia is None:
            raise ContratoInvalidoError(f"gap inválido: {valor!r}")
        return Gap(voltas=int(correspondencia.group(1)))
    return Gap(segundos=_decimal(valor))


def _criar_conversor_valor(tipo: object) -> Callable[[object], object]:
    """Escolhe a função de conversão de um único valor a partir do tipo anotado."""
    simples: dict[object, Callable[[object], object]] = {
        int: _inteiro,
        Decimal: _decimal,
        float: _real,
        str: _texto,
        bool: _booleano,
        datetime: _data_hora,
        Gap: converter_gap,
    }
    if tipo in simples:
        return simples[tipo]
    if isinstance(tipo, type) and issubclass(tipo, StrEnum):
        return _criar_conversor_enum(tipo)
    if get_origin(tipo) is tuple:
        return _criar_conversor_tupla(tipo)
    raise TypeError(f"tipo sem regra de conversão: {tipo!r}")


def _criar_conversor_enum(tipo: type[StrEnum]) -> Callable[[object], object]:
    def converter(valor: object) -> StrEnum:
        try:
            return tipo(_texto(valor))
        except ValueError as exc:
            raise ContratoInvalidoError(
                f"valor fora do domínio de {tipo.__name__}: {valor!r}"
            ) from exc

    return converter


def _criar_conversor_tupla(tipo: object) -> Callable[[object], object]:
    tipo_item, item_opcional = desembrulhar_opcional(get_args(tipo)[0])
    converter_item = _criar_conversor_valor(tipo_item)

    def converter(valor: object) -> tuple[object, ...]:
        if not isinstance(valor, list):
            raise ContratoInvalidoError(f"esperada lista, recebido {valor!r}")
        if not item_opcional and None in valor:
            raise ContratoInvalidoError("lista com item nulo")
        return tuple(None if item is None else converter_item(item) for item in valor)

    return converter


def criar_conversor[T](modelo: type[T]) -> Conversor[T]:
    """Cria o conversor de registros brutos para a entidade ``modelo``.

    As anotações são analisadas uma única vez; o conversor devolvido é reaproveitado
    para todos os registros do endpoint.

    Raises:
        TypeError: Se algum campo usar um tipo sem regra de conversão (erro de programação).
    """
    dicas = get_type_hints(modelo)
    regras: list[tuple[str, Callable[[object], object], bool, object]] = []
    for campo in fields(modelo):
        tipo, opcional = desembrulhar_opcional(dicas[campo.name])
        regras.append((campo.name, _criar_conversor_valor(tipo), opcional, campo.default))

    def converter(registro: Mapping[str, object]) -> T:
        if not isinstance(registro, Mapping):
            raise ContratoInvalidoError(f"esperado objeto JSON, recebido {type(registro).__name__}")
        valores: dict[str, object] = {}
        for nome, converter_valor, opcional, padrao in regras:
            bruto = registro.get(nome)
            if bruto is not None:
                try:
                    valores[nome] = converter_valor(bruto)
                except ContratoInvalidoError as exc:
                    raise ContratoInvalidoError(f"{nome}: {exc}") from exc
            elif padrao is not MISSING:
                valores[nome] = padrao
            elif opcional:
                valores[nome] = None
            else:
                raise ContratoInvalidoError(f"campo obrigatório ausente: {nome}")
        return modelo(**valores)

    return converter


def desdobrar_fases_quali(registro: Mapping[str, object]) -> dict[str, object]:
    """Desdobra ``duration`` e ``gap_to_leader`` em listas Q1-Q3 nos campos ``*_q1..q3``.

    Em sessões que não são de classificação, os campos chegam como escalares e o
    registro é devolvido sem alteração.

    Raises:
        ContratoInvalidoError: Se uma lista tiver mais de três fases.
    """
    if not isinstance(registro, Mapping):
        raise ContratoInvalidoError(f"esperado objeto JSON, recebido {type(registro).__name__}")
    desdobrado = dict(registro)
    for campo in ("duration", "gap_to_leader"):
        valor = registro.get(campo)
        if not isinstance(valor, list):
            continue
        if len(valor) > len(_FASES_QUALI):
            raise ContratoInvalidoError(f"{campo}: mais de três fases de classificação")
        desdobrado[campo] = None
        for fase, valor_fase in zip(_FASES_QUALI, valor, strict=False):
            desdobrado[f"{campo}_{fase}"] = valor_fase
    return desdobrado


def validar[T](
    registros: Iterable[Mapping[str, object]], conversor: Conversor[T]
) -> ResultadoValidacao[T]:
    """Valida registros brutos, separando entidades válidas de rejeitadas."""
    validos: list[T] = []
    rejeitados: list[RegistroRejeitado] = []
    for registro in registros:
        try:
            validos.append(conversor(registro))
        except ContratoInvalidoError as exc:
            rejeitados.append(RegistroRejeitado(registro=registro, motivo=str(exc)))
    return ResultadoValidacao(validos=tuple(validos), rejeitados=tuple(rejeitados))
