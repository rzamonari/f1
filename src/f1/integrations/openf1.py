"""Cliente REST da OpenF1 com filtros por operador, retry e leitura em janelas de tempo."""

import logging
import time
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx

from f1.domain.consulta import Filtro, Operador, ValorFiltro
from f1.domain.erros import FonteIndisponivelError, RequisicaoRecusadaError

logger = logging.getLogger(__name__)

STATUS_TRANSITORIOS = frozenset({429, 502, 503, 504})
# A OpenF1 responde 404 com este corpo quando a consulta é válida mas não há dados.
DETALHE_SEM_RESULTADOS = "No results found."

type Registro = dict[str, object]


def formatar_valor(valor: ValorFiltro) -> str:
    """Formata um valor de filtro; datas viram ISO 8601 em UTC, sem fuso explícito."""
    if isinstance(valor, datetime):
        return valor.astimezone(UTC).replace(tzinfo=None).isoformat()
    return str(valor)


def montar_query(filtros: Sequence[Filtro]) -> str:
    """Monta a query string com o operador no nome do parâmetro (``speed>=315``).

    O ``params`` do httpx trataria o operador como parte da chave e o codificaria
    junto com ``=``. Aqui, campo e valor são codificados e o operador é inserido
    entre eles. Uma sequência de valores repete o parâmetro.
    """
    partes: list[str] = []
    for filtro in filtros:
        valores = (
            filtro.valor
            if isinstance(filtro.valor, Sequence) and not isinstance(filtro.valor, str)
            else [filtro.valor]
        )
        operador = Operador(filtro.operador).value
        partes.extend(
            f"{quote(filtro.campo, safe='')}{operador}{quote(formatar_valor(v), safe='')}"
            for v in valores
        )
    return "&".join(partes)


def dividir_em_janelas(
    inicio: datetime, fim: datetime, tamanho: timedelta
) -> Iterator[tuple[datetime, datetime]]:
    """Divide ``[inicio, fim)`` em janelas contíguas ``[a, b)``, sem lacunas nem sobreposição.

    Raises:
        ValueError: Se ``tamanho`` não for positivo.
    """
    if tamanho <= timedelta(0):
        raise ValueError("o tamanho da janela deve ser positivo")
    atual = inicio
    while atual < fim:
        proximo = min(atual + tamanho, fim)
        yield atual, proximo
        atual = proximo


class ClienteOpenF1:
    """Lê endpoints da OpenF1.

    O ``httpx.Client`` é injetado já configurado com ``base_url`` e timeout. Quem
    cria o cliente é responsável por fechá-lo.
    """

    def __init__(
        self,
        cliente: httpx.Client,
        max_tentativas: int = 4,
        backoff_base_s: float = 1.0,
        pausa_entre_requisicoes_s: float = 0.0,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_tentativas < 1:
            raise ValueError("max_tentativas deve ser >= 1")
        self._cliente = cliente
        self._max_tentativas = max_tentativas
        self._backoff_base_s = backoff_base_s
        self._pausa_s = pausa_entre_requisicoes_s
        self._dormir = dormir

    def buscar(self, endpoint: str, filtros: Sequence[Filtro]) -> list[Registro]:
        """Retorna todos os registros do endpoint que atendem aos filtros.

        A OpenF1 não pagina: a resposta traz todos os registros de uma vez. Para
        endpoints de alto volume, use :meth:`buscar_em_janelas`.

        Raises:
            FonteIndisponivelError: Se a API continuar indisponível após os retries.
            RequisicaoRecusadaError: Se a API recusar a requisição (4xx definitivo).
        """
        caminho = f"/{endpoint}?{montar_query(filtros)}" if filtros else f"/{endpoint}"
        resposta = self._get_com_retry(caminho)
        if self._pausa_s > 0:
            self._dormir(self._pausa_s)
        if resposta.status_code == httpx.codes.NOT_FOUND:
            return []
        corpo = resposta.json()
        if not isinstance(corpo, list):
            raise RequisicaoRecusadaError(f"resposta inesperada de {endpoint}: esperada lista")
        return corpo

    def buscar_em_janelas(
        self,
        endpoint: str,
        filtros: Sequence[Filtro],
        inicio: datetime,
        fim: datetime,
        tamanho_janela: timedelta,
    ) -> Iterator[list[Registro]]:
        """Lê o endpoint em janelas ``date >= a`` e ``date < b`` que cobrem ``[inicio, fim)``.

        Gera um lote por janela, para que o chamador processe o volume aos poucos.
        """
        for a, b in dividir_em_janelas(inicio, fim, tamanho_janela):
            yield self.buscar(
                endpoint,
                [
                    *filtros,
                    Filtro("date", Operador.MAIOR_OU_IGUAL, a),
                    Filtro("date", Operador.MENOR, b),
                ],
            )

    def _get_com_retry(self, caminho: str) -> httpx.Response:
        ultimo_erro: Exception | None = None
        espera_sugerida_s: float | None = None
        for tentativa in range(1, self._max_tentativas + 1):
            try:
                resposta = self._cliente.get(caminho)
            except httpx.TransportError as exc:  # timeout, conexão recusada, DNS
                ultimo_erro, espera_sugerida_s = exc, None
            else:
                if resposta.status_code not in STATUS_TRANSITORIOS:
                    self._verificar_status(resposta, caminho)
                    return resposta
                ultimo_erro = httpx.HTTPStatusError(
                    f"status transitório {resposta.status_code}",
                    request=resposta.request,
                    response=resposta,
                )
                espera_sugerida_s = _ler_retry_after(resposta)
            if tentativa < self._max_tentativas:
                espera_s = self._backoff_base_s * 2 ** (tentativa - 1)
                if espera_sugerida_s is not None:
                    espera_s = max(espera_s, espera_sugerida_s)
                logger.warning(
                    "falha transitória na OpenF1; nova tentativa agendada",
                    extra={
                        "tentativa": tentativa,
                        "erro": type(ultimo_erro).__name__,
                        "espera_s": espera_s,
                    },
                )
                self._dormir(espera_s)
        raise FonteIndisponivelError(
            f"OpenF1 indisponível após {self._max_tentativas} tentativas"
        ) from ultimo_erro

    @staticmethod
    def _verificar_status(resposta: httpx.Response, caminho: str) -> None:
        """Aceita 2xx e o 404 de "sem resultados"; os demais erros são definitivos."""
        if resposta.status_code == httpx.codes.NOT_FOUND and _eh_sem_resultados(resposta):
            return
        try:
            resposta.raise_for_status()
        except httpx.HTTPStatusError as exc:
            endpoint = caminho.split("?", 1)[0]
            raise RequisicaoRecusadaError(
                f"OpenF1 recusou {endpoint} com status {resposta.status_code}"
            ) from exc


def _eh_sem_resultados(resposta: httpx.Response) -> bool:
    try:
        corpo = resposta.json()
    except ValueError:
        return False
    return isinstance(corpo, dict) and corpo.get("detail") == DETALHE_SEM_RESULTADOS


def _ler_retry_after(resposta: httpx.Response) -> float | None:
    """Lê ``Retry-After`` em segundos; o formato de data HTTP é ignorado."""
    valor = resposta.headers.get("Retry-After")
    if valor is None:
        return None
    try:
        return max(0.0, float(valor))
    except ValueError:
        return None
