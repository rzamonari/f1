# Arquitetura

## Módulos

```text
src/f1/
├── cli.py                    # argparse; monta dependências; único ponto com captura ampla
├── config/settings.py        # Configuracao (frozen) + carregar_configuracao()
├── domain/
│   ├── modelos.py            # uma entidade por endpoint (campos com o nome da API)
│   ├── analitico.py          # RitmoPiloto, EstrategiaPiloto, TelemetriaVolta
│   ├── tipos.py              # Gap, TipoSessao, Composto
│   ├── validacao.py          # conversores derivados das anotações + RegistroRejeitado
│   ├── endpoints.py          # catálogo dos endpoints ingeridos
│   ├── consulta.py           # Filtro/Operador (contrato entre pipelines e cliente)
│   └── erros.py              # IngestaoError e subclasses
├── transformations/          # funções puras: voltas, estrategia, telemetria
├── integrations/openf1.py    # ClienteOpenF1: query com operadores, retry, janelas
├── repositories/             # DuckDB: base genérica, bruto, analítico, quarentena
├── pipelines/                # portas (Protocol) + catalogo, sessao, telemetria, analitico, temporada
└── observability/logging.py  # JSON estruturado + id_execucao
```

A direção das dependências segue o padrão do time: `domain/` não importa nada do projeto, `transformations/` importa só `domain/`, e `pipelines/` recebe as implementações concretas como `Protocol`s (`FonteOpenF1`, `DestinoParticionado`, `LeitorParticionado`, `DestinoRejeitados`), injetadas pela CLI.

## Fluxo de dados

```text
OpenF1 ──► integrations/openf1 ──► domain/validacao ──► repositories (bruto)
 (HTTP)        (extração)        (válidos | rejeitados)       │
                                         │                    ▼
                                         ▼          transformations/* ──► repositories (analítico)
                                    quarentena
```

## Partições e idempotência

| Dado | Partição | Escrita |
|---|---|---|
| `meetings`, `sessions` | `year` | `DELETE` + `INSERT` na mesma transação |
| Endpoints de sessão | `session_key` | todos os endpoints da sessão em **uma** transação |
| `car_data`, `location` | `session_key` + `driver_number` | uma transação por piloto |
| Tabelas analíticas | `session_key` | as três tabelas em uma transação |
| `quarentena` | `endpoint` + `particao` | substituída a cada execução, mesmo vazia |

Toda execução recebe uma partição explícita (`--ano`, `--session-key`). `latest` é aceito em `f1 sessao`, mas é resolvido para um número concreto **antes** da ingestão e registrado no log.

Registros cuja chave não pertence à partição pedida (por exemplo, outra `session_key`) são rejeitados: eles escapariam do `DELETE` da partição e quebrariam a idempotência.

## Regras de rejeição

| Situação | Tratamento |
|---|---|
| Campo obrigatório ausente, tipo inválido, valor fora do domínio | Quarentena com motivo; segue |
| Taxa de rejeição de um endpoint acima de `F1_LIMITE_TAXA_REJEICAO` | Interrompe a partição, sem gravar nada dela (provável mudança de schema) |
| Endpoint sem dados (`404 No results found.` ou lista vazia) | `WARNING`; segue |
| Endpoint só de corrida em sessão que não é corrida | `INFO`; partição limpa |
| API indisponível após os retries (`429`, `502`, `503`, `504`, timeout) | Interrompe (`FonteIndisponivelError`) |
| Erro 4xx definitivo | Interrompe sem retry (`RequisicaoRecusadaError`) |
| Falha de escrita no DuckDB | Interrompe, com rollback |
| Erro de programação | Interrompe; nunca vira rejeição |

No comando `temporada`, uma `IngestaoError` interrompe só a sessão afetada. As demais seguem e o resumo final lista as falhas. Qualquer outra exceção interrompe tudo.

## Decisões técnicas

| Decisão | Escolha | Motivo |
|---|---|---|
| Armazenamento | DuckDB, arquivo único | Analítico e transacional. Uma corrida tem dezenas de milhares de linhas de telemetria por piloto, volume que pesa no SQLite e no pandas em memória |
| Carga em lote | Arquivo JSON Lines temporário + `read_json` | No DuckDB, `executemany` e listas como parâmetro levaram ~26 s para 50 mil linhas; o JSON Lines levou ~0,3 s, sem pandas/pyarrow |
| Schema | Derivado das `dataclass`es | Um único lugar define o contrato. A evolução é **só aditiva**: um campo novo vira coluna (`ADD COLUMN IF NOT EXISTS`); remover ou mudar o tipo exige migração manual |
| Conexão | Aberta por operação (`conexao_sob_demanda`) | O DuckDB bloqueia o arquivo para outros processos; abrir só ao gravar ou ler deixa o banco livre para o dashboard durante as chamadas à API |
| Datas | `TIMESTAMP` em UTC, sem fuso | Evita depender do `pytz` para ler `TIMESTAMPTZ`; a conversão para UTC acontece na validação |
| Tempos | `Decimal` → `DECIMAL(18, 3)` | Sem erro de arredondamento binário em tempos de volta e gaps |
| Cliente HTTP | `httpx` | Timeout explícito e `MockTransport` para testes sem rede |
| Query string | Montada à mão | O operador fica no nome do parâmetro (`speed>=315`), o que o `params` do httpx não representa |
| Retry | Laço explícito | Backoff exponencial + `Retry-After`, testável com `sleep` injetado |
| Orquestração | CLI + agendador | Uma etapa por execução; as funções de `pipelines/` não dependem do orquestrador |
