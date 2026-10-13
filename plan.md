# Plano do projeto F1: pipeline de dados da OpenF1

> Baseado em [doc_api.md](doc_api.md) (API OpenF1) e [skill.md](skill.md) (padrões do time de Engenharia de Dados).
> Os IDs entre parênteses (ex.: `DAD-12`) remetem às regras do `skill.md`.

---

## 1. Objetivo

Construir um pipeline de dados em Python que **extrai dados históricos de Fórmula 1 da API OpenF1**, valida, transforma e grava em um banco analítico local. O banco serve de base para análises (ritmo de corrida, estratégia de pneus, pit stops, clima, telemetria).

### Escopo

- Dados históricos (2023 em diante), que são gratuitos e não exigem autenticação.
- Ingestão por **sessão** (`session_key`) e por **temporada** (`year`), com reprocessamento idempotente.
- Execução por CLI, localmente ou em um agendador.

### Fora do escopo (nesta versão)

- Dados em tempo real (MQTT/WebSocket): exigem assinatura paga e autenticação OAuth2. A arquitetura deixa espaço para um cliente autenticado no futuro (seção 10).
- Download dos áudios de `team_radio`. Vamos guardar só a URL do MP3.
- Dashboard ou camada de visualização.

---

## 2. Situação atual do repositório

| Item | Estado | Ação |
|---|---|---|
| `pyproject.toml` | Mínimo, sem dependências nem configuração de ferramentas | Completar conforme `skill.md` §3.1 |
| `requires-python = ">=3.12"` | Sem limite superior | Trocar para `">=3.12,<3.14"` (POE-08) |
| `[tool.poetry].requires-poetry` | Ausente | Adicionar `">=2.1,<3.0"` (POE-09) |
| `readme = "README.md"` | **Arquivo não existe**, o que faz `poetry install` falhar | Criar `README.md` (DOC-08) |
| `.python-version` | `3.12.10` | OK |
| `src/f1/__init__.py` | Existe, vazio | Pacote importável `f1` (EST-01) |
| `tests/__init__.py` | Existe | Remover. Com `--import-mode=importlib`, não é necessário |
| `poetry.lock`, `.gitignore`, `mkdocs.yml`, `docs/`, CI | Ausentes | Criar na Fase 0 |

---

## 3. Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Nome de distribuição / importável | `f1` / `f1` | Já definido no `pyproject.toml` |
| Idioma dos nomes | Português no domínio (`Sessao`, `Volta`, `Stint`). Os campos da API mantêm o nome original na camada bruta | COD-01. Termos consagrados da F1 (`stint`, `pit`, `grid`) ficam em inglês |
| Cliente HTTP | `httpx` | Timeout explícito, `MockTransport` para testes sem rede (DAD-16, TST-04) |
| Armazenamento | **DuckDB** (arquivo único) | Analítico, transacional, lê e escreve Parquet. A telemetria (`car_data`, `location`) gera cerca de 500 mil linhas por piloto e sessão de corrida, volume grande para SQLite e para pandas em memória (§5.8) |
| Contratos | `dataclass(frozen=True, slots=True)` com conversão explícita | DAD-05, sem dependência extra |
| Configuração | `dataclass` + `os.environ` lido só na CLI | COD-21 a COD-24. Poucas variáveis, então sem `pydantic-settings` |
| Orquestração | CLI (`argparse`) + agendador da plataforma | Uma etapa por execução (§5.8). A lógica não depende do orquestrador (DAD-28) |
| Retry | Laço explícito e testável, sem `tenacity` | DAD-21 |

**Dependências de produção:** `httpx`, `duckdb`.
**Dependências de desenvolvimento:** `pytest`, `pytest-cov`, `ruff`, `mkdocs`, `mkdocs-material`.
Todas entram via `poetry add` / `poetry add --group dev` (POE-03, IA-07).

---

## 4. Particularidades da API que afetam o design

| Particularidade (doc_api.md) | Impacto no projeto |
|---|---|
| Filtros com operadores no nome do parâmetro (`speed>=315`, `date>=...`) | O cliente monta a query string manualmente a partir de uma lista de `Filtro(campo, operador, valor)`, porque `params` do httpx codificaria o operador como parte da chave |
| Vários valores repetem o parâmetro (`driver_number=4&driver_number=81`) | O construtor de query aceita listas |
| Sem paginação documentada | Endpoints de alto volume (`car_data`, `location`) são lidos em **janelas de tempo** (`date>=X&date<Y`) por piloto, com a sessão dividida em fatias de tamanho configurável (DAD-19, DAD-22) |
| Limites de taxa não publicados | Retry com backoff exponencial em 429/502/503/504, respeitando `Retry-After` (DAD-17, DAD-20). Pausa configurável entre requisições |
| `meetings`/`sessions` atualizados à meia-noite UTC; `session_result` e `starting_grid` saem minutos depois da publicação oficial | Ingerir uma sessão só depois de `date_end` + margem configurável. Reprocessar é seguro (idempotente) |
| Campos com tipo variável: `gap_to_leader`/`interval` (número, `"+N LAP"` ou `null`); `duration`/`gap_to_leader` em `session_result` (número ou array Q1–Q3 na quali) | O domínio modela explicitamente: `Gap` = segundos `Decimal` **ou** voltas de atraso **ou** líder. Quali vira três colunas `q1/q2/q3` |
| Campos depreciados: `country_code` em `drivers`, `pit_duration` em `pit` | Não usar. Ler `lane_duration` e `stop_duration` (este só a partir do GP dos EUA 2024, então pode ser nulo) |
| `segments_sector_*` são arrays e não existem em corridas | Guardar como lista nullable. Não filtrar por eles na API |
| `championship_*` em beta, só corridas; `overtakes` pode estar incompleto; `team_radio` com cobertura menor a partir de 2026 | Ingestão opcional, com aviso no log quando vier vazio. Documentar a limitação em `docs/troubleshooting.md` |
| `date` em ISO 8601 UTC | Converter para `datetime` timezone-aware em UTC (DAD-08) |

---

## 5. Arquitetura

### 5.1 Estrutura de módulos

```text
src/f1/
├── __init__.py
├── cli.py                         # argparse, monta dependências, captura ampla só aqui
├── config/
│   └── settings.py                # Configuracao (frozen) + carregar_configuracao()
├── domain/
│   ├── modelos.py                 # Meeting, Sessao, Piloto, Volta, Stint, PitStop, Clima, ...
│   ├── tipos.py                   # Gap, TipoSessao, Composto (StrEnum)
│   └── validacao.py               # conversores registro bruto → domínio, RegistroRejeitado
├── transformations/
│   ├── voltas.py                  # ritmo, melhor volta, voltas válidas (sem pit-out)
│   ├── estrategia.py              # stints + pits → estratégia por piloto
│   └── telemetria.py              # agregações por volta (vel. máx., % acelerador, uso de DRS)
├── integrations/
│   └── openf1.py                  # ClienteOpenF1: query com operadores, retry, janelas de tempo
├── repositories/
│   ├── duckdb_bruto.py            # tabelas por endpoint, substituição por session_key
│   ├── duckdb_analitico.py        # tabelas derivadas
│   └── duckdb_quarentena.py       # registros rejeitados
├── pipelines/
│   ├── catalogo.py                # meetings + sessions de um ano
│   ├── sessao.py                  # todos os endpoints de uma sessão
│   └── telemetria.py              # car_data/location em janelas
└── observability/
    └── logging.py                 # JSON estruturado + id_execucao
```

### 5.2 Fluxo de dados

```text
OpenF1 ──► integrations/openf1 ──► domain/validacao ──► repositories/duckdb_bruto
 (HTTP)        (extração)         (válidos | rejeitados)        │
                                          │                     ▼
                                          ▼          transformations/* ──► duckdb_analitico
                                  duckdb_quarentena
```

As dependências seguem a direção da §1.4: `pipelines/` recebe `Protocol`s (`FonteOpenF1`, `DestinoSessao`, `DestinoRejeitados`) e a CLI injeta as implementações concretas (DAD-02).

### 5.3 Partições e idempotência

| Dado | Chave de partição | Estratégia de escrita |
|---|---|---|
| `meetings`, `sessions` | `year` | `DELETE WHERE year = ?` + `INSERT` na mesma transação |
| Endpoints de sessão (drivers, laps, stints, pit, position, intervals, race_control, weather, session_result, starting_grid, overtakes, team_radio, championship_*) | `session_key` | `DELETE WHERE session_key = ?` + `INSERT` na mesma transação (DAD-12, DAD-26) |
| `car_data`, `location` | `session_key` + `driver_number` | Mesma estratégia, um piloto por transação, para limitar memória |
| Tabelas analíticas | `session_key` | Recalculadas a partir das tabelas brutas |
| Quarentena | `session_key` + endpoint | Substituição por partição |

Execução sempre com partição explícita (`--session-key`, `--ano`). Não existe "agora" implícito (DAD-11). `latest` pode ser aceito na CLI, mas é resolvido para um `session_key` concreto **antes** de iniciar e registrado no log.

### 5.4 Regras de rejeição (DAD-09)

| Situação | Tratamento |
|---|---|
| Registro com campo obrigatório ausente ou tipo inválido | Quarentena com motivo; seguir |
| Taxa de rejeição de um endpoint acima de `F1_LIMITE_TAXA_REJEICAO` (padrão 5%) | Interromper a sessão (provável mudança de schema) |
| Endpoint retorna lista vazia | `WARNING` e seguir (dado pode não existir para a sessão) |
| API indisponível após os retries | Interromper |
| Erro 4xx definitivo | Interromper sem retry |
| Falha de escrita no DuckDB | Interromper, com rollback |

### 5.5 Configuração (variáveis de ambiente)

| Variável | Obrigatória | Padrão | Segredo |
|---|---|---|---|
| `F1_AMBIENTE` | sim | — | não |
| `F1_CAMINHO_BANCO` | sim | — | não |
| `F1_API_BASE_URL` | não | `https://api.openf1.org/v1` | não |
| `F1_TIMEOUT_S` | não | `30` | não |
| `F1_MAX_TENTATIVAS` | não | `4` | não |
| `F1_PAUSA_ENTRE_REQUISICOES_S` | não | `0.5` | não |
| `F1_JANELA_TELEMETRIA_MIN` | não | `10` | não |
| `F1_LIMITE_TAXA_REJEICAO` | não | `0.05` | não |
| `F1_NIVEL_LOG` | não | `INFO` | não |
| `F1_OPENF1_USUARIO` / `F1_OPENF1_SENHA` | não (só tempo real, futuro) | — | **sim**, `repr=False` (SEG-04) |

Um `.env.example` com valores fictícios é versionado. O `.env` real não é (SEG-01).

### 5.6 CLI

```bash
poetry run f1 catalogo --ano 2024                   # meetings + sessions do ano
poetry run f1 sessao --session-key 9159             # todos os endpoints leves da sessão
poetry run f1 sessao --session-key 9159 --com-telemetria
poetry run f1 temporada --ano 2024 --tipo Race      # catálogo + todas as corridas do ano
poetry run f1 analitico --session-key 9159          # recalcula tabelas derivadas
```

Retorno `0` em sucesso e `1` em falha, com `logger.exception` (COD-14, LOG-05).

---

## 6. Fases de implementação

Cada fase é um PR pequeno (GIT-03), com testes, documentação e as verificações da §7 passando.

### Fase 0: Fundação do projeto
- [ ] Completar o `pyproject.toml` conforme `skill.md` §3.1, trocando `meu_projeto` por `f1` (Ruff, Pytest, Coverage, `requires-poetry`, `requires-python`, `[project.scripts] f1 = "f1.cli:main"`)
- [ ] `poetry add httpx duckdb` e `poetry add --group dev pytest pytest-cov ruff mkdocs mkdocs-material`
- [ ] Versionar `poetry.lock` junto com o `pyproject.toml` (POE-12)
- [ ] Criar `.gitignore` (§12.2, incluindo `*.duckdb`), `README.md`, `CHANGELOG.md` e `.env.example`
- [ ] Criar `mkdocs.yml` e as páginas mínimas de `docs/` (§8.2)
- [ ] Criar `.github/workflows/ci.yml` (§11.3)
- [ ] Remover `tests/__init__.py` e criar `tests/unit/`, `tests/integration/`, `tests/fixtures/` e `tests/conftest.py`
- [ ] `observability/logging.py` e `config/settings.py`, com testes

**Pronto quando:** CI verde com um teste real de `carregar_configuracao` e cobertura ≥ 50%.

### Fase 1: Cliente OpenF1
- [ ] `Filtro` + montagem de query com operadores e valores repetidos
- [ ] `ClienteOpenF1.buscar(endpoint, filtros)` com timeout, retry em falhas transitórias, `Retry-After`, `sleep` injetado
- [ ] `buscar_em_janelas(...)` para endpoints de alto volume (gerador)
- [ ] Testes com `httpx.MockTransport`: operadores codificados corretamente, retry/backoff, erro definitivo sem retry, causa preservada, janelas cobrindo o intervalo sem lacunas nem sobreposição

### Fase 2: Catálogo (meetings + sessions)
- [ ] Modelos `Meeting` e `Sessao`, conversores e validação
- [ ] Repositório DuckDB bruto + quarentena
- [ ] `pipelines/catalogo.py` e o comando `f1 catalogo --ano`
- [ ] Testes unitários com fakes e teste de integração DuckDB (`tmp_path`) para idempotência

### Fase 3: Dados de sessão (endpoints leves)
Na ordem: `drivers` → `laps` → `stints` → `pit` → `session_result` → `starting_grid` → `weather` → `race_control` → `position` → `intervals` → `overtakes` → `team_radio` → `championship_drivers` / `championship_teams`.
- [ ] Um conversor por endpoint, com testes parametrizados para os casos da §4 (gap `"+1 LAP"`, `null` para o líder, quali com array Q1–Q3, `stop_duration` ausente, campos depreciados ignorados)
- [ ] `pipelines/sessao.py` e o comando `f1 sessao --session-key`
- [ ] Endpoints só de corrida (`intervals`, `overtakes`, `championship_*`) pulados com `INFO` em outros tipos de sessão

### Fase 4: Telemetria (`car_data`, `location`)
- [ ] Leitura em janelas por piloto, gravação em lote por piloto
- [ ] Medir memória e tempo de uma corrida completa e registrar em `docs/operations.md`
- [ ] Flag `--com-telemetria` (o padrão é não ingerir, pelo volume)

### Fase 5: Camada analítica
- [ ] `transformations/voltas.py`: melhor volta, ritmo médio excluindo pit-out e voltas sob SC/VSC (cruzando com `race_control`)
- [ ] `transformations/estrategia.py`: estratégia por piloto (compostos, voltas por stint, tempo de pit)
- [ ] `transformations/telemetria.py`: agregados por volta
- [ ] Funções puras, com testes parametrizados (TST-07, TST-14)

### Fase 6: Temporada e operação
- [ ] Comando `f1 temporada --ano --tipo` (catálogo + laço de sessões, falha isolada por sessão com resumo final)
- [ ] Pular sessões canceladas (`is_cancelled`) ou ainda não encerradas
- [ ] `docs/operations.md` (agendamento, reprocessamento) e `docs/troubleshooting.md`

---

## 7. Qualidade e validação

Comandos obrigatórios em toda fase (IA-15, CI-01):

```bash
poetry check --lock
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest tests/unit --cov=f1 --cov-report=term-missing --cov-fail-under=50
poetry run mkdocs build --strict
poetry run pytest tests/integration -m integration   # DuckDB em tmp_path, sem rede
```

- Testes unitários **nunca** acessam a API real (TST-04). As fixtures em `tests/fixtures/` são respostas JSON pequenas da OpenF1, salvas uma vez e reduzidas. São dados públicos e não pessoais.
- Um teste de fumaça opcional contra a API real fica em `tests/integration/`, marcado `integration`, e não roda por padrão na CI.
- Testes de idempotência (rodar duas vezes e comparar o estado final) em todo pipeline.

---

## 8. Documentação (MkDocs Material)

| Página | Conteúdo específico do projeto |
|---|---|
| `index.md` | Propósito, escopo e fora de escopo (tempo real) |
| `getting-started.md` | Poetry, `poetry install`, primeira execução `f1 catalogo --ano 2024` |
| `configuration.md` | Tabela da §5.5 |
| `architecture.md` | §3 a §5 deste plano: decisão pelo DuckDB, partições, contratos por endpoint |
| `development.md` / `testing.md` | Fluxo local, fixtures da OpenF1 |
| `operations.md` | Agendamento, reprocessamento por sessão/ano, volumes medidos na Fase 4 |
| `troubleshooting.md` | 429, dados vazios em endpoints beta, `session_result` ainda não publicado |

---

## 9. Riscos

| Risco | Mitigação |
|---|---|
| Limites de taxa desconhecidos causando 429 em lote | Pausa configurável, backoff com `Retry-After`, ingestão por sessão |
| Mudança de schema na API (campos depreciados removidos após 2026) | Validação estrita + limite de taxa de rejeição interrompendo a execução |
| Volume da telemetria | Janelas de tempo, gravação por piloto, telemetria opcional |
| Dados incompletos (beta, `overtakes`, `team_radio`) | Tratar ausência como esperada, documentar e não falhar |
| Dados publicados com atraso | Margem após `date_end`; reprocessamento idempotente |

---

## 10. Evoluções futuras

- **Tempo real:** `integrations/openf1_auth.py` (token OAuth2 renovado antes de 1 h, no backend) e um consumidor MQTT em `integrations/`, gravando no mesmo repositório bruto.
- Exportação Parquet particionada por `year/session_key` para consumo externo.
- Orquestrador (Airflow/Dagster/Prefect) chamando as mesmas funções de `pipelines/` (DAD-28).

---

## 11. Decisões em aberto

1. **Armazenamento:** confirmar DuckDB. A alternativa sem dependência seria SQLite, que fica limitado para a telemetria.
2. **Telemetria no MVP:** a proposta é deixá-la para a Fase 4 e como opcional.
3. **Plataforma de CI:** o plano assume GitHub Actions.
4. **Idioma do domínio:** o plano assume português (`Sessao`, `Volta`), seguindo o `skill.md`.
