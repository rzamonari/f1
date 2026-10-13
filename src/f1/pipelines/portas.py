"""Portas (contratos) que os pipelines recebem por injeção de dependência."""

from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime, timedelta
from typing import Protocol

from f1.domain.consulta import Filtro
from f1.domain.validacao import RegistroRejeitado

type Registro = dict[str, object]


class FonteOpenF1(Protocol):
    """Origem dos registros brutos da OpenF1."""

    def buscar(self, endpoint: str, filtros: Sequence[Filtro]) -> list[Registro]:
        """Retorna todos os registros do endpoint que atendem aos filtros."""
        ...

    def buscar_em_janelas(
        self,
        endpoint: str,
        filtros: Sequence[Filtro],
        inicio: datetime,
        fim: datetime,
        tamanho_janela: timedelta,
    ) -> Iterator[list[Registro]]:
        """Gera os registros em lotes, um por janela de tempo de ``[inicio, fim)``."""
        ...


class DestinoParticionado(Protocol):
    """Destino que substitui partições inteiras de forma atômica e idempotente."""

    def substituir_particao(
        self, particao: Mapping[str, int], lotes: Mapping[type, Sequence[object]]
    ) -> None:
        """Substitui a partição de cada tabela (definida pelo tipo) em uma transação."""
        ...


class LeitorParticionado(Protocol):
    """Leitura de entidades já gravadas, por partição."""

    def ler[T](self, modelo: type[T], particao: Mapping[str, int]) -> list[T]:
        """Retorna as entidades do tipo ``modelo`` gravadas na partição."""
        ...


class DestinoRejeitados(Protocol):
    """Destino de quarentena para registros rejeitados."""

    def registrar(
        self, endpoint: str, particao: Mapping[str, int], rejeitados: Sequence[RegistroRejeitado]
    ) -> None:
        """Substitui os rejeitados do endpoint na partição."""
        ...
