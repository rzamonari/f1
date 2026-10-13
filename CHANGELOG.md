# Changelog

Mudanças relevantes por versão, no formato [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Adicionado

- Cliente da OpenF1 com filtros por operador (`speed>=315`), valores repetidos, retry com backoff exponencial e `Retry-After`, e leitura em janelas de tempo.
- Contratos de entrada para 18 endpoints, com quarentena de registros rejeitados e limite de taxa de rejeição.
- Camada bruta no DuckDB, com substituição atômica de partições (`year`, `session_key`, `session_key` + `driver_number`).
- Camada analítica: ritmo por piloto (sem pit-out nem SC/VSC), estratégia de pneus e pit stops, e telemetria agregada por volta.
- CLI `f1` com os comandos `catalogo`, `sessao` (com `--com-telemetria` opcional), `temporada` e `analitico`.
- Logging estruturado em JSON com `id_execucao`.
- Dashboard Streamlit (`src/f1/dashboard/app.py`) com as 5 voltas mais rápidas por circuito, lendo do DuckDB.
- Documentação MkDocs Material, com modo claro/escuro, e atalhos `poetry run task docs` / `task docs-build` (taskipy).
- CI no GitHub Actions, com deploy da documentação no GitHub Pages a cada push na `main`.
- Hooks de pre-commit (`.pre-commit-config.yaml`) com Ruff, `poetry check --lock` e verificações básicas de arquivos.
