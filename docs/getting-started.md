# Primeiros passos

## Pré-requisitos

- Python 3.12 (a versão de desenvolvimento está em `.python-version`).
- Poetry 2.1 ou superior, instalado pelo instalador oficial ou pelo `pipx`.

## Instalação

```bash
poetry config virtualenvs.in-project true --local   # já versionado em poetry.toml
poetry env use 3.12
poetry install
```

!!! warning "VIRTUAL_ENV herdado do shell"
    Se a variável `VIRTUAL_ENV` estiver definida no seu shell (por exemplo, apontando para o Python do pyenv), o Poetry instala as dependências nesse interpretador em vez de criar o `.venv`. Remova a variável antes (`unset VIRTUAL_ENV` no bash, `Remove-Item Env:VIRTUAL_ENV` no PowerShell). Para conferir, use `poetry env info --path`, que deve apontar para `.venv`.

## Configuração mínima

Copie `.env.example` para `.env` e ajuste os valores, ou exporte as variáveis:

```bash
export F1_AMBIENTE=dev
export F1_CAMINHO_BANCO=./dados/f1.duckdb
```

A lista completa está em [Configuração](configuration.md). O projeto não lê o `.env` sozinho: carregue-o no shell ou no agendador.

## Primeira execução

```bash
# 1. Catálogo do ano: meetings e sessões
poetry run f1 catalogo --ano 2024

# 2. Uma sessão (corrida de Singapura 2024)
poetry run f1 sessao --session-key 9606

# 3. Tabelas analíticas da sessão
poetry run f1 analitico --session-key 9606
```

Cada comando escreve uma linha JSON por evento de log e termina com código `0` em sucesso e `1` em falha.

## Dashboard

```bash
poetry run streamlit run src/f1/dashboard/app.py
```

Abre em http://localhost:8501 a página **F1 — 5 Voltas Mais Rápidas por Circuito**, com filtros de ano e tipo de sessão e um bloco por circuito. O dashboard só lê o DuckDB e não chama a API. Uma sessão sem voltas mostra o comando `f1 sessao` que a ingere.

!!! note "Banco em uso"
    No Windows, o DuckDB bloqueia o arquivo para outros processos enquanto há uma conexão aberta. A CLI só abre a conexão durante cada gravação, de modo que o dashboard consegue ler enquanto ela consulta a API. Se a leitura coincidir com uma gravação, o dashboard mostra "ingestão em andamento"; clique em **Tentar novamente**. Do lado da CLI, a abertura do banco é repetida por até 10 s antes de falhar.

## Explorando os dados

```bash
poetry run python -c "import duckdb; print(duckdb.connect('dados/f1.duckdb', read_only=True).sql('SELECT * FROM ritmo_piloto ORDER BY ritmo_medio_s LIMIT 5'))"
```

As tabelas estão descritas em [Contratos de dados](data-contracts.md).
