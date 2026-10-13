# Desenvolvimento

## Fluxo local

```bash
poetry install
poetry run ruff check . --fix
poetry run ruff format .
poetry run pytest tests/unit --cov=f1 --cov-report=term-missing --cov-fail-under=50
poetry run pytest tests/integration -m integration
poetry run mkdocs build --strict
```

O mesmo conjunto roda na CI (`.github/workflows/ci.yml`), além de `poetry check --lock`.

### Documentação

```bash
poetry run task docs         # http://127.0.0.1:8000, recarrega ao salvar
poetry run task docs-build   # build estrito, igual ao da CI
poetry run task --list       # lista os atalhos
```

Os atalhos ficam em `[tool.taskipy.tasks]` no `pyproject.toml`.

A publicação é feita pela CI: a cada push na `main`, depois dos jobs `qualidade` e `integracao`, o job `documentacao` roda `mkdocs gh-deploy --strict` e atualiza a branch `gh-pages` (https://rzamonari.github.io/f1/). Nos PRs a CI só faz o build estrito. Não rode `gh-deploy` à mão.

## Convenções

- Nomes do domínio em português (`Sessao`, `Volta`). Termos consagrados da F1 (`stint`, `pit`, `grid`) ficam em inglês.
- Os campos das entidades brutas mantêm o nome da API, para que a camada bruta seja rastreável até a fonte.
- Imports absolutos a partir de `f1`. O Ruff proíbe imports relativos.
- Exceções capturadas pelo tipo. A captura ampla só existe em `cli.main`.
- Nada de `print`: use `logging` com mensagem fixa e dados em `extra`.

## Como adicionar um endpoint

1. Crie a `dataclass` em `domain/modelos.py`, com os campos da API e `X | None` para os opcionais.
2. Registre-a em `domain/endpoints.py` (`ENDPOINTS_SESSAO`, com `so_corrida=True` se for o caso). O conversor e a tabela são derivados das anotações.
3. Acrescente uma amostra real e reduzida em `tests/fixtures/openf1_amostras.json` e o mapeamento nos testes parametrizados.
4. Atualize [Contratos de dados](data-contracts.md) e o `CHANGELOG.md`.

Um campo novo em uma entidade existente vira uma coluna nova na próxima execução (`ADD COLUMN IF NOT EXISTS`). Remover um campo ou mudar o tipo dele exige migração manual do banco.

## Dependências

Só com `poetry add` (produção) ou `poetry add --group dev` (desenvolvimento), com `pyproject.toml` e `poetry.lock` no mesmo commit. Nunca use `pip`.

| Dependência | Uso |
|---|---|
| `httpx` | cliente HTTP com timeout e `MockTransport` |
| `duckdb` | banco analítico local |
| `streamlit` | dashboard |
| `pytest`, `pytest-cov` | testes e cobertura |
| `ruff` | lint, formatação e imports |
| `mkdocs`, `mkdocs-material` | documentação |
| `taskipy` | atalhos `poetry run task <nome>` |
