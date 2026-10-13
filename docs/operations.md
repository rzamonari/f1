# Operação

## Comandos

| Comando | Partição | Uso típico |
|---|---|---|
| `f1 catalogo --ano 2024` | `year` | diário, depois da meia-noite UTC (horário em que a OpenF1 atualiza `meetings`/`sessions`) |
| `f1 sessao --session-key 9606` | `session_key` | depois de cada sessão, respeitada a margem `F1_MARGEM_APOS_SESSAO_MIN` |
| `f1 sessao --session-key 9606 --com-telemetria` | também `session_key` + `driver_number` | sob demanda (volume alto, ver abaixo) |
| `f1 analitico --session-key 9606` | `session_key` | depois de `sessao`; recalcula as tabelas derivadas |
| `f1 temporada --ano 2024 --tipo Race` | catálogo + cada sessão | carga inicial ou reprocessamento de um ano; inclui o analítico |
| `streamlit run src/f1/dashboard/app.py` | — | dashboard somente leitura |

Todos terminam com código `0` em sucesso e `1` em falha. `temporada` retorna `1` se qualquer sessão falhar, mesmo que as outras tenham sido gravadas.

## Agendamento

Uma etapa por execução, chamada pelo agendador da plataforma (cron, job agendado, CI agendado):

```cron
# Catálogo do ano corrente, diariamente às 01:00 UTC
0 1 * * *  cd /opt/f1 && poetry run f1 catalogo --ano 2026
# Corridas do ano, às segundas às 06:00 UTC (idempotente: reprocessa as já gravadas)
0 6 * * 1  cd /opt/f1 && poetry run f1 temporada --ano 2026 --tipo Race
```

As variáveis de ambiente vêm do agendador, não de um `.env` (ver [Configuração](configuration.md)). Execuções concorrentes sobre o mesmo banco são toleradas: cada gravação abre o arquivo só por instantes e repete a abertura por até 10 s se ele estiver em uso. Ainda assim, prefira não sobrepor dois comandos que gravam, porque eles dividem a cota da API.

## Reprocessamento

Toda escrita substitui a partição inteira em uma transação, então reexecutar é seguro e produz o mesmo estado final:

- **Uma sessão:** `f1 sessao --session-key N` e depois `f1 analitico --session-key N`.
- **Um ano:** `f1 temporada --ano A --tipo Race` (ou `Qualifying`, `Practice`).
- **Telemetria de uma sessão:** `f1 sessao --session-key N --com-telemetria`. Cada piloto é uma transação própria. Se a execução for interrompida, os pilotos já concluídos ficam completos; basta repetir o comando.

## Volumes e tempos medidos

Medidos em 13/10/2026 (Windows 11, Python 3.12), na corrida de Singapura 2024 (`session_key` 9606, 20 pilotos), com os padrões de configuração (`F1_PAUSA_ENTRE_REQUISICOES_S=0.5`, janela de 10 min).

| Etapa | Registros | Requisições | Tempo | Pico de memória |
|---|---|---|---|---|
| `sessao` (endpoints leves) | 30.304 | 14 | ~14 s sem `429`; até ~80 s com uma espera de `Retry-After` | — |
| `sessao --com-telemetria` (só a telemetria) | 1.258.660 (`car_data` 622.380 + `location` 636.280), 0 rejeitados | ~720 (20 pilotos × 2 endpoints × 18 janelas) | ~2 a 3 min por piloto; **~40 a 55 min por corrida** | **195 MB** |
| `analitico` | 20 ritmo + 20 estratégia + 1.177 voltas de telemetria | 0 | 7,4 s | 143 MB |

Observações:

- **O gargalo é a cota da OpenF1, não o processamento.** Durante a telemetria a API respondeu `429` 33 vezes, sempre com `Retry-After: 60`. Cada piloto rende ~63 mil linhas (cerca de 31 mil por endpoint); validar e gravar esse volume leva poucos segundos.
- **A memória é limitada a um piloto por vez**, porque a gravação é por piloto. O pico não cresce com o número de pilotos.
- **O arquivo DuckDB é compacto:** com a telemetria completa dessa corrida e algumas outras sessões, o arquivo ficou com ~19 MB.
- O tempo total de parede da medição não serve de referência, porque o computador entrou em suspensão no meio. Os tempos por piloto acima vêm dos trechos contínuos. A cota também foi dividida com outra ingestão concorrente, então os números são conservadores.

## Monitoramento

Os logs são JSON, uma linha por evento, com `id_execucao`. Eventos úteis para alertas:

| Evento (`mensagem`) | Nível | Ação |
|---|---|---|
| `execução falhou` | ERROR | ver `exception`; reexecutar a partição |
| `sessão falhou; seguindo para a próxima` | ERROR | a temporada continuou; reprocessar a sessão |
| `registros rejeitados enviados para a quarentena` | WARNING | consultar a tabela `quarentena` |
| `falha transitória na OpenF1; nova tentativa agendada` | WARNING | frequente durante a telemetria; só preocupa se terminar em `FonteIndisponivelError` |
| `endpoint sem dados para a partição` | WARNING | esperado em alguns endpoints (ver [Troubleshooting](troubleshooting.md)) |
| `banco em uso por outro processo; nova tentativa agendada` | WARNING | outro processo leu ou gravou no mesmo instante |
