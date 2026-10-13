"""Etapa comum de ingestão: validar um endpoint, enviar rejeitados à quarentena e medir."""

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from f1.domain.endpoints import Endpoint
from f1.domain.erros import TaxaRejeicaoExcedidaError
from f1.domain.validacao import ContratoInvalidoError, Conversor, ResultadoValidacao, validar
from f1.pipelines.portas import DestinoRejeitados

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ContagemEndpoint:
    """Contagens da ingestão de um endpoint em uma partição."""

    endpoint: str
    lidos: int
    validos: int
    rejeitados: int


def validar_endpoint(
    endpoint: Endpoint,
    registros: Iterable[Mapping[str, object]],
    particao: Mapping[str, int],
    quarentena: DestinoRejeitados,
    limite_taxa_rejeicao: float,
) -> ResultadoValidacao[object]:
    """Valida os registros de um endpoint e aplica as regras de rejeição.

    Registros de outra partição (por exemplo, outra ``session_key``) são rejeitados:
    eles escapariam da substituição da partição e quebrariam a idempotência.

    A quarentena da partição é sempre substituída (mesmo sem rejeitados), para que
    um reprocessamento não deixe rejeições antigas. Os rejeitados são gravados
    antes da verificação do limite, para ficarem disponíveis no diagnóstico.

    Raises:
        TaxaRejeicaoExcedidaError: Se a taxa de rejeição superar o limite.
    """
    resultado = validar(registros, _conversor_na_particao(endpoint.conversor, particao))
    quarentena.registrar(endpoint.nome, particao, resultado.rejeitados)
    contexto = {"endpoint": endpoint.nome, **particao}
    if not resultado.validos and not resultado.rejeitados:
        logger.warning("endpoint sem dados para a partição", extra=contexto)
    if resultado.rejeitados:
        logger.warning(
            "registros rejeitados enviados para a quarentena",
            extra={**contexto, "rejeitados": len(resultado.rejeitados)},
        )
    if resultado.taxa_rejeicao > limite_taxa_rejeicao:
        raise TaxaRejeicaoExcedidaError(
            f"{endpoint.nome}: taxa de rejeição {resultado.taxa_rejeicao:.1%} "
            f"acima do limite {limite_taxa_rejeicao:.1%}"
        )
    return resultado


def _conversor_na_particao(
    conversor: Conversor[object], particao: Mapping[str, int]
) -> Conversor[object]:
    def converter(registro: Mapping[str, object]) -> object:
        entidade = conversor(registro)
        for campo, esperado in particao.items():
            valor = getattr(entidade, campo)
            if valor != esperado:
                raise ContratoInvalidoError(f"{campo}={valor} fora da partição {campo}={esperado}")
        return entidade

    return converter


def contar(endpoint: Endpoint, resultado: ResultadoValidacao[object]) -> ContagemEndpoint:
    """Resume o resultado da validação de um endpoint."""
    return ContagemEndpoint(
        endpoint=endpoint.nome,
        lidos=len(resultado.validos) + len(resultado.rejeitados),
        validos=len(resultado.validos),
        rejeitados=len(resultado.rejeitados),
    )
