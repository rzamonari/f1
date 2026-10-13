# Troubleshooting

## `FonteIndisponivelError: OpenF1 indisponível após N tentativas`

**Causa:** respostas `429`, `502`, `503` ou `504`, ou timeouts, em todas as tentativas. A OpenF1 não publica seus limites de taxa.

**Solução:** aumente `F1_PAUSA_ENTRE_REQUISICOES_S` (por exemplo, para `1.0`) e, se preciso, `F1_MAX_TENTATIVAS`. O cliente já respeita `Retry-After`. Reexecute a mesma partição: a ingestão é idempotente.

## `RequisicaoRecusadaError: OpenF1 recusou /<endpoint> com status 4xx`

**Causa:** erro definitivo, que não é repetido (filtro inválido, endpoint inexistente). O `404` com `{"detail": "No results found."}` **não** é erro: significa que não há dados.

**Solução:** confira o `session_key` e o endpoint. Se a API mudou, atualize o catálogo em `domain/endpoints.py`.

## `TaxaRejeicaoExcedidaError: <endpoint>: taxa de rejeição X% acima do limite`

**Causa provável:** mudança de schema na API (campo renomeado, tipo novo, valor de enum novo, como um composto de pneu inédito).

**Diagnóstico:**

```sql
SELECT endpoint, particao, motivo, COUNT(*)
FROM quarentena
GROUP BY ALL
ORDER BY 4 DESC;
```

**Solução:** ajuste a entidade em `domain/modelos.py` ou `domain/tipos.py`, acrescente a amostra nas fixtures e reprocesse. Nada da partição foi gravado.

## `SessaoIndisponivelError: sessão N só pode ser ingerida após ...`

**Causa:** a sessão ainda não passou de `date_end` + `F1_MARGEM_APOS_SESSAO_MIN`. `session_result` e `starting_grid` saem minutos depois da publicação oficial, e `meetings`/`sessions` só são atualizados à meia-noite UTC.

**Solução:** aguarde e reexecute. Para dados recém-publicados, reprocessar no dia seguinte é seguro.

## Endpoints vazios (`WARNING endpoint sem dados para a partição`)

Esperado em alguns casos:

| Endpoint | Quando vem vazio |
|---|---|
| `starting_grid` | Em corridas: o grid é publicado na `session_key` da **classificação** |
| `session_result` | Antes da publicação oficial |
| `overtakes` | Cobertura incompleta |
| `team_radio` | Seleção parcial; cobertura bem menor a partir de 2026 |
| `championship_drivers`, `championship_teams` | Endpoints beta, só corridas |

## `Binder Error: Table "<tabela>" does not have a column with name "<campo>"`

**Causa:** o banco foi criado por uma versão anterior e a execução não passou por `criar_tabelas`.

**Solução:** qualquer comando da CLI acrescenta as colunas novas ao iniciar. Remoções e mudanças de tipo exigem migração manual.

## O Poetry instalou pacotes fora do `.venv`

**Causa:** a variável `VIRTUAL_ENV` está definida no shell, então o Poetry trata o interpretador apontado por ela como ambiente do projeto.

**Solução:** remova a variável e rode `poetry install` de novo. Veja [Primeiros passos](getting-started.md).
