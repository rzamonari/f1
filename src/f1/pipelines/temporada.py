"""Pipeline de temporada: catálogo do ano e ingestão de todas as sessões de um tipo."""

import logging
import time
from dataclasses import dataclass

from f1.domain.erros import IngestaoError, SessaoIndisponivelError
from f1.domain.tipos import TipoSessao
from f1.pipelines.analitico import executar_analitico
from f1.pipelines.catalogo import executar_catalogo
from f1.pipelines.portas import (
    DestinoParticionado,
    DestinoRejeitados,
    FonteOpenF1,
    LeitorParticionado,
)
from f1.pipelines.sessao import ParametrosSessao, executar_sessao, verificar_disponibilidade

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FalhaSessao:
    """Sessão que falhou e o motivo."""

    session_key: int
    motivo: str


@dataclass(frozen=True, slots=True)
class ResumoTemporada:
    """Resultado da ingestão de uma temporada."""

    ano: int
    tipo: TipoSessao
    processadas: tuple[int, ...]
    puladas: tuple[int, ...]
    falhas: tuple[FalhaSessao, ...]


@dataclass(frozen=True, slots=True)
class DestinosTemporada:
    """Repositórios usados pela temporada (agrupados para limitar o número de parâmetros)."""

    bruto: DestinoParticionado
    leitor_bruto: LeitorParticionado
    analitico: DestinoParticionado
    quarentena: DestinoRejeitados


def executar_temporada(
    ano: int,
    tipo: TipoSessao,
    fonte: FonteOpenF1,
    destinos: DestinosTemporada,
    parametros: ParametrosSessao,
) -> ResumoTemporada:
    """Atualiza o catálogo do ano e ingere cada sessão do tipo, com camada analítica.

    Sessões canceladas ou ainda não encerradas são puladas. A falha de uma sessão
    (``IngestaoError``) é isolada: a temporada segue e a falha entra no resumo.
    Qualquer outra exceção, como uma falha de escrita no banco, interrompe tudo.

    Raises:
        IngestaoError: Se a ingestão do catálogo falhar.
    """
    inicio = time.perf_counter()
    catalogo = executar_catalogo(
        ano, fonte, destinos.bruto, destinos.quarentena, parametros.limite_taxa_rejeicao
    )
    sessoes = sorted(
        (s for s in catalogo.sessoes if s.session_type is tipo), key=lambda s: s.date_start
    )
    processadas: list[int] = []
    puladas: list[int] = []
    falhas: list[FalhaSessao] = []
    for sessao in sessoes:
        chave = sessao.session_key
        try:
            verificar_disponibilidade(sessao, parametros)
        except SessaoIndisponivelError as exc:
            logger.info("sessão pulada", extra={"session_key": chave, "motivo": str(exc)})
            puladas.append(chave)
            continue
        try:
            executar_sessao(sessao, fonte, destinos.bruto, destinos.quarentena, parametros)
        except IngestaoError as exc:
            logger.exception("sessão falhou; seguindo para a próxima", extra={"session_key": chave})
            falhas.append(FalhaSessao(chave, str(exc)))
            continue
        executar_analitico(chave, destinos.leitor_bruto, destinos.analitico)
        processadas.append(chave)

    resumo = ResumoTemporada(ano, tipo, tuple(processadas), tuple(puladas), tuple(falhas))
    logger.info(
        "temporada concluída",
        extra={
            "pipeline": "temporada",
            "ano": ano,
            "tipo": str(tipo),
            "processadas": len(resumo.processadas),
            "puladas": len(resumo.puladas),
            "falhas": [f.session_key for f in resumo.falhas],
            "duracao_s": round(time.perf_counter() - inicio, 3),
        },
    )
    return resumo
