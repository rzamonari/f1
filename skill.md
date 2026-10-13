---
name: engenharia-python-dados
description: Padrões oficiais de desenvolvimento Python do time de Engenharia de Dados — estrutura src/, Poetry, pyproject.toml, Ruff, Pytest com cobertura mínima de 50%, MkDocs Material, segurança, logging, CI/CD e regras para agentes de IA. Use ao criar, modificar, revisar ou testar código Python nos projetos do time.
---

# Padrões de Engenharia Python — Engenharia de Dados

Este documento define os padrões oficiais de desenvolvimento Python do time de Engenharia de Dados. Ele é a referência para engenheiros e para agentes de IA que criam, modificam, revisam ou testam código nos projetos do time.

> **Regra geral:** nenhum código está pronto para integração na branch principal enquanto não seguir este documento e não passar por todas as verificações obrigatórias (seção 11). Uma exceção só vale se estiver justificada por escrito e aprovada na revisão.

---

## Sumário

0. [Como usar este documento](#0-como-usar-este-documento)
1. [Estrutura e arquitetura do projeto](#1-estrutura-e-arquitetura-do-projeto)
2. [Poetry: gerenciamento obrigatório](#2-poetry-gerenciamento-obrigatório)
3. [Configuração centralizada no pyproject.toml](#3-configuração-centralizada-no-pyprojecttoml)
4. [Padrões de código Python](#4-padrões-de-código-python)
5. [Arquitetura de Engenharia de Dados](#5-arquitetura-de-engenharia-de-dados)
6. [Ruff: lint, formatação e imports](#6-ruff-lint-formatação-e-imports)
7. [Pytest e cobertura mínima](#7-pytest-e-cobertura-mínima)
8. [Documentação com MkDocs Material](#8-documentação-com-mkdocs-material)
9. [Segurança e gestão de configuração](#9-segurança-e-gestão-de-configuração)
10. [Logging, erros e observabilidade](#10-logging-erros-e-observabilidade)
11. [CI/CD e validação automatizada](#11-cicd-e-validação-automatizada)
12. [Git, revisão de código e manutenção](#12-git-revisão-de-código-e-manutenção)
13. [Regras para agentes de IA](#13-regras-para-agentes-de-ia)
14. [Checklist de conformidade](#14-checklist-de-conformidade)
15. [Referência rápida de comandos](#15-referência-rápida-de-comandos)

---

## 0. Como usar este documento

### 0.1 Níveis normativos

| Marcador | Significado |
|---|---|
| **[OBRIGATÓRIO]** | Vale para todos os projetos. Uma exceção precisa de justificativa escrita no PR (ou em um ADR) e da aprovação de um revisor. |
| **[RECOMENDADO]** | Boa prática a adotar sempre que se aplicar. Quem decidir não seguir deve conseguir explicar o motivo na revisão. |
| **[OPCIONAL]** | Depende do contexto, da complexidade ou dos requisitos do projeto. |

As regras têm identificadores (ex.: `EST-03`, `POE-01`) para serem citadas em revisões de código e em relatórios de agentes.

### 0.2 Versões de referência

Os exemplos de comandos e de configuração deste documento valem **em conjunto** para a combinação abaixo. Se o projeto usar versões diferentes, confira a documentação da ferramenta antes de copiar a configuração.

| Ferramenta | Versão de referência | Observação |
|---|---|---|
| Python | 3.12 (projetos declaram `>=3.12,<3.14`) | Fixado em `.python-version` |
| Poetry | 2.x (mínimo 2.1) | Formato `[project]` (PEP 621) no `pyproject.toml` |
| poetry-core | `>=2.0.0,<3.0.0` | Backend de build |
| Ruff | 0.12.x | Configuração em `[tool.ruff]`, `[tool.ruff.lint]` e `[tool.ruff.format]` |
| pytest | 8.x | |
| pytest-cov | 6.x (traz coverage 7.x) | |
| MkDocs | 1.6.x (sempre `<2.0`) | MkDocs 2.0 é incompatível com plugins e temas atuais |
| Material for MkDocs | 9.x (mínimo 9.6) | Validado com 9.7 |
| mkdocstrings[python] | 0.29.x | Opcional |

Para atualizar a versão **major** de qualquer ferramenta, abra um PR específico, revise a configuração e atualize este documento.

### 0.3 Convenções dos exemplos

- `meu-projeto` é o **nome de distribuição** (aparece no `pyproject.toml` e no repositório).
- `meu_projeto` é o **nome importável** do pacote (o diretório em `src/`).
- Os comandos usam a sintaxe do bash. No PowerShell, rode os comandos de várias linhas em uma única linha ou troque `\` por `` ` ``.

---

## 1. Estrutura e arquitetura do projeto

### 1.1 Estrutura de referência

```text
meu-projeto/
├── pyproject.toml          # metadados, dependências e configuração de ferramentas
├── poetry.lock             # versões resolvidas (versionado, nunca editado à mão)
├── README.md               # visão rápida + link para a documentação
├── CHANGELOG.md            # mudanças relevantes por versão
├── .gitignore
├── .python-version         # versão do Python do projeto (ex.: 3.12)
├── mkdocs.yml
├── src/
│   └── meu_projeto/
│       ├── __init__.py
│       ├── config/          # carregamento e validação de configuração
│       ├── domain/          # entidades, regras de negócio, contratos
│       ├── services/        # casos de uso que coordenam domínio e portas
│       ├── repositories/    # persistência (bancos, data lake, arquivos)
│       ├── pipelines/       # orquestração das etapas de um fluxo de dados
│       ├── transformations/ # funções puras de transformação
│       ├── integrations/    # clientes de APIs e serviços externos
│       ├── utils/           # utilitários pequenos, genéricos e sem regra de negócio
│       └── cli.py           # ponto de entrada da linha de comando
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── conftest.py
├── docs/
│   ├── index.md
│   ├── getting-started.md
│   ├── architecture.md
│   ├── development.md
│   └── reference/
└── scripts/                 # automações auxiliares, fora do pacote distribuído
```

**Esta estrutura é uma referência, não um molde obrigatório.** Crie um diretório só quando existir uma responsabilidade real para ele. Um projeto pequeno pode ter apenas `config/`, `transformations/`, `pipelines/` e `cli.py`.

### 1.2 Nome de distribuição e nome importável

**[OBRIGATÓRIO] EST-01** — O diretório em `src/` precisa ter o nome importável do pacote, em `snake_case`. Esse nome não muda quando o nome de distribuição muda.

| Item | Exemplo | Onde aparece |
|---|---|---|
| Nome de distribuição | `meu-projeto` | `[project].name`, repositório, artefato publicado |
| Nome importável | `meu_projeto` | `src/meu_projeto/`, `import meu_projeto`, `--cov=meu_projeto` |

### 1.3 Regras de estrutura

| ID | Nível | Regra |
|---|---|---|
| EST-02 | **[OBRIGATÓRIO]** | Código de produção fica apenas em `src/<pacote>/`. Testes ficam em `tests/`, documentação em `docs/` e automações auxiliares em `scripts/`. |
| EST-03 | **[OBRIGATÓRIO]** | Use imports absolutos a partir do pacote principal (`from meu_projeto.domain.vendas import Venda`). Imports relativos são proibidos e o Ruff verifica isso (regra `TID252`). |
| EST-04 | **[OBRIGATÓRIO]** | Não pode haver dependências circulares entre módulos. Se aparecer um ciclo, mova o contrato compartilhado para um módulo mais baixo (normalmente `domain/`). |
| EST-05 | **[OBRIGATÓRIO]** | `scripts/` não pode conter lógica de negócio. Um script chama funções do pacote, e o pacote nunca importa de `scripts/`. |
| EST-06 | **[RECOMENDADO]** | Organize o código por domínio e por responsabilidade (`domain/vendas.py`, `transformations/vendas.py`), não por tipo técnico genérico (`helpers.py`, `functions.py`). |
| EST-07 | **[RECOMENDADO]** | Sinais de alerta: módulo com mais de ~400 linhas, função com mais de ~50 linhas, classe com mais de uma razão para mudar. Ao passar desses limites, avalie dividir. |
| EST-08 | **[RECOMENDADO]** | A lógica de negócio (`domain/`, `transformations/`) não importa clientes de banco, SDKs de nuvem nem bibliotecas HTTP. |
| EST-09 | **[OBRIGATÓRIO]** | Leitura, validação, transformação, escrita e orquestração ficam em funções ou módulos separados (detalhes na seção 5). |
| EST-10 | **[OBRIGATÓRIO]** | Só crie uma abstração (classe base, `Protocol`, fábrica) quando ela trouxer um benefício concreto, como permitir testes sem infraestrutura, ter duas implementações reais ou isolar um fornecedor. |
| EST-11 | **[OBRIGATÓRIO]** | Não crie classes utilitárias gigantes (`Utils`, `Helper`, `Manager`) nem funções genéricas que recebem flags para fazer coisas diferentes. |
| EST-12 | **[RECOMENDADO]** | `utils/` só guarda funções pequenas, sem estado e sem regra de negócio. Se uma função de `utils/` passar a conhecer o domínio, mova-a para o módulo de domínio correspondente. |

### 1.4 Direção das dependências entre camadas

```text
cli.py ─► pipelines/ ─► services/ ─► domain/
                │            │          ▲
                │            └──────────┤
                ▼                       │
        transformations/ ───────────────┘
                ▲
integrations/ ──┘ (implementam portas definidas no domínio ou nos pipelines)
repositories/ ──► domain/
config/ ◄── cli.py (só o ponto de entrada lê a configuração e injeta as dependências)
```

- `domain/` não importa nenhum outro módulo do projeto.
- `transformations/` importa apenas `domain/`.
- `integrations/` e `repositories/` conhecem a infraestrutura e o domínio, mas nunca importam `pipelines/` nem `cli.py`.
- `cli.py` (ou o operador do orquestrador) monta as dependências concretas e as entrega ao pipeline.

**[OPCIONAL]** Em projetos grandes, verifique esses limites automaticamente com `import-linter` (instalado com `poetry add --group dev import-linter`).

### 1.5 Exemplo: imports

```python
# Correto: import absoluto a partir do pacote
from meu_projeto.domain.vendas import Venda
from meu_projeto.transformations.vendas import consolidar_por_loja_e_dia
```

```python
# Incorreto: import relativo, ambíguo ao mover arquivos
from ..domain.vendas import Venda
from .vendas import consolidar_por_loja_e_dia

# Incorreto: manipular sys.path para "fazer funcionar"
import sys
sys.path.append("../src")
```

### 1.6 Exemplo: arquitetura simples de um pipeline

Pipeline que lê vendas de uma API, valida, consolida por loja e dia e grava em um banco:

```text
src/meu_projeto/
├── __init__.py
├── cli.py                       # monta dependências e chama o pipeline
├── config/
│   └── settings.py              # Configuracao + carregar_configuracao()
├── domain/
│   ├── vendas.py                # Venda, ResumoDiario, StatusVenda
│   └── validacao.py             # contrato de entrada e separação de rejeitados
├── transformations/
│   └── vendas.py                # consolidar_por_loja_e_dia() (função pura)
├── integrations/
│   └── api_vendas.py            # ClienteVendasApi (HTTP, paginação, retry)
├── repositories/
│   └── resumo_sqlite.py         # RepositorioResumoSqlite (escrita idempotente)
├── pipelines/
│   └── vendas.py                # executar_pipeline_vendas(): orquestração
└── observability/
    └── logging.py               # configuração de logging estruturado
```

| Etapa | Módulo | Depende de infraestrutura? | Como é testada |
|---|---|---|---|
| Extração | `integrations/api_vendas.py` | Sim (HTTP) | Unitário com transporte simulado; integração opcional |
| Validação | `domain/validacao.py` | Não | Unitário puro |
| Transformação | `transformations/vendas.py` | Não | Unitário puro e parametrizado |
| Persistência | `repositories/resumo_sqlite.py` | Sim (banco) | Integração com banco temporário |
| Orquestração | `pipelines/vendas.py` | Não (recebe portas) | Unitário com implementações falsas |

O código completo desse exemplo está na seção 5.9.

---

## 2. Poetry: gerenciamento obrigatório

### 2.1 Regras

| ID | Nível | Regra |
|---|---|---|
| POE-01 | **[OBRIGATÓRIO]** | O Poetry é a única ferramenta autorizada para gerenciar dependências e ambientes virtuais, instalar pacotes e executar o projeto. |
| POE-02 | **[OBRIGATÓRIO]** | É proibido usar `pip` diretamente: `pip install`, `pip uninstall`, `pip freeze`, `python -m pip` ou qualquer variação, seja em documentação, scripts, Dockerfiles, CI ou procedimentos operacionais. |
| POE-03 | **[OBRIGATÓRIO]** | Toda dependência é declarada no `pyproject.toml` usando `poetry add` / `poetry remove`. As versões resolvidas ficam no `poetry.lock`. |
| POE-04 | **[OBRIGATÓRIO]** | O `poetry.lock` é versionado e **nunca editado à mão**. Em caso de conflito de merge, resolva o `pyproject.toml` e regenere o lock com `poetry lock`. |
| POE-05 | **[OBRIGATÓRIO]** | O ambiente virtual (`.venv/`) nunca é versionado. |
| POE-06 | **[OBRIGATÓRIO]** | Dependências de produção ficam em `[project].dependencies`. Ferramentas de desenvolvimento (pytest, ruff, mkdocs) ficam no grupo `dev`. |
| POE-07 | **[OBRIGATÓRIO]** | Ferramentas e scripts rodam com `poetry run <comando>`, nunca a partir de instalações globais. |
| POE-08 | **[OBRIGATÓRIO]** | A faixa de Python suportada é declarada em `requires-python`, e a versão de desenvolvimento fica em `.python-version`. |
| POE-09 | **[OBRIGATÓRIO]** | A versão mínima do Poetry é declarada em `[tool.poetry].requires-poetry`. |
| POE-10 | **[RECOMENDADO]** | Cada nova dependência deve ser justificada no PR (o que resolve, alternativas consideradas, manutenção e licença). Prefira a biblioteca padrão quando ela for suficiente. |
| POE-11 | **[RECOMENDADO]** | Atualize dependências em PRs específicos, separados de mudanças funcionais. |

### 2.2 Instalação do próprio Poetry

O Poetry é instalado fora do projeto, pelo **instalador oficial** ou pelo **pipx**. Nunca instale com `pip install poetry`.

```bash
# Opção 1: pipx (recomendada em estações de trabalho)
pipx install poetry

# Opção 2: instalador oficial (Linux/macOS/CI)
curl -sSL https://install.python-poetry.org | python3 -
```

```powershell
# Windows (PowerShell): instalador oficial
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

### 2.3 Comandos padronizados (Poetry 2.x)

```bash
# Verificar a versão do Poetry
poetry --version

# Criar o ambiente virtual dentro do projeto (.venv/); grava em poetry.toml
poetry config virtualenvs.in-project true --local

# Selecionar o interpretador do projeto
poetry env use 3.12

# Instalar as dependências declaradas (respeita o poetry.lock)
poetry install

# Sincronizar o ambiente com o lock, removendo pacotes que não estão nele
poetry sync

# Adicionar dependência de produção
poetry add pandas

# Adicionar dependência com restrição explícita
poetry add "pandas@^2.2"

# Adicionar dependência de desenvolvimento
poetry add --group dev pytest

# Remover dependência
poetry remove pandas
poetry remove --group dev pytest

# Consultar dependências
poetry show
poetry show --tree
poetry show --outdated

# Atualizar uma dependência dentro da restrição declarada
poetry update pandas

# Validar pyproject.toml e a consistência com o poetry.lock
poetry check --lock

# Executar Python e ferramentas no ambiente gerenciado
poetry run python -m meu_projeto.cli --help
poetry run pytest

# Informações sobre o ambiente virtual
poetry env info
poetry env list
```

#### Ativar o ambiente virtual

No Poetry 2.x, `poetry shell` **não existe mais** no núcleo da ferramenta (passou para o plugin `poetry-plugin-shell`). O comando oficial é `poetry env activate`, que **imprime** o comando de ativação e não abre um shell novo:

```bash
# bash/zsh
eval $(poetry env activate)
```

```powershell
# PowerShell
Invoke-Expression (poetry env activate)
```

Como padrão, prefira `poetry run`. Ativar o ambiente é só uma conveniência no uso interativo.

#### Diferenças entre versões que afetam o time

| Uso antigo (Poetry 1.x) | Uso correto (Poetry 2.x) |
|---|---|
| `poetry shell` | `poetry env activate` (ou o plugin `poetry-plugin-shell`) |
| `poetry install --sync` | `poetry sync` |
| `poetry lock --no-update` | `poetry lock` (no 2.x, não atualiza versões já travadas) |
| `poetry lock` (re-resolver tudo) | `poetry lock --regenerate` |
| `poetry export` (nativo) | Exige o plugin `poetry-plugin-export` |
| `[tool.poetry.dependencies]` para metadados e dependências | `[project]` (PEP 621) para metadados e dependências de produção |
| `poetry install --no-dev` | `poetry install --only main` (ou `--without dev`) |

### 2.4 Lockfile no desenvolvimento local e no CI

| Situação | Comando | Comportamento |
|---|---|---|
| Clonar o projeto | `poetry install` | Instala exatamente o que está no `poetry.lock` |
| Depois de um `git pull` que mudou o lock | `poetry sync` | Alinha o ambiente ao lock e remove pacotes que sobraram |
| Adicionar ou remover dependência | `poetry add` / `poetry remove` | Atualiza `pyproject.toml` e `poetry.lock` juntos |
| Conflito de merge no lock | Resolver o `pyproject.toml` → `poetry lock` | Gera um lock coerente sem editar à mão |
| CI | `poetry check --lock` → `poetry install --no-interaction` | Falha se o lock estiver desatualizado em relação ao `pyproject.toml` |
| Imagem de produção | `poetry install --only main --no-interaction` | Instala só as dependências de produção |

**[OBRIGATÓRIO] POE-12** — Um PR que altera dependências inclui `pyproject.toml` **e** `poetry.lock` no mesmo commit.

### 2.5 Atualização controlada de dependências

```bash
# 1. Ver o que está desatualizado
poetry show --outdated

# 2. Atualizar dentro das restrições (uma dependência ou um grupo pequeno por vez)
poetry update httpx

# 3. Para mudar a versão major, altere a restrição explicitamente
poetry add "httpx@^0.28"

# 4. Validar
poetry check --lock
poetry run ruff check .
poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50
```

**[RECOMENDADO] POE-13** — Revise o changelog das dependências atualizadas, principalmente em mudanças major, e registre impactos no `CHANGELOG.md` do projeto.

**[RECOMENDADO] POE-14** — Mantenha a verificação de vulnerabilidades ativa na plataforma do repositório (Dependabot, Renovate, GitLab Dependency Scanning ou equivalente). Revise os alertas a cada atualização.

### 2.6 Exemplo correto e incorreto

```bash
# Incorreto: dependência fora do controle do lock
pip install requests
python -m pip install -r requirements.txt
pytest   # usa o pytest global, com versão desconhecida

# Correto
poetry add requests
poetry install
poetry run pytest
```

**[OBRIGATÓRIO] POE-15** — Não existe `requirements.txt` mantido à mão. Se um sistema externo exigir esse formato, gere o arquivo com `poetry-plugin-export` em uma etapa automatizada e não o versione como fonte da verdade.

---

## 3. Configuração centralizada no pyproject.toml

**[OBRIGATÓRIO] CFG-01** — Metadados, dependências, build, Ruff, Pytest e Coverage ficam no `pyproject.toml`. Não crie `setup.py`, `setup.cfg`, `ruff.toml`, `.ruff.toml`, `pytest.ini`, `tox.ini` ou `.coveragerc` para configurações que cabem no `pyproject.toml`.

**[OBRIGATÓRIO] CFG-02** — A configuração do MkDocs fica no `mkdocs.yml`, porque o MkDocs não lê o `pyproject.toml`.

### 3.1 Exemplo de referência (Poetry 2.x, Ruff 0.12, pytest 8, pytest-cov 6)

```toml
[project]
name = "meu-projeto"
version = "0.1.0"
description = "Pipeline de ingestão e consolidação de vendas."
readme = "README.md"
requires-python = ">=3.12,<3.14"
authors = [{ name = "Time de Engenharia de Dados", email = "engenharia-dados@example.com" }]
dependencies = [
    "httpx (>=0.28,<0.29)",
]

[project.scripts]
meu-projeto = "meu_projeto.cli:main"

[tool.poetry]
requires-poetry = ">=2.1,<3.0"
packages = [{ include = "meu_projeto", from = "src" }]

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-cov = "^6.0"
ruff = "^0.12"
mkdocs = "^1.6"
mkdocs-material = "^9.6"

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"

# ---------------------------------------------------------------- Ruff
[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]
# .venv, build, dist, .git e caches já são excluídos por padrão.
# "site" é a saída gerada pelo `mkdocs build` e não contém código-fonte.
extend-exclude = ["site"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle (erros)
    "W",    # pycodestyle (avisos)
    "F",    # pyflakes: nomes indefinidos, imports não usados
    "I",    # isort: organização de imports
    "N",    # pep8-naming
    "D",    # pydocstyle: docstrings
    "UP",   # pyupgrade: sintaxe moderna para a versão alvo
    "B",    # flake8-bugbear: bugs prováveis
    "C4",   # flake8-comprehensions
    "SIM",  # flake8-simplify
    "PTH",  # flake8-use-pathlib
    "DTZ",  # flake8-datetimez: datetimes sem timezone
    "T20",  # flake8-print: proíbe print()
    "BLE",  # flake8-blind-except
    "S",    # flake8-bandit: segurança
    "LOG",  # flake8-logging
    "G",    # flake8-logging-format
    "PT",   # flake8-pytest-style
    "TID",  # flake8-tidy-imports: proíbe imports relativos (com a config abaixo)
    "RUF",  # regras específicas do Ruff
]
ignore = [
    "E501",  # comprimento de linha: o formatador controla; strings longas e URLs são toleradas
    "D105",  # docstring em métodos mágicos (__repr__, __eq__...) é dispensável
    "D107",  # a docstring de __init__ fica na docstring da classe
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "S101",  # assert é a forma idiomática de verificar no pytest
    "S105",  # senhas fictícias em fixtures
    "S106",
    "D",     # docstrings não são exigidas em testes; o nome do teste descreve o cenário
]
"scripts/**/*.py" = [
    "T20",   # scripts auxiliares podem escrever no terminal
]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.isort]
known-first-party = ["meu_projeto"]

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"

[tool.ruff.format]
quote-style = "double"
docstring-code-format = true

# ---------------------------------------------------------------- Pytest
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--import-mode=importlib",
]
markers = [
    "integration: testes que dependem de recursos reais (banco, storage, rede); executados em etapa própria",
]
xfail_strict = true

# ---------------------------------------------------------------- Coverage
[tool.coverage.run]
source = ["meu_projeto"]
branch = true

[tool.coverage.report]
fail_under = 50
show_missing = true
skip_empty = true
exclude_also = [
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "@(abc\\.)?abstractmethod",
]

[tool.coverage.html]
directory = "htmlcov"
```

### 3.2 Notas sobre o exemplo

- **Dependências de produção** usam a sintaxe PEP 508 em `[project].dependencies`, que é o formato gravado por `poetry add` no Poetry 2.x. **Grupos de desenvolvimento** ficam em `[tool.poetry.group.<nome>.dependencies]`. Não edite essas seções à mão para incluir dependências: use `poetry add`.
- **`packages`** declara explicitamente o layout `src/`. Assim, o empacotamento não depende da detecção automática de diretórios.
- **`requires-python = ">=3.12,<3.14"`**: o limite superior vale para versões validadas pelo time. Para ampliar a faixa, abra um PR que rode a CI na nova versão.
- **Cobertura**: `fail_under = 50` garante que `--cov` sozinho já aplica o piso. O comando oficial também passa `--cov-fail-under=50` explicitamente (seção 7), com o mesmo valor, o que deixa o critério visível nos logs de CI.
- **`source = ["meu_projeto"]`** usa o mesmo alvo do `--cov=meu_projeto`. Não troque por `source_pkgs` combinado com `--cov=<pacote>`: a combinação gera o aviso `module-not-measured`.
- **`branch = true`**: a cobertura considera linhas e desvios condicionais. O percentual reportado é a métrica combinada.
- As faixas de versão do grupo `dev` são exemplos coerentes com a seção 0.2. Use as versões que `poetry add` resolver no momento da criação do projeto e mantenha a mesma major.

---

## 4. Padrões de código Python

Base: PEP 8 (estilo), PEP 257 (docstrings), PEP 484 e seguintes (tipagem). Quando há uma regra do Ruff correspondente, o Ruff é a autoridade.

### 4.1 Nomenclatura

| Elemento | Convenção | Exemplo correto | Exemplo incorreto |
|---|---|---|---|
| Pacote/módulo | `snake_case`, curto | `transformations/vendas.py` | `Transformations/VendasUtils.py` |
| Classe | `PascalCase` | `ResumoDiario` | `resumo_diario` |
| Exceção | `PascalCase` terminando em `Error` (regra `N818`) | `ContratoInvalidoError` | `ErroContrato` |
| Função/método | `snake_case`, verbo | `consolidar_por_loja_e_dia` | `processa`, `doStuff` |
| Variável | `snake_case`, substantivo descritivo | `vendas_validas` | `df2`, `tmp`, `x` |
| Constante | `UPPER_SNAKE_CASE`, no nível do módulo | `STATUS_TRANSITORIOS` | `statusTransitorios` |
| Membro de `Enum` | `UPPER_SNAKE_CASE` | `StatusVenda.CONFIRMADA` | `StatusVenda.confirmada` |
| Privado ao módulo/classe | prefixo `_` | `_normalizar_cnpj` | — |

**[RECOMENDADO] COD-01** — Escolha um idioma para os nomes do domínio (português ou inglês) e mantenha-o no projeto inteiro. Termos técnicos consagrados (`client`, `repository`, `batch`) podem ficar em inglês.

### 4.2 Type hints

| ID | Nível | Regra |
|---|---|---|
| COD-02 | **[OBRIGATÓRIO]** | Toda função, método e classe pública tem parâmetros e retorno anotados. |
| COD-03 | **[OBRIGATÓRIO]** | Use a sintaxe moderna: `list[str]`, `dict[str, int]`, `X \| None`. Não use `List`, `Optional` ou `Union` de `typing` (o Ruff `UP` corrige). |
| COD-04 | **[OBRIGATÓRIO]** | Evite `Any`. Use tipos concretos, `object` (quando o valor não é usado), `Mapping[str, object]` para registros brutos, `Protocol` ou `TypedDict`. Quando `Any` for inevitável, por exemplo em uma fronteira com uma biblioteca sem tipos, isole-o no módulo de integração. |
| COD-05 | **[RECOMENDADO]** | Em parâmetros, prefira tipos abstratos (`Iterable`, `Sequence`, `Mapping` de `collections.abc`). Em retornos, prefira tipos concretos. |
| COD-06 | **[OPCIONAL]** | Verificação estática com `mypy` ou `pyright` (`poetry add --group dev mypy`). Se o projeto adotar, a verificação entra na CI. |

```python
# Correto
from collections.abc import Iterable, Mapping


def contar_por_status(registros: Iterable[Mapping[str, object]]) -> dict[str, int]:
    """Conta registros agrupando pelo campo ``status``."""
    contagem: dict[str, int] = {}
    for registro in registros:
        status = str(registro.get("status", "desconhecido"))
        contagem[status] = contagem.get(status, 0) + 1
    return contagem
```

```python
# Incorreto: sem tipos, Any desnecessário, typing legado
from typing import Any, Dict, List, Optional


def contar(regs: List[Any], filtro: Optional[str] = None) -> Dict:
    ...
```

### 4.3 Docstrings

**[OBRIGATÓRIO] COD-07** — Módulos, classes e funções públicas têm docstring no **estilo Google**, verificado pelo Ruff (`D` + `convention = "google"`).

**[OBRIGATÓRIO] COD-08** — A docstring explica **o que** a função faz, o contrato (entradas, saídas, exceções) e decisões não óbvias. Ela não repete a assinatura nem descreve linha a linha.

```python
def substituir_particao(self, data_referencia: date, resumos: Sequence[ResumoDiario]) -> None:
    """Substitui todos os resumos de uma data de forma atômica.

    A operação é idempotente: executá-la duas vezes com a mesma entrada produz
    o mesmo estado final.

    Args:
        data_referencia: Data da partição a ser substituída.
        resumos: Resumos consolidados da data. Uma sequência vazia limpa a partição.

    Raises:
        sqlite3.DatabaseError: Se a transação falhar; nenhuma alteração é mantida.
    """
```

Funções privadas simples podem dispensar docstring quando o nome e os tipos já bastam.

### 4.4 Funções pequenas e coesas

| ID | Nível | Regra |
|---|---|---|
| COD-09 | **[OBRIGATÓRIO]** | Uma função tem uma responsabilidade. Se a descrição precisar de "e" ("lê **e** valida **e** grava"), divida a função. |
| COD-10 | **[RECOMENDADO]** | Prefira funções puras (saída depende só da entrada, sem efeitos colaterais) para transformações e regras de negócio. |
| COD-11 | **[OBRIGATÓRIO]** | Não use parâmetro booleano que muda o comportamento da função (`processar(df, modo_completo=True)`). Crie duas funções com nomes claros. |
| COD-12 | **[RECOMENDADO]** | Com mais de ~5 parâmetros, agrupe-os em uma `dataclass` de parâmetros ou de configuração. |
| COD-13 | **[OBRIGATÓRIO]** | Não use argumentos padrão mutáveis (`def f(itens=[])`). O Ruff `B006` detecta isso. |

### 4.5 Tratamento de exceções

| ID | Nível | Regra |
|---|---|---|
| COD-14 | **[OBRIGATÓRIO]** | Capture exceções específicas. `except Exception` só é permitido no ponto de entrada (CLI, task do orquestrador), para registrar com `logger.exception` e **relançar** ou sair com código de erro. |
| COD-15 | **[OBRIGATÓRIO]** | `except:` sem tipo e `except Exception: pass` são proibidos. |
| COD-16 | **[OBRIGATÓRIO]** | Ao transformar uma exceção em outra, preserve a causa com `raise NovaError(...) from exc`. |
| COD-17 | **[RECOMENDADO]** | Defina exceções de domínio (`ContratoInvalidoError`, `TaxaRejeicaoExcedidaError`) para erros que o chamador precisa distinguir. |
| COD-18 | **[RECOMENDADO]** | Mantenha o bloco `try` mínimo, só com a linha que pode lançar a exceção esperada. |

```python
# Correto: exceção específica, contexto adicionado, causa preservada
try:
    valor = Decimal(str(registro["valor_bruto"]))
except InvalidOperation as exc:
    raise ContratoInvalidoError(f"valor_bruto inválido: {registro['valor_bruto']!r}") from exc
```

```python
# Incorreto: esconde a causa e continua com estado inválido
try:
    valor = Decimal(str(registro["valor_bruto"]))
except Exception:
    print("erro no valor")
    valor = Decimal(0)
```

### 4.6 Context managers e recursos externos

**[OBRIGATÓRIO] COD-19** — Arquivos, conexões, sessões HTTP, cursores e locks são abertos com `with`, para garantir a liberação mesmo quando há erro.

**[OBRIGATÓRIO] COD-20** — Quem cria um recurso é responsável por fechá-lo. Funções que **recebem** um cliente ou uma conexão não o fecham.

```python
import sqlite3
from contextlib import closing

# Correto: closing() fecha a conexão; o "with conexao" controla a transação
with closing(sqlite3.connect(caminho_banco)) as conexao, conexao:
    conexao.execute("DELETE FROM resumo WHERE data = ?", (data_referencia.isoformat(),))
```

> Atenção: no `sqlite3`, `with conexao:` **não fecha** a conexão, só faz commit ou rollback. Conheça a semântica do context manager de cada biblioteca.

### 4.7 Configuração separada do código

| ID | Nível | Regra |
|---|---|---|
| COD-21 | **[OBRIGATÓRIO]** | Valores que mudam entre ambientes (URLs, caminhos, credenciais, tamanhos de lote, níveis de log) vêm de variáveis de ambiente ou de um mecanismo de configuração. Eles não ficam no código. |
| COD-22 | **[OBRIGATÓRIO]** | A configuração é lida e validada **uma vez**, no ponto de entrada, e depois injetada. Módulos internos não chamam `os.environ` / `os.getenv`. |
| COD-23 | **[OBRIGATÓRIO]** | A configuração é representada por um objeto imutável e tipado (`@dataclass(frozen=True)`). |
| COD-24 | **[OPCIONAL]** | `pydantic-settings` vale a pena quando houver muitas variáveis, tipos complexos ou validação elaborada. Para poucas variáveis, use a biblioteca padrão (exemplo na seção 9.3). |

### 4.8 Caminhos com pathlib

**[OBRIGATÓRIO] COD-25** — Manipule caminhos com `pathlib.Path`. Não use `os.path` (o Ruff `PTH` detecta).

```python
# Correto
from pathlib import Path

saida = Path(configuracao.diretorio_saida) / "vendas" / f"{data_referencia:%Y-%m-%d}.csv"
saida.parent.mkdir(parents=True, exist_ok=True)
with saida.open("w", encoding="utf-8", newline="") as arquivo:
    ...
```

```python
# Incorreto
import os

saida = os.path.join(diretorio, "vendas/" + data + ".csv")
if not os.path.exists(os.path.dirname(saida)):
    os.makedirs(os.path.dirname(saida))
f = open(saida, "w")
```

**[OBRIGATÓRIO] COD-26** — Sempre informe `encoding="utf-8"` (ou o encoding real da fonte) ao abrir arquivos de texto.

### 4.9 dataclasses, Enum, Protocol e classes de domínio

| Ferramenta | Quando usar | Exemplo |
|---|---|---|
| `@dataclass(frozen=True, slots=True)` | Entidades e valores de domínio, resultados e configuração | `Venda`, `ResumoDiario`, `Configuracao` |
| `enum.StrEnum` / `Enum` | Conjunto fechado de valores | `StatusVenda`, `Ambiente` |
| `typing.Protocol` | Contrato de uma dependência externa que será injetada (porta) | `FonteVendas`, `DestinoResumo` |
| `TypedDict` | Estrutura de dicionário vinda de JSON quando converter para dataclass não compensa | Payload bruto de API |
| Classe comum | Objeto com estado e comportamento real (cliente com sessão, repositório com conexão) | `ClienteVendasApi` |

**[RECOMENDADO] COD-27** — Prefira objetos imutáveis (`frozen=True`, tuplas, `frozenset`). A imutabilidade elimina uma classe inteira de bugs em pipelines com várias etapas.

**[RECOMENDADO] COD-28** — Não crie classe só para agrupar funções sem estado. Um módulo já cumpre esse papel.

### 4.10 Estado global

**[OBRIGATÓRIO] COD-29** — Não use estado global mutável: variáveis de módulo alteradas em tempo de execução, `global`, singletons com estado ou caches implícitos. Constantes imutáveis no nível do módulo são permitidas.

**[OBRIGATÓRIO] COD-30** — Importar um módulo não pode ter efeitos colaterais, como abrir conexões, ler variáveis de ambiente, configurar logging ou fazer chamadas de rede.

### 4.11 Comentários e código morto

| ID | Nível | Regra |
|---|---|---|
| COD-31 | **[OBRIGATÓRIO]** | Não deixe código comentado nem funções sem uso. O histórico fica no Git. |
| COD-32 | **[RECOMENDADO]** | Um comentário explica **por que**, não **o que**. `# incrementa i` é ruído. `# a API retorna no máximo 500 itens mesmo com limit maior` é informação útil. |
| COD-33 | **[RECOMENDADO]** | Elimine duplicação relevante (mesma regra de negócio em dois lugares). Tolere duplicação trivial quando a abstração necessária para eliminá-la for artificial. |
| COD-34 | **[OBRIGATÓRIO]** | Não use `print()` em código de produção. Use `logging` (o Ruff `T20` detecta). |

### 4.12 Exemplo de refatoração: antes e depois

**Antes**: leitura, validação, transformação, escrita, configuração e log misturados em uma função, sem nenhuma forma de testar sem disco e sem variáveis de ambiente.

```python
import csv
import os

TOTAL = {}


def processa(arquivo):
    try:
        f = open(os.path.join(os.getenv("DIR_ENTRADA"), arquivo))
        for linha in csv.DictReader(f):
            if linha["status"] == "confirmada":
                chave = linha["loja"] + "|" + linha["data"]
                TOTAL[chave] = TOTAL.get(chave, 0) + float(linha["valor"])
        out = open(os.path.join(os.getenv("DIR_SAIDA"), "resumo.csv"), "a")
        for k, v in TOTAL.items():
            out.write(k.replace("|", ",") + "," + str(v) + "\n")
        print("ok")
    except Exception as e:
        print("erro", e)
```

Problemas: estado global (`TOTAL` acumula entre chamadas); `float` para valores monetários; arquivos que nunca são fechados; modo `"a"`, que não é idempotente (reprocessar duplica os dados); `except Exception` que esconde falhas; `print`; configuração lida no meio da lógica; nenhuma unidade testável isoladamente.

**Depois**: responsabilidades separadas, função pura de transformação, I/O nas bordas e escrita idempotente.

```python
"""Consolidação de vendas a partir de arquivos CSV."""

import csv
import logging
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

STATUS_CONFIRMADA = "confirmada"


def ler_vendas_csv(caminho: Path) -> Iterator[dict[str, str]]:
    """Lê vendas de um CSV linha a linha, sem carregar o arquivo inteiro em memória."""
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        yield from csv.DictReader(arquivo)


def consolidar(vendas: Iterable[Mapping[str, str]]) -> dict[tuple[str, str], Decimal]:
    """Soma o valor das vendas confirmadas por loja e data."""
    totais: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for venda in vendas:
        if venda["status"] == STATUS_CONFIRMADA:
            totais[(venda["loja"], venda["data"])] += Decimal(venda["valor"])
    return dict(totais)


def gravar_resumo_csv(totais: Mapping[tuple[str, str], Decimal], destino: Path) -> None:
    """Grava o resumo sobrescrevendo o destino (reprocessar produz o mesmo arquivo)."""
    temporario = destino.with_suffix(".tmp")
    with temporario.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["loja", "data", "valor_total"])
        for (loja, data), valor in sorted(totais.items()):
            escritor.writerow([loja, data, f"{valor:.2f}"])
    temporario.replace(destino)  # troca atômica no mesmo sistema de arquivos


def processar_arquivo(entrada: Path, saida: Path) -> None:
    """Orquestra leitura, consolidação e gravação de um arquivo de vendas."""
    totais = consolidar(ler_vendas_csv(entrada))
    gravar_resumo_csv(totais, saida)
    logger.info("resumo gravado", extra={"entrada": entrada.name, "grupos": len(totais)})
```

Ganhos: `consolidar` é testada com uma lista de dicionários, sem tocar no disco. Os caminhos chegam por parâmetro (a configuração é resolvida no ponto de entrada). `Decimal` mantém a precisão monetária. A escrita via arquivo temporário e `replace` é atômica e idempotente. Erros não são mais escondidos e chegam ao ponto de entrada com stack trace.

---

## 5. Arquitetura de Engenharia de Dados

### 5.1 Separação das etapas

**[OBRIGATÓRIO] DAD-01** — Todo pipeline separa, em funções ou módulos distintos:

1. **Extração**: lê da fonte (API, banco, arquivo, fila). Não aplica regra de negócio.
2. **Validação**: confere o contrato de entrada e separa registros válidos e rejeitados.
3. **Transformação**: aplica regras de negócio com funções puras sempre que possível.
4. **Carga**: persiste no destino de forma idempotente e transacional quando a tecnologia permitir.
5. **Orquestração**: encadeia as etapas, mede, registra logs e decide se falha ou continua.

**[OBRIGATÓRIO] DAD-02** — A orquestração recebe extração e carga como **dependências injetadas** (objetos que seguem um `Protocol`). Assim, o fluxo pode ser testado sem infraestrutura real.

### 5.2 Contratos de entrada e saída

| ID | Nível | Regra |
|---|---|---|
| DAD-03 | **[OBRIGATÓRIO]** | Cada pipeline documenta o contrato de entrada (campos, tipos, obrigatoriedade, domínios válidos) e de saída (schema, granularidade, chave, particionamento). |
| DAD-04 | **[OBRIGATÓRIO]** | Dados externos são validados **antes** da transformação. A transformação recebe objetos de domínio já validados. |
| DAD-05 | **[RECOMENDADO]** | Representar o contrato em código: `dataclass` com conversão explícita (exemplo na 5.9), `pydantic`, `pandera` ou o recurso nativo da engine adotada. Escolha uma abordagem por projeto. |
| DAD-06 | **[RECOMENDADO]** | Verificações de qualidade na saída (unicidade da chave, nulos em campos obrigatórios, contagens coerentes com a entrada) em pipelines que alimentam consumidores críticos. |
| DAD-07 | **[OBRIGATÓRIO]** | Use `Decimal` (ou o tipo decimal da engine) para valores monetários. `float` é proibido para dinheiro. |
| DAD-08 | **[OBRIGATÓRIO]** | Datas e horas são timezone-aware (`datetime.now(UTC)`). O armazenamento é em UTC, salvo contrato explícito em contrário (o Ruff `DTZ` detecta datetimes sem timezone). |

### 5.3 Dados inválidos e registros rejeitados

**[OBRIGATÓRIO] DAD-09** — Para cada pipeline, defina por escrito quais erros **interrompem** a execução e quais viram **rejeições de dados**:

| Situação | Tratamento |
|---|---|
| Registro individual fora do contrato (campo ausente, tipo inválido) | Rejeitar o registro com motivo e seguir |
| Taxa de rejeição acima do limite configurado | Interromper (provável mudança de schema na fonte) |
| Fonte indisponível depois dos retries | Interromper |
| Falha de escrita no destino | Interromper, com rollback quando houver transação |
| Configuração inválida | Interromper antes de qualquer processamento |
| Erro de programação (`TypeError`, `KeyError` inesperado) | Interromper. Nunca tratar como rejeição. |

**[OBRIGATÓRIO] DAD-10** — Registros rejeitados são persistidos em um destino identificável (tabela ou diretório de quarentena) com: registro original (com dados sensíveis mascarados quando necessário), motivo, identificador da execução e data de referência. Rejeitar silenciosamente é proibido.

### 5.4 Idempotência, reprocessamento e recuperação

| ID | Nível | Regra |
|---|---|---|
| DAD-11 | **[OBRIGATÓRIO]** | Execute o pipeline para um período ou partição explícita (`--data-referencia 2026-10-12`), nunca para "agora" implícito. |
| DAD-12 | **[OBRIGATÓRIO]** | Reexecutar o pipeline com os mesmos parâmetros produz o mesmo estado final. Estratégias: substituir a partição (`DELETE` + `INSERT` na mesma transação, `INSERT OVERWRITE`), `MERGE`/upsert por chave natural, ou escrita em temporário seguida de troca atômica. |
| DAD-13 | **[OBRIGATÓRIO]** | `append` sem chave de deduplicação é proibido em tabelas que podem ser reprocessadas. |
| DAD-14 | **[RECOMENDADO]** | Em cargas incrementais, guarde a marca d'água (último timestamp ou ID processado) **depois** da carga confirmada, nunca antes. |
| DAD-15 | **[RECOMENDADO]** | Processos longos registram checkpoints por lote, para retomar do último lote confirmado. |

### 5.5 Integrações: timeouts, retries e paginação

| ID | Nível | Regra |
|---|---|---|
| DAD-16 | **[OBRIGATÓRIO]** | Toda chamada de rede tem timeout explícito (conexão e leitura). |
| DAD-17 | **[OBRIGATÓRIO]** | Retry só para falhas transitórias (timeout, erro de conexão, HTTP 429/502/503/504), com limite de tentativas e backoff exponencial. Erros definitivos (400, 401, 403, 404, 422) não são repetidos. |
| DAD-18 | **[OBRIGATÓRIO]** | Retry só em operações idempotentes. `POST` não idempotente só é repetido com chave de idempotência suportada pela API. |
| DAD-19 | **[OBRIGATÓRIO]** | APIs paginadas são consumidas até o fim, com condição de parada explícita. Use geradores para não acumular todas as páginas em memória sem necessidade. |
| DAD-20 | **[RECOMENDADO]** | Respeite `Retry-After` e limites de taxa documentados pela fonte. |
| DAD-21 | **[OPCIONAL]** | A biblioteca `tenacity` vale a pena quando houver muitas políticas de retry. Para casos simples, um laço explícito e testável (exemplo na 5.9) basta. |

### 5.6 Memória e volume

| ID | Nível | Regra |
|---|---|---|
| DAD-22 | **[OBRIGATÓRIO]** | Não carregue a fonte inteira em memória sem estimar o volume. Leia em fluxo (geradores, `chunksize`, cursores server-side, leitura lazy) quando o volume puder crescer. |
| DAD-23 | **[RECOMENDADO]** | Processe e grave em lotes de tamanho configurável. |
| DAD-24 | **[RECOMENDADO]** | Selecione só as colunas necessárias e filtre na fonte (predicate pushdown, `WHERE` no banco) em vez de filtrar em Python. |
| DAD-25 | **[RECOMENDADO]** | Prefira formatos colunares (Parquet) para dados analíticos intermediários e de saída. |

### 5.7 Transações e consistência

**[OBRIGATÓRIO] DAD-26** — A escrita que substitui ou atualiza um conjunto de dados acontece em uma única transação quando o destino permite. Em destinos sem transação (object storage), escreva em um caminho temporário e publique por troca atômica ou por um marcador de sucesso (`_SUCCESS`, manifesto).

**[OBRIGATÓRIO] DAD-27** — Leitores do destino nunca podem ver um estado parcial (metade da partição escrita).

### 5.8 Seleção de ferramentas de processamento e orquestração

**Não há framework obrigatório.** Escolha pelos critérios abaixo e registre a decisão em `docs/architecture.md`.

| Critério | Biblioteca padrão / SQL | pandas | Polars / DuckDB | Spark (PySpark) | dbt |
|---|---|---|---|---|---|
| Volume típico | Pequeno, fluxo registro a registro | Cabe com folga na memória | Até dezenas/centenas de GB em um nó (lazy/streaming) | Distribuído, além de um nó | Executado no warehouse |
| Melhor uso | Integrações, validação, regras de negócio | Análise e transformação tabular moderada | Transformação tabular eficiente em um nó | Grandes volumes e clusters já existentes | Modelagem SQL dentro do warehouse |
| Custo operacional | Mínimo | Baixo | Baixo | Alto (cluster, tuning) | Médio (projeto dbt, warehouse) |
| Dependências | Nenhuma | Média | Média | Alta | Média |

| Necessidade de orquestração | Opção adequada |
|---|---|
| Uma etapa, agenda simples | Agendador da plataforma (cron, job agendado da nuvem, CI agendado) |
| Vários passos com dependências, retries e backfill | Orquestrador já adotado pela empresa (Airflow, Dagster, Prefect, etc.) |

**[OBRIGATÓRIO] DAD-28** — A lógica de negócio não depende do orquestrador. Uma task do orquestrador só chama uma função do pacote (ex.: `executar_pipeline_vendas`) com parâmetros explícitos, o que permite testar e executar o pipeline localmente sem o orquestrador.

**[RECOMENDADO] DAD-29** — Isole SDKs de provedores (S3, GCS, Azure Blob, BigQuery, etc.) em `integrations/` ou `repositories/`, atrás de um `Protocol`, quando houver chance real de troca ou quando isso facilitar os testes.

### 5.9 Exemplo completo de pipeline modular

#### `src/meu_projeto/domain/vendas.py`

```python
"""Entidades de domínio de vendas."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class StatusVenda(StrEnum):
    """Status possíveis de uma venda na origem."""

    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"


@dataclass(frozen=True, slots=True)
class Venda:
    """Venda validada conforme o contrato de entrada."""

    id_venda: str
    id_loja: str
    data_venda: date
    valor_bruto: Decimal
    desconto: Decimal
    status: StatusVenda

    @property
    def valor_liquido(self) -> Decimal:
        """Valor da venda após o desconto."""
        return self.valor_bruto - self.desconto


@dataclass(frozen=True, slots=True)
class ResumoDiario:
    """Total de vendas confirmadas de uma loja em um dia."""

    id_loja: str
    data: date
    quantidade: int
    valor_total: Decimal
```

#### `src/meu_projeto/domain/validacao.py`

```python
"""Validação do contrato de entrada de vendas."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from meu_projeto.domain.vendas import StatusVenda, Venda

CAMPOS_OBRIGATORIOS = frozenset({"id_venda", "id_loja", "data_venda", "valor_bruto", "status"})


class ContratoInvalidoError(ValueError):
    """Registro não atende ao contrato de entrada."""


@dataclass(frozen=True, slots=True)
class RegistroRejeitado:
    """Registro de entrada recusado e o motivo da recusa."""

    registro: Mapping[str, object]
    motivo: str


@dataclass(frozen=True, slots=True)
class ResultadoValidacao:
    """Separação entre vendas válidas e registros rejeitados."""

    validas: tuple[Venda, ...]
    rejeitados: tuple[RegistroRejeitado, ...]


def converter_venda(registro: Mapping[str, object]) -> Venda:
    """Converte um registro bruto em ``Venda``.

    Raises:
        ContratoInvalidoError: Se faltarem campos ou houver valores inválidos.
    """
    faltantes = CAMPOS_OBRIGATORIOS - registro.keys()
    if faltantes:
        raise ContratoInvalidoError(f"campos ausentes: {sorted(faltantes)}")
    try:
        valor_bruto = Decimal(str(registro["valor_bruto"]))
        desconto = Decimal(str(registro.get("desconto", "0")))
        data_venda = date.fromisoformat(str(registro["data_venda"]))
        status = StatusVenda(str(registro["status"]))
    except (InvalidOperation, ValueError) as exc:
        raise ContratoInvalidoError(f"valor inválido: {exc}") from exc
    if not (valor_bruto.is_finite() and desconto.is_finite()):
        raise ContratoInvalidoError("valores monetários devem ser finitos")
    if valor_bruto < 0 or desconto < 0 or desconto > valor_bruto:
        raise ContratoInvalidoError("valores monetários inconsistentes")
    return Venda(
        id_venda=str(registro["id_venda"]),
        id_loja=str(registro["id_loja"]),
        data_venda=data_venda,
        valor_bruto=valor_bruto,
        desconto=desconto,
        status=status,
    )


def validar_vendas(registros: Iterable[Mapping[str, object]]) -> ResultadoValidacao:
    """Valida registros brutos, separando vendas válidas de rejeitadas."""
    validas: list[Venda] = []
    rejeitados: list[RegistroRejeitado] = []
    for registro in registros:
        try:
            validas.append(converter_venda(registro))
        except ContratoInvalidoError as exc:
            rejeitados.append(RegistroRejeitado(registro=registro, motivo=str(exc)))
    return ResultadoValidacao(validas=tuple(validas), rejeitados=tuple(rejeitados))
```

#### `src/meu_projeto/transformations/vendas.py`

```python
"""Transformações puras sobre vendas."""

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from meu_projeto.domain.vendas import ResumoDiario, StatusVenda, Venda


def consolidar_por_loja_e_dia(vendas: Iterable[Venda]) -> list[ResumoDiario]:
    """Consolida vendas confirmadas por loja e data, ordenadas por loja e data."""
    totais: dict[tuple[str, date], Decimal] = defaultdict(Decimal)
    quantidades: Counter[tuple[str, date]] = Counter()
    for venda in vendas:
        if venda.status is not StatusVenda.CONFIRMADA:
            continue
        chave = (venda.id_loja, venda.data_venda)
        totais[chave] += venda.valor_liquido
        quantidades[chave] += 1
    return [
        ResumoDiario(id_loja=loja, data=dia, quantidade=quantidades[(loja, dia)], valor_total=total)
        for (loja, dia), total in sorted(totais.items())
    ]
```

#### `src/meu_projeto/pipelines/vendas.py`

```python
"""Orquestração do pipeline diário de vendas."""

import logging
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from meu_projeto.domain.validacao import RegistroRejeitado, validar_vendas
from meu_projeto.domain.vendas import ResumoDiario
from meu_projeto.transformations.vendas import consolidar_por_loja_e_dia

logger = logging.getLogger(__name__)


class FonteVendas(Protocol):
    """Origem de registros brutos de vendas."""

    def ler(self, data_referencia: date) -> Iterable[Mapping[str, object]]:
        """Retorna os registros brutos da data informada."""
        ...


class DestinoResumo(Protocol):
    """Destino dos resumos diários consolidados."""

    def substituir_particao(self, data_referencia: date, resumos: Sequence[ResumoDiario]) -> None:
        """Substitui de forma idempotente os resumos da data informada."""
        ...


class DestinoRejeitados(Protocol):
    """Destino de quarentena para registros rejeitados."""

    def registrar(self, data_referencia: date, rejeitados: Sequence[RegistroRejeitado]) -> None:
        """Persiste os registros rejeitados da data informada."""
        ...


class TaxaRejeicaoExcedidaError(RuntimeError):
    """A proporção de registros rejeitados ultrapassou o limite permitido."""


@dataclass(frozen=True, slots=True)
class ResultadoExecucao:
    """Métricas de uma execução do pipeline."""

    lidos: int
    validos: int
    rejeitados: int
    resumos_gravados: int


def executar_pipeline_vendas(
    data_referencia: date,
    fonte: FonteVendas,
    destino: DestinoResumo,
    quarentena: DestinoRejeitados,
    limite_taxa_rejeicao: float = 0.05,
) -> ResultadoExecucao:
    """Executa extração, validação, consolidação e carga de vendas de uma data.

    Raises:
        TaxaRejeicaoExcedidaError: Se a taxa de rejeição superar o limite.
    """
    inicio = time.perf_counter()
    contexto = {"pipeline": "vendas", "data_referencia": data_referencia.isoformat()}
    logger.info("pipeline iniciado", extra=contexto)

    registros = list(fonte.ler(data_referencia))
    validacao = validar_vendas(registros)

    if validacao.rejeitados:
        quarentena.registrar(data_referencia, validacao.rejeitados)

    taxa_rejeicao = len(validacao.rejeitados) / len(registros) if registros else 0.0
    if taxa_rejeicao > limite_taxa_rejeicao:
        raise TaxaRejeicaoExcedidaError(
            f"taxa de rejeição {taxa_rejeicao:.1%} acima do limite {limite_taxa_rejeicao:.1%}"
        )

    resumos = consolidar_por_loja_e_dia(validacao.validas)
    destino.substituir_particao(data_referencia, resumos)

    resultado = ResultadoExecucao(
        lidos=len(registros),
        validos=len(validacao.validas),
        rejeitados=len(validacao.rejeitados),
        resumos_gravados=len(resumos),
    )
    logger.info(
        "pipeline concluído",
        extra={
            **contexto,
            "lidos": resultado.lidos,
            "validos": resultado.validos,
            "rejeitados": resultado.rejeitados,
            "resumos_gravados": resultado.resumos_gravados,
            "duracao_s": round(time.perf_counter() - inicio, 3),
        },
    )
    return resultado
```

> Este exemplo materializa os registros de um dia em memória (`list(...)`), o que serve para volumes diários moderados. Para volumes maiores, aplique a seção 5.6: valide e grave em lotes e acumule só os contadores.

#### `src/meu_projeto/integrations/api_vendas.py`

```python
"""Cliente da API de vendas com paginação e retry para falhas transitórias."""

import logging
import time
from collections.abc import Callable, Iterator, Mapping
from datetime import date

import httpx

logger = logging.getLogger(__name__)

STATUS_TRANSITORIOS = frozenset({429, 502, 503, 504})


class IntegracaoIndisponivelError(RuntimeError):
    """A integração permaneceu indisponível após todas as tentativas."""


class ClienteVendasApi:
    """Lê vendas paginadas da API de vendas.

    O ``httpx.Client`` é injetado já configurado com ``base_url``, autenticação
    e timeout. Quem cria o cliente é responsável por fechá-lo.
    """

    def __init__(
        self,
        cliente: httpx.Client,
        tamanho_pagina: int = 500,
        max_tentativas: int = 4,
        backoff_base_s: float = 1.0,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_tentativas < 1:
            raise ValueError("max_tentativas deve ser >= 1")
        self._cliente = cliente
        self._tamanho_pagina = tamanho_pagina
        self._max_tentativas = max_tentativas
        self._backoff_base_s = backoff_base_s
        self._dormir = dormir

    def ler(self, data_referencia: date) -> Iterator[Mapping[str, object]]:
        """Itera sobre todas as vendas da data, página a página."""
        pagina = 1
        while True:
            params = {
                "data": data_referencia.isoformat(),
                "pagina": pagina,
                "tamanho": self._tamanho_pagina,
            }
            corpo = self._get_com_retry("/vendas", params).json()
            yield from corpo["itens"]
            if not corpo.get("proxima_pagina"):
                return
            pagina += 1

    def _get_com_retry(self, caminho: str, params: Mapping[str, str | int]) -> httpx.Response:
        ultimo_erro: Exception | None = None
        for tentativa in range(1, self._max_tentativas + 1):
            try:
                resposta = self._cliente.get(caminho, params=params)
            except httpx.TransportError as exc:  # timeout, conexão recusada, DNS
                ultimo_erro = exc
            else:
                if resposta.status_code not in STATUS_TRANSITORIOS:
                    resposta.raise_for_status()  # erros 4xx definitivos não são repetidos
                    return resposta
                ultimo_erro = httpx.HTTPStatusError(
                    f"status transitório {resposta.status_code}",
                    request=resposta.request,
                    response=resposta,
                )
            if tentativa < self._max_tentativas:
                espera_s = self._backoff_base_s * 2 ** (tentativa - 1)
                logger.warning(
                    "falha transitória na API de vendas; nova tentativa agendada",
                    extra={
                        "tentativa": tentativa,
                        "erro": type(ultimo_erro).__name__,
                        "espera_s": espera_s,
                    },
                )
                self._dormir(espera_s)
        raise IntegracaoIndisponivelError(
            f"API de vendas indisponível após {self._max_tentativas} tentativas"
        ) from ultimo_erro
```

#### `src/meu_projeto/repositories/resumo_sqlite.py`

```python
"""Persistência idempotente de resumos diários em SQLite."""

import sqlite3
from collections.abc import Sequence
from datetime import date

from meu_projeto.domain.vendas import ResumoDiario


class RepositorioResumoSqlite:
    """Grava resumos diários substituindo a partição da data em uma transação."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._conexao = conexao

    def criar_tabela(self) -> None:
        """Cria a tabela de resumos, se ainda não existir."""
        with self._conexao:
            self._conexao.execute(
                """
                CREATE TABLE IF NOT EXISTS resumo_vendas_diario (
                    id_loja TEXT NOT NULL,
                    data TEXT NOT NULL,
                    quantidade INTEGER NOT NULL,
                    valor_total TEXT NOT NULL,
                    PRIMARY KEY (id_loja, data)
                )
                """
            )

    def substituir_particao(self, data_referencia: date, resumos: Sequence[ResumoDiario]) -> None:
        """Substitui todos os resumos da data em uma única transação."""
        with self._conexao:  # commit no sucesso, rollback em exceção
            self._conexao.execute(
                "DELETE FROM resumo_vendas_diario WHERE data = ?",
                (data_referencia.isoformat(),),
            )
            self._conexao.executemany(
                "INSERT INTO resumo_vendas_diario (id_loja, data, quantidade, valor_total) "
                "VALUES (?, ?, ?, ?)",
                [
                    (r.id_loja, r.data.isoformat(), r.quantidade, str(r.valor_total))
                    for r in resumos
                ],
            )
```

> SQL sempre com parâmetros (`?`, `%s`, `:nome`), nunca com f-string ou concatenação de valores (o Ruff `S608` sinaliza).

#### `src/meu_projeto/repositories/quarentena_sqlite.py`

```python
"""Persistência de registros rejeitados (quarentena) em SQLite."""

import json
import sqlite3
from collections.abc import Sequence
from datetime import date

from meu_projeto.domain.validacao import RegistroRejeitado


class RepositorioQuarentenaSqlite:
    """Grava registros rejeitados com motivo, substituindo os da mesma data."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._conexao = conexao
        with self._conexao:
            self._conexao.execute(
                "CREATE TABLE IF NOT EXISTS quarentena_vendas "
                "(data TEXT NOT NULL, registro TEXT NOT NULL, motivo TEXT NOT NULL)"
            )

    def registrar(self, data_referencia: date, rejeitados: Sequence[RegistroRejeitado]) -> None:
        """Substitui os rejeitados da data, mantendo a quarentena idempotente."""
        with self._conexao:
            self._conexao.execute(
                "DELETE FROM quarentena_vendas WHERE data = ?", (data_referencia.isoformat(),)
            )
            self._conexao.executemany(
                "INSERT INTO quarentena_vendas (data, registro, motivo) VALUES (?, ?, ?)",
                [
                    (
                        data_referencia.isoformat(),
                        json.dumps(dict(r.registro), ensure_ascii=False, default=str),
                        r.motivo,
                    )
                    for r in rejeitados
                ],
            )
```

> Se os registros da fonte trouxerem dados pessoais, mascare-os antes de gravar na quarentena (seção 9).

#### `src/meu_projeto/cli.py`

```python
"""Ponto de entrada de linha de comando do projeto."""

import argparse
import logging
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from datetime import date

import httpx

from meu_projeto.config.settings import carregar_configuracao
from meu_projeto.integrations.api_vendas import ClienteVendasApi
from meu_projeto.observability.logging import configurar_logging, definir_id_execucao
from meu_projeto.pipelines.vendas import executar_pipeline_vendas
from meu_projeto.repositories.quarentena_sqlite import RepositorioQuarentenaSqlite
from meu_projeto.repositories.resumo_sqlite import RepositorioResumoSqlite

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Executa o pipeline de vendas para a data de referência informada."""
    parser = argparse.ArgumentParser(prog="meu-projeto")
    parser.add_argument("--data-referencia", type=date.fromisoformat, required=True)
    args = parser.parse_args(argv)

    configuracao = carregar_configuracao()
    configurar_logging(configuracao.nivel_log)
    definir_id_execucao()

    try:
        with (
            httpx.Client(
                base_url=configuracao.api_base_url,
                headers={"Authorization": f"Bearer {configuracao.api_token}"},
                timeout=httpx.Timeout(30.0, connect=5.0),
            ) as cliente_http,
            closing(sqlite3.connect(configuracao.caminho_banco)) as conexao,
        ):
            destino = RepositorioResumoSqlite(conexao)
            destino.criar_tabela()
            executar_pipeline_vendas(
                data_referencia=args.data_referencia,
                fonte=ClienteVendasApi(cliente_http),
                destino=destino,
                quarentena=RepositorioQuarentenaSqlite(conexao),
                limite_taxa_rejeicao=configuracao.limite_taxa_rejeicao,
            )
    except Exception:
        # Único ponto onde a captura ampla é permitida: registra com stack trace e
        # devolve código de erro ao agendador/orquestrador.
        logger.exception("pipeline falhou", extra={"pipeline": "vendas"})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Execução local: `poetry run python -m meu_projeto.cli --data-referencia 2026-10-12` ou, com o script declarado em `[project.scripts]`, `poetry run meu-projeto --data-referencia 2026-10-12`.

---

## 6. Ruff: lint, formatação e imports

### 6.1 Regras

| ID | Nível | Regra |
|---|---|---|
| RUF-01 | **[OBRIGATÓRIO]** | O Ruff é a única ferramenta de lint, formatação e organização de imports. Não use Black, isort, Flake8 ou Pylint em paralelo. |
| RUF-02 | **[OBRIGATÓRIO]** | A configuração fica no `pyproject.toml` (seção 3.1). As regras `I` (imports) fazem parte do `select` oficial, para não depender de `--select I` na linha de comando. |
| RUF-03 | **[OBRIGATÓRIO]** | O código passa em `ruff check .` e `ruff format --check .` **antes** de ir para revisão. |
| RUF-04 | **[OBRIGATÓRIO]** | Prefira corrigir o problema. Supressões são pontuais (`# noqa: <código>`), sempre com o código da regra e uma justificativa na mesma linha. |
| RUF-05 | **[OBRIGATÓRIO]** | `# noqa` sem código, `# ruff: noqa` no arquivo inteiro e regras desativadas globalmente para esconder problemas recorrentes são proibidos. Para mudar o `select`/`ignore` do projeto, abra um PR com justificativa. |
| RUF-06 | **[OBRIGATÓRIO]** | Toda exclusão de diretório (`extend-exclude`) e todo `per-file-ignores` tem um comentário com o motivo. |
| RUF-07 | **[RECOMENDADO]** | Configure o editor para formatar ao salvar com o Ruff do ambiente do projeto (`.venv`). |

### 6.2 Comandos

```bash
# Verificar problemas de lint (inclui imports, pois "I" está no select)
poetry run ruff check .

# Corrigir automaticamente apenas correções seguras
poetry run ruff check . --fix

# Formatar o código
poetry run ruff format .

# Verificar formatação sem modificar arquivos (usado na CI)
poetry run ruff format --check .

# Verificar só a organização de imports (diagnóstico pontual)
poetry run ruff check . --select I

# Corrigir só a organização de imports
poetry run ruff check . --select I --fix

# Entender uma regra
poetry run ruff rule B006
```

> O `ruff format` **não** reordena imports. A ordenação é feita pelas regras `I` no `ruff check --fix`. Por isso, o fluxo local é `ruff check . --fix` seguido de `ruff format .`.

> **Correções inseguras:** `--unsafe-fixes` pode mudar o comportamento do código. Só use com revisão manual do diff, nunca na CI.

### 6.3 Racional das regras selecionadas

| Grupo | Por que está habilitado |
|---|---|
| `E`, `W`, `F` | Base: erros de sintaxe, nomes indefinidos, imports e variáveis não usados |
| `I` | Ordem e agrupamento de imports determinísticos |
| `N` | Convenções de nome da PEP 8 (inclui `N818`: exceções terminam em `Error`) |
| `D` (google) | Docstrings em módulos, classes e funções públicas |
| `UP` | Sintaxe moderna para Python 3.12 |
| `B` | Bugs comuns (argumentos padrão mutáveis, `except` mal formado) |
| `C4`, `SIM` | Simplificações que melhoram a legibilidade |
| `PTH` | Força `pathlib` |
| `DTZ` | Datetimes com timezone, essencial em dados |
| `T20` | Proíbe `print` em produção |
| `BLE` | Proíbe `except Exception` cego (permitido quando há `logger.exception` ou `raise`) |
| `S` | Problemas de segurança (SQL por concatenação, `subprocess` com shell, `pickle`, `yaml.load`) |
| `LOG`, `G` | Uso correto do `logging` (sem f-string na mensagem, sem `logging.warn`) |
| `PT` | Estilo consistente no pytest |
| `TID` | Proíbe imports relativos (`ban-relative-imports = "all"`) |
| `RUF` | Regras próprias do Ruff (ex.: `noqa` sem uso) |

Ficaram de fora por gerar ruído desproporcional para o time: `ANN` (os tipos são cobrados na revisão e, opcionalmente, por mypy), `ERA` (falsos positivos em comentários explicativos), `PL` e `TRY` (muitas regras opinativas). Um projeto pode habilitá-los com aprovação do time.

### 6.4 Supressão pontual

```python
# Correto: código específico + justificativa
resultado = subprocess.run(  # noqa: S603 - argumentos fixos, sem entrada do usuário
    ["/usr/bin/gzip", "-t", str(caminho)], check=True, capture_output=True
)

# Incorreto: suprime tudo, sem motivo
resultado = subprocess.run(comando, shell=True)  # noqa
```

---

## 7. Pytest e cobertura mínima

### 7.1 Regras

| ID | Nível | Regra |
|---|---|---|
| TST-01 | **[OBRIGATÓRIO]** | Todos os projetos usam Pytest. |
| TST-02 | **[OBRIGATÓRIO]** | A cobertura mínima dos testes unitários sobre o código de produção (`src/meu_projeto`) é **50%**, medida por `pytest-cov` com branch coverage. A execução falha abaixo desse piso. |
| TST-03 | **[OBRIGATÓRIO]** | A medição cobre só o pacote de produção (`source`/`--cov=meu_projeto`), nunca `tests/`, `scripts/` ou arquivos gerados. |
| TST-04 | **[OBRIGATÓRIO]** | Testes unitários são rápidos, isolados e determinísticos. Não acessam rede, banco real, storage real nem relógio real e não dependem da ordem de execução. |
| TST-05 | **[OBRIGATÓRIO]** | Testes de integração ficam em `tests/integration/`, são marcados com `@pytest.mark.integration` e rodam em uma etapa própria. Eles **não substituem** os unitários nem contam para o piso de cobertura. |
| TST-06 | **[OBRIGATÓRIO]** | Todo bug corrigido ganha um teste que reproduz o problema. |
| TST-07 | **[OBRIGATÓRIO]** | Código novo ou alterado em `domain/`, `transformations/` e `pipelines/` tem testes cobrindo sucesso, entradas inválidas, limites e falhas esperadas. |
| TST-08 | **[RECOMENDADO]** | Aumente a cobertura aos poucos nos módulos críticos. Percentuais acima de 50% só se tornam obrigatórios com aprovação do time. |
| TST-09 | **[OBRIGATÓRIO]** | Cobertura não substitui qualidade. Testes sem `assert` relevante ou que só executam código para "subir a métrica" são rejeitados na revisão. |

### 7.2 Comandos

```bash
# Executar testes unitários
poetry run pytest tests/unit

# Testes unitários com cobertura (comando oficial, idêntico ao da CI)
poetry run pytest tests/unit \
  --cov=meu_projeto \
  --cov-report=term-missing \
  --cov-fail-under=50

# Relatório HTML de cobertura (gera htmlcov/, que não é versionado)
poetry run pytest tests/unit \
  --cov=meu_projeto \
  --cov-report=html \
  --cov-fail-under=50

# Testes de integração (etapa própria, sem piso de cobertura)
poetry run pytest tests/integration -m integration

# Um teste específico, com saída detalhada
poetry run pytest tests/unit/transformations/test_vendas.py -k loja -vv
```

`--cov-fail-under=50` repete o valor de `fail_under` do `pyproject.toml`. Os dois precisam ser sempre iguais. Se o piso mudar, altere ambos no mesmo PR.

### 7.3 Organização

```text
tests/
├── conftest.py                      # fixtures compartilhadas
├── fixtures/
│   └── vendas_validas.json          # massas de dados pequenas e anonimizadas
├── unit/                            # espelha src/meu_projeto/
│   ├── domain/
│   │   └── test_validacao.py
│   ├── transformations/
│   │   └── test_vendas.py
│   ├── integrations/
│   │   └── test_api_vendas.py
│   └── pipelines/
│       └── test_vendas.py
└── integration/
    └── repositories/
        └── test_resumo_sqlite.py
```

| ID | Nível | Regra |
|---|---|---|
| TST-10 | **[OBRIGATÓRIO]** | A estrutura de `tests/unit/` espelha a de `src/meu_projeto/`. |
| TST-11 | **[OBRIGATÓRIO]** | O nome do teste descreve cenário e resultado: `test_<unidade>_<cenario>_<resultado_esperado>`. |
| TST-12 | **[RECOMENDADO]** | Siga Arrange / Act / Assert, com um comportamento por teste. |
| TST-13 | **[RECOMENDADO]** | Fixtures com o menor escopo suficiente (`function` por padrão). `session` só para recursos caros e imutáveis. |
| TST-14 | **[RECOMENDADO]** | Use `@pytest.mark.parametrize` para variações do mesmo comportamento, em vez de copiar testes. |
| TST-15 | **[OBRIGATÓRIO]** | Dados de fixtures são sintéticos ou anonimizados. Dados pessoais reais em `tests/` são proibidos. |
| TST-16 | **[RECOMENDADO]** | Prefira **fakes** (implementações simples em memória de um `Protocol`) a mocks profundos. Use `unittest.mock`/`monkeypatch` para fronteiras pontuais. Não faça asserts sobre detalhes internos (ordem de chamadas privadas). |
| TST-17 | **[OBRIGATÓRIO]** | Relógio, aleatoriedade e `sleep` são injetados ou controlados nos testes, sem espera real. |

### 7.4 Exemplos

#### `tests/conftest.py`

```python
from datetime import date
from decimal import Decimal

import pytest

from meu_projeto.domain.vendas import StatusVenda, Venda


@pytest.fixture
def fabrica_venda():
    """Cria vendas válidas com valores padrão sobrescrevíveis."""

    def _criar(**sobrescritas: object) -> Venda:
        campos: dict[str, object] = {
            "id_venda": "v-1",
            "id_loja": "loja-1",
            "data_venda": date(2026, 10, 12),
            "valor_bruto": Decimal("100.00"),
            "desconto": Decimal("0"),
            "status": StatusVenda.CONFIRMADA,
        }
        campos.update(sobrescritas)
        return Venda(**campos)

    return _criar
```

#### Transformação de dados: `tests/unit/transformations/test_vendas.py`

```python
from datetime import date
from decimal import Decimal

from meu_projeto.domain.vendas import ResumoDiario, StatusVenda
from meu_projeto.transformations.vendas import consolidar_por_loja_e_dia


def test_consolidar_soma_valor_liquido_por_loja_e_dia(fabrica_venda):
    vendas = [
        fabrica_venda(id_venda="1", valor_bruto=Decimal("100"), desconto=Decimal("10")),
        fabrica_venda(id_venda="2", valor_bruto=Decimal("50")),
        fabrica_venda(id_venda="3", id_loja="loja-2", valor_bruto=Decimal("30")),
    ]

    resumos = consolidar_por_loja_e_dia(vendas)

    assert resumos == [
        ResumoDiario("loja-1", date(2026, 10, 12), quantidade=2, valor_total=Decimal("140")),
        ResumoDiario("loja-2", date(2026, 10, 12), quantidade=1, valor_total=Decimal("30")),
    ]


def test_consolidar_ignora_vendas_canceladas(fabrica_venda):
    vendas = [fabrica_venda(status=StatusVenda.CANCELADA)]

    assert consolidar_por_loja_e_dia(vendas) == []


def test_consolidar_entrada_vazia_retorna_lista_vazia():
    assert consolidar_por_loja_e_dia([]) == []
```

#### Validação e contratos: `tests/unit/domain/test_validacao.py`

```python
from decimal import Decimal

import pytest

from meu_projeto.domain.validacao import (
    ContratoInvalidoError,
    converter_venda,
    validar_vendas,
)

REGISTRO_VALIDO = {
    "id_venda": "v-1",
    "id_loja": "loja-1",
    "data_venda": "2026-10-12",
    "valor_bruto": "100.00",
    "desconto": "5.00",
    "status": "confirmada",
}


def test_converter_venda_registro_valido_retorna_venda():
    venda = converter_venda(REGISTRO_VALIDO)

    assert venda.valor_liquido == Decimal("95.00")


@pytest.mark.parametrize(
    ("sobrescrita", "mensagem"),
    [
        ({"valor_bruto": "abc"}, "valor inválido"),
        ({"data_venda": "12/10/2026"}, "valor inválido"),
        ({"status": "pendente"}, "valor inválido"),
        ({"valor_bruto": "-1"}, "inconsistentes"),
        ({"desconto": "200"}, "inconsistentes"),
        ({"valor_bruto": "NaN"}, "finitos"),
    ],
)
def test_converter_venda_valores_invalidos_lanca_erro(sobrescrita, mensagem):
    with pytest.raises(ContratoInvalidoError, match=mensagem):
        converter_venda({**REGISTRO_VALIDO, **sobrescrita})


def test_converter_venda_campo_ausente_informa_campo():
    registro = {k: v for k, v in REGISTRO_VALIDO.items() if k != "id_loja"}

    with pytest.raises(ContratoInvalidoError, match="id_loja"):
        converter_venda(registro)


def test_validar_vendas_separa_validas_e_rejeitadas():
    resultado = validar_vendas([REGISTRO_VALIDO, {**REGISTRO_VALIDO, "valor_bruto": "x"}])

    assert len(resultado.validas) == 1
    assert len(resultado.rejeitados) == 1
    assert "valor inválido" in resultado.rejeitados[0].motivo
```

#### Regra de negócio e falha esperada: `tests/unit/pipelines/test_vendas.py`

```python
from datetime import date

import pytest

from meu_projeto.pipelines.vendas import TaxaRejeicaoExcedidaError, executar_pipeline_vendas

DATA = date(2026, 10, 12)
VALIDO = {
    "id_venda": "v-1",
    "id_loja": "loja-1",
    "data_venda": "2026-10-12",
    "valor_bruto": "10",
    "status": "confirmada",
}
INVALIDO = {"id_venda": "v-2"}


class FonteFake:
    def __init__(self, registros):
        self.registros = registros

    def ler(self, data_referencia):
        return self.registros


class DestinoFake:
    def __init__(self):
        self.particoes = {}

    def substituir_particao(self, data_referencia, resumos):
        self.particoes[data_referencia] = list(resumos)


class QuarentenaFake:
    def __init__(self):
        self.rejeitados = []

    def registrar(self, data_referencia, rejeitados):
        self.rejeitados.extend(rejeitados)


def test_pipeline_grava_resumo_e_envia_rejeitados_para_quarentena():
    destino, quarentena = DestinoFake(), QuarentenaFake()

    resultado = executar_pipeline_vendas(
        DATA, FonteFake([VALIDO, INVALIDO]), destino, quarentena, limite_taxa_rejeicao=0.5
    )

    assert resultado.lidos == 2
    assert resultado.rejeitados == 1
    assert len(destino.particoes[DATA]) == 1
    assert len(quarentena.rejeitados) == 1


def test_pipeline_reexecucao_produz_mesmo_estado():
    destino = DestinoFake()
    fonte = FonteFake([VALIDO])

    executar_pipeline_vendas(DATA, fonte, destino, QuarentenaFake())
    primeira = list(destino.particoes[DATA])
    executar_pipeline_vendas(DATA, fonte, destino, QuarentenaFake())

    assert destino.particoes[DATA] == primeira


def test_pipeline_taxa_rejeicao_acima_do_limite_interrompe_sem_gravar():
    destino, quarentena = DestinoFake(), QuarentenaFake()

    with pytest.raises(TaxaRejeicaoExcedidaError):
        executar_pipeline_vendas(DATA, FonteFake([VALIDO, INVALIDO]), destino, quarentena)

    assert destino.particoes == {}
    assert len(quarentena.rejeitados) == 1  # rejeitados preservados para diagnóstico
```

#### Integração externa simulada: `tests/unit/integrations/test_api_vendas.py`

```python
from datetime import date

import httpx
import pytest

from meu_projeto.integrations.api_vendas import ClienteVendasApi, IntegracaoIndisponivelError


def _cliente(handler) -> httpx.Client:
    return httpx.Client(base_url="https://api.exemplo", transport=httpx.MockTransport(handler))


def test_ler_percorre_todas_as_paginas():
    def handler(request: httpx.Request) -> httpx.Response:
        pagina = int(request.url.params["pagina"])
        return httpx.Response(200, json={"itens": [{"id": pagina}], "proxima_pagina": pagina < 3})

    with _cliente(handler) as http:
        itens = list(ClienteVendasApi(http).ler(date(2026, 10, 12)))

    assert [item["id"] for item in itens] == [1, 2, 3]


def test_ler_repete_falha_transitoria_com_backoff():
    respostas = iter([httpx.Response(503), httpx.Response(200, json={"itens": []})])
    esperas: list[float] = []

    with _cliente(lambda request: next(respostas)) as http:
        api = ClienteVendasApi(http, backoff_base_s=2.0, dormir=esperas.append)
        assert list(api.ler(date(2026, 10, 12))) == []

    assert esperas == [2.0]


def test_ler_esgota_tentativas_e_preserva_causa():
    with _cliente(lambda request: httpx.Response(503)) as http:
        api = ClienteVendasApi(http, max_tentativas=3, dormir=lambda _: None)
        with pytest.raises(IntegracaoIndisponivelError) as erro:
            list(api.ler(date(2026, 10, 12)))

    assert isinstance(erro.value.__cause__, httpx.HTTPStatusError)


def test_ler_erro_definitivo_nao_repete():
    chamadas = []

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas.append(request)
        return httpx.Response(401)

    with _cliente(handler) as http, pytest.raises(httpx.HTTPStatusError):
        list(ClienteVendasApi(http, dormir=lambda _: None).ler(date(2026, 10, 12)))

    assert len(chamadas) == 1
```

#### Controle de relógio

```python
# Produção: o relógio é injetado
from collections.abc import Callable
from datetime import UTC, datetime


def nome_arquivo_execucao(agora: Callable[[], datetime] = lambda: datetime.now(UTC)) -> str:
    """Gera o nome do arquivo de saída a partir do instante da execução."""
    return f"vendas_{agora():%Y%m%dT%H%M%SZ}.parquet"


# Teste: relógio fixo, resultado determinístico
def test_nome_arquivo_execucao_usa_instante_utc():
    fixo = datetime(2026, 10, 12, 3, 0, tzinfo=UTC)

    assert nome_arquivo_execucao(lambda: fixo) == "vendas_20261012T030000Z.parquet"
```

#### Teste de integração: `tests/integration/repositories/test_resumo_sqlite.py`

```python
import sqlite3
from contextlib import closing
from datetime import date
from decimal import Decimal

import pytest

from meu_projeto.domain.vendas import ResumoDiario
from meu_projeto.repositories.resumo_sqlite import RepositorioResumoSqlite

pytestmark = pytest.mark.integration

DATA = date(2026, 10, 12)


def test_substituir_particao_e_idempotente(tmp_path):
    with closing(sqlite3.connect(tmp_path / "teste.db")) as conexao:
        repositorio = RepositorioResumoSqlite(conexao)
        repositorio.criar_tabela()
        resumo = ResumoDiario("loja-1", DATA, quantidade=1, valor_total=Decimal("10"))

        repositorio.substituir_particao(DATA, [resumo])
        repositorio.substituir_particao(DATA, [resumo])

        total = conexao.execute("SELECT COUNT(*) FROM resumo_vendas_diario").fetchone()[0]

    assert total == 1
```

---

## 8. Documentação com MkDocs Material

### 8.1 Regras

| ID | Nível | Regra |
|---|---|---|
| DOC-01 | **[OBRIGATÓRIO]** | A documentação oficial é construída com MkDocs e o tema Material for MkDocs, fica em `docs/` e é configurada em `mkdocs.yml`. |
| DOC-02 | **[OBRIGATÓRIO]** | A documentação faz parte do produto. Um PR que muda comportamento, configuração, variáveis de ambiente, contrato de dados ou forma de execução atualiza a documentação no **mesmo PR**. |
| DOC-03 | **[OBRIGATÓRIO]** | `mkdocs build --strict` passa localmente e na CI. |
| DOC-04 | **[OBRIGATÓRIO]** | A navegação é explícita em `nav`. Toda página em `docs/` aparece no `nav` ou está listada em `not_in_nav`. |
| DOC-05 | **[RECOMENDADO]** | Não duplique o que pode ser gerado: a referência de API vem das docstrings (`mkdocstrings`) quando o projeto expõe uma API Python usada por outros. Comandos e exemplos de configuração apontam para o `pyproject.toml` em vez de copiar trechos longos. |
| DOC-06 | **[RECOMENDADO]** | Páginas curtas e objetivas, com exemplos executáveis. Texto que descreve um comportamento inexistente é tratado como bug. |
| DOC-07 | **[OBRIGATÓRIO]** | Links internos são relativos e apontam para arquivos `.md` (ex.: `[Arquitetura](architecture.md)`), para que o modo estrito consiga validá-los. Imagens ficam em `docs/assets/`, com texto alternativo. |
| DOC-08 | **[OBRIGATÓRIO]** | O `README.md` é curto: propósito, como instalar, como rodar os testes e o link para a documentação completa. |

### 8.2 Conteúdo mínimo

| Página | Conteúdo |
|---|---|
| `docs/index.md` | Propósito, escopo, o que o projeto **não** faz, contatos |
| `docs/getting-started.md` | Pré-requisitos (Python, Poetry), instalação (`poetry install`), primeira execução |
| `docs/configuration.md` | Tabela com todas as variáveis de ambiente: nome, obrigatoriedade, padrão, exemplo e se é segredo |
| `docs/architecture.md` | Módulos, fluxo de dados, contratos de entrada e saída, decisões técnicas (ex.: escolha de engine) |
| `docs/development.md` | Fluxo local, comandos de qualidade, convenções, como adicionar dependências |
| `docs/testing.md` | Como rodar os testes unitários e de integração, cobertura, como escrever novos testes |
| `docs/operations.md` | Como executar em cada ambiente, parâmetros, reprocessamento, monitoramento, alertas |
| `docs/troubleshooting.md` | Erros conhecidos, sintomas, causas e solução |
| `docs/reference/` | Referência de API gerada (opcional) e exemplos de uso |

### 8.3 Dependências e comandos

```bash
# Adicionar MkDocs e o tema Material ao grupo de desenvolvimento
poetry add --group dev mkdocs mkdocs-material

# (Opcional) referência de API a partir das docstrings
poetry add --group dev "mkdocstrings[python]"

# Executar a documentação localmente (http://127.0.0.1:8000)
poetry run mkdocs serve

# Gerar o site estático validando links e avisos (saída em site/, não versionada)
poetry run mkdocs build --strict
```

O `--strict` transforma avisos em erros: links para páginas inexistentes, páginas fora do `nav`, âncoras inválidas e configuração inválida, conforme as regras de `validation` do `mkdocs.yml`. Use o `--strict` na linha de comando do build, e não `strict: true` no arquivo, para que o `mkdocs serve` continue tolerante durante a edição.

### 8.4 `mkdocs.yml` de referência (MkDocs 1.6, Material 9.6)

```yaml
site_name: Meu Projeto
site_description: Pipeline de ingestão e consolidação de vendas.
repo_url: https://git.example.com/engenharia-dados/meu-projeto
docs_dir: docs

theme:
  name: material
  language: pt-BR
  features:
    - navigation.sections
    - navigation.top
    - search.highlight
    - content.code.copy

nav:
  - Início: index.md
  - Primeiros passos: getting-started.md
  - Configuração: configuration.md
  - Arquitetura: architecture.md
  - Desenvolvimento: development.md
  - Testes e qualidade: testing.md
  - Operação: operations.md
  - Troubleshooting: troubleshooting.md
  - Referência:
      - Pipelines: reference/pipelines.md

markdown_extensions:
  - admonition
  - tables
  - toc:
      permalink: true
  - pymdownx.highlight
  - pymdownx.superfences
  - pymdownx.details

validation:
  omitted_files: warn
  absolute_links: warn
  unrecognized_links: warn
  anchors: warn

plugins:
  - search
  # Habilite somente se mkdocstrings[python] estiver no grupo dev:
  # - mkdocstrings:
  #     handlers:
  #       python:
  #         paths: [src]
  #         options:
  #           docstring_style: google
  #           show_source: false
```

Com `mkdocstrings` habilitado, uma página de referência contém só o identificador do módulo:

```markdown
# Pipelines

::: meu_projeto.pipelines.vendas
```

**[OBRIGATÓRIO] DOC-09** — Mudanças de versão major do MkDocs ou do Material são avaliadas em um PR específico, com build estrito aprovado. As faixas de versão ficam fixadas no grupo `dev`. A restrição `mkdocs = "^1.6"` mantém o MkDocs abaixo da 2.0: a equipe do Material for MkDocs avisa que a 2.0 remove o sistema de plugins e reescreve o de temas, sem caminho de migração. Esse aviso aparece no `mkdocs build` e pode ser ignorado enquanto a restrição estiver mantida. Uma migração exige decisão do time.

---

## 9. Segurança e gestão de configuração

### 9.1 Regras

| ID | Nível | Regra |
|---|---|---|
| SEG-01 | **[OBRIGATÓRIO]** | Nunca versione senhas, tokens, chaves privadas, strings de conexão com credencial, arquivos `.env` reais ou credenciais de nuvem. |
| SEG-02 | **[OBRIGATÓRIO]** | Em produção, segredos vêm do gerenciador de segredos da infraestrutura (cofre, secret manager da nuvem, secrets do orquestrador ou da plataforma de CI), injetados como variáveis de ambiente ou lidos em tempo de execução. |
| SEG-03 | **[OBRIGATÓRIO]** | A configuração é validada no início da execução. Uma variável obrigatória ausente ou inválida interrompe o processo antes de qualquer leitura ou escrita de dados, com uma mensagem que cita o **nome** da variável e nunca o valor. |
| SEG-04 | **[OBRIGATÓRIO]** | Segredos não aparecem em logs, exceções, `repr`, relatórios de teste nem na documentação. Use `field(repr=False)` em campos sensíveis. |
| SEG-05 | **[OBRIGATÓRIO]** | Dados pessoais (CPF, e-mail, telefone, endereço, nome) não são registrados em logs. Quando for preciso correlacionar, use identificadores técnicos ou valores mascarados ou hasheados. |
| SEG-06 | **[OBRIGATÓRIO]** | Dados de fontes externas são tratados como não confiáveis e validados antes do uso (seção 5.2). |
| SEG-07 | **[OBRIGATÓRIO]** | Sem desserialização insegura: `pickle`/`marshal` apenas com dados gerados pelo próprio sistema em local confiável, `yaml.safe_load` em vez de `yaml.load`, e nunca `eval`/`exec` com dados externos. |
| SEG-08 | **[OBRIGATÓRIO]** | Comandos externos usam `subprocess.run([...], check=True)` com lista de argumentos e `shell=False`. Entradas externas nunca são concatenadas em comandos ou SQL. |
| SEG-09 | **[OBRIGATÓRIO]** | Exceções e mensagens destinadas a consumidores externos (APIs, relatórios, e-mails) não expõem stack traces, caminhos internos, queries ou nomes de hosts. Esses detalhes ficam apenas nos logs internos. |
| SEG-10 | **[OBRIGATÓRIO]** | Os alertas de vulnerabilidade em dependências são analisados. Os críticos e altos são tratados com prioridade ou recebem uma justificativa documentada. |
| SEG-11 | **[RECOMENDADO]** | Ative a varredura de segredos no repositório (secret scanning da plataforma ou um hook de pre-commit) e na CI. |
| SEG-12 | **[RECOMENDADO]** | Use credenciais de menor privilégio por ambiente: o pipeline de desenvolvimento não acessa dados de produção. |

### 9.2 Desenvolvimento local e produção

| Aspecto | Desenvolvimento local | Produção |
|---|---|---|
| Origem dos valores | Variáveis exportadas no shell ou um `.env` local **não versionado** | Gerenciador de segredos e variáveis do runtime |
| Arquivo de exemplo | `.env.example` versionado, **só com nomes e valores fictícios** | Não se aplica |
| Credenciais | Pessoais ou de sandbox, com escopo mínimo | Contas de serviço dedicadas, com rotação |
| Dados | Sintéticos, amostras anonimizadas ou ambiente de homologação | Reais, com controles de acesso e auditoria |

`.env.example`:

```dotenv
MEU_PROJETO_AMBIENTE=dev
MEU_PROJETO_API_BASE_URL=https://api-sandbox.example.com
MEU_PROJETO_API_TOKEN=substitua-localmente
MEU_PROJETO_CAMINHO_BANCO=./dados/local.db
MEU_PROJETO_NIVEL_LOG=DEBUG
```

> Se o projeto ler `.env` automaticamente (ex.: com `python-dotenv` ou `pydantic-settings`), isso só pode acontecer no ambiente `dev`. Em produção, a fonte é sempre o runtime.

### 9.3 Exemplo: `src/meu_projeto/config/settings.py`

```python
"""Carregamento e validação da configuração a partir de variáveis de ambiente."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

PREFIXO = "MEU_PROJETO_"
OBRIGATORIAS = ("AMBIENTE", "API_BASE_URL", "API_TOKEN", "CAMINHO_BANCO")


class Ambiente(StrEnum):
    """Ambientes de execução suportados."""

    DEV = "dev"
    HML = "hml"
    PRD = "prd"


class ConfiguracaoInvalidaError(RuntimeError):
    """A configuração do ambiente está ausente ou inválida."""


@dataclass(frozen=True, slots=True)
class Configuracao:
    """Configuração imutável da aplicação."""

    ambiente: Ambiente
    api_base_url: str
    api_token: str = field(repr=False)
    caminho_banco: Path
    nivel_log: str = "INFO"
    limite_taxa_rejeicao: float = 0.05


def carregar_configuracao(env: Mapping[str, str] | None = None) -> Configuracao:
    """Lê e valida a configuração.

    Args:
        env: Variáveis de ambiente; usa ``os.environ`` quando omitido (útil para testes).

    Raises:
        ConfiguracaoInvalidaError: Se faltar variável obrigatória ou algum valor for inválido.
    """
    origem = os.environ if env is None else env
    faltantes = [PREFIXO + nome for nome in OBRIGATORIAS if not origem.get(PREFIXO + nome)]
    if faltantes:
        raise ConfiguracaoInvalidaError(f"variáveis obrigatórias ausentes: {', '.join(faltantes)}")
    try:
        ambiente = Ambiente(origem[PREFIXO + "AMBIENTE"])
        limite = float(origem.get(PREFIXO + "LIMITE_TAXA_REJEICAO", "0.05"))
    except ValueError as exc:
        raise ConfiguracaoInvalidaError(f"valor de configuração inválido: {exc}") from exc
    if not 0 <= limite <= 1:
        raise ConfiguracaoInvalidaError(f"{PREFIXO}LIMITE_TAXA_REJEICAO deve estar entre 0 e 1")
    return Configuracao(
        ambiente=ambiente,
        api_base_url=origem[PREFIXO + "API_BASE_URL"],
        api_token=origem[PREFIXO + "API_TOKEN"],
        caminho_banco=Path(origem[PREFIXO + "CAMINHO_BANCO"]),
        nivel_log=origem.get(PREFIXO + "NIVEL_LOG", "INFO").upper(),
        limite_taxa_rejeicao=limite,
    )
```

Os parâmetros por ambiente mudam **valores**, nunca o fluxo. Se o código tiver `if ambiente == "prd":` alterando lógica de negócio, isso é sinal de configuração mal modelada.

---

## 10. Logging, erros e observabilidade

### 10.1 Regras

| ID | Nível | Regra |
|---|---|---|
| LOG-01 | **[OBRIGATÓRIO]** | Use o módulo `logging` da biblioteca padrão, com `logger = logging.getLogger(__name__)` em cada módulo. `structlog` e outras bibliotecas estruturadas são **[OPCIONAL]** e precisam de aprovação do time. |
| LOG-02 | **[OBRIGATÓRIO]** | O logging é configurado **só no ponto de entrada** (CLI, task do orquestrador). Bibliotecas e módulos internos nunca chamam `logging.basicConfig` nem adicionam handlers. |
| LOG-03 | **[OBRIGATÓRIO]** | Registre o início, a conclusão (com duração e contagens de lidos, válidos, rejeitados e gravados) e as falhas de cada pipeline e de cada etapa relevante. |
| LOG-04 | **[OBRIGATÓRIO]** | Os logs incluem um identificador de execução (`id_execucao`) e contexto operacional (pipeline, data de referência, lote). Quando o orquestrador fornecer um ID de execução, use esse ID. |
| LOG-05 | **[OBRIGATÓRIO]** | As falhas são registradas com stack trace (`logger.exception(...)` dentro do `except`, ou `exc_info=True`). |
| LOG-06 | **[OBRIGATÓRIO]** | A mensagem de log é fixa. Dados variáveis vão em `extra={...}` ou em argumentos `%s`, nunca em f-strings (o Ruff `G004` detecta). |
| LOG-07 | **[OBRIGATÓRIO]** | Não registre log por registro dentro de laços de alto volume. Registre agregados por lote ou etapa, ou amostras limitadas. |
| LOG-08 | **[OBRIGATÓRIO]** | Não capture uma exceção só para registrá-la e seguir em frente. Ao capturar, é preciso **recuperar** (retry, rejeição documentada), **enriquecer** (relançar com contexto e `from exc`) ou **encerrar** (ponto de entrada). |
| LOG-09 | **[OBRIGATÓRIO]** | Níveis: `DEBUG` para diagnóstico detalhado (desligado em produção), `INFO` para marcos do fluxo, `WARNING` para situações anômalas recuperadas (retry, rejeições abaixo do limite), `ERROR`/`exception` para falhas que interrompem uma operação. |
| LOG-10 | **[RECOMENDADO]** | Em produção, use formato estruturado (JSON, uma linha por evento), para facilitar consulta e alertas na plataforma de observabilidade. |

### 10.2 Exemplo: `src/meu_projeto/observability/logging.py`

```python
"""Configuração de logging estruturado em JSON com identificador de execução."""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

_id_execucao: ContextVar[str] = ContextVar("id_execucao", default="-")

_ATRIBUTOS_PADRAO = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


def definir_id_execucao(valor: str | None = None) -> str:
    """Define o identificador da execução corrente e o retorna."""
    id_execucao = valor or uuid.uuid4().hex
    _id_execucao.set(id_execucao)
    return id_execucao


class FiltroContexto(logging.Filter):
    """Adiciona o identificador de execução a todos os registros de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Enriquece o registro e permite sua emissão."""
        record.id_execucao = _id_execucao.get()
        return True


class FormatadorJson(logging.Formatter):
    """Formata cada registro como um objeto JSON em uma linha."""

    def format(self, record: logging.LogRecord) -> str:
        """Serializa o registro, incluindo campos de ``extra`` e stack trace."""
        evento: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }
        evento.update({k: v for k, v in vars(record).items() if k not in _ATRIBUTOS_PADRAO})
        if record.exc_info:
            evento["exception"] = self.formatException(record.exc_info)
        return json.dumps(evento, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO") -> None:
    """Configura o logger raiz. Deve ser chamada uma única vez, no ponto de entrada."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatadorJson())
    handler.addFilter(FiltroContexto())
    raiz = logging.getLogger()
    raiz.handlers[:] = [handler]
    raiz.setLevel(nivel)
```

Saída típica:

```json
{"ts": "2026-10-12T03:00:04.512+00:00", "nivel": "INFO", "logger": "meu_projeto.pipelines.vendas", "mensagem": "pipeline concluído", "pipeline": "vendas", "data_referencia": "2026-10-12", "lidos": 1520, "validos": 1514, "rejeitados": 6, "resumos_gravados": 38, "duracao_s": 4.211, "id_execucao": "3f2c9a..."}
```

### 10.3 Exceções sem perder a causa

```python
# Correto: enriquece com contexto e preserva a causa original
try:
    repositorio.substituir_particao(data_referencia, resumos)
except sqlite3.DatabaseError as exc:
    raise CargaFalhouError(f"falha ao gravar partição {data_referencia}") from exc
```

```python
# Correto: recuperação documentada (rejeição) com log agregado, sem log por registro
resultado = validar_vendas(registros)
if resultado.rejeitados:
    logger.warning(
        "registros rejeitados enviados para quarentena",
        extra={"quantidade": len(resultado.rejeitados)},
    )
```

```python
# Incorreto: engole a falha; o pipeline "termina com sucesso" sem gravar nada
try:
    repositorio.substituir_particao(data_referencia, resumos)
except Exception as e:
    logger.error(f"erro: {e}")  # sem stack trace, f-string, sem relançar
```

```python
# Incorreto: log por registro em laço de alto volume, com dado pessoal
for cliente in clientes:
    logger.info("processando cliente %s com CPF %s", cliente.nome, cliente.cpf)
```

---

## 11. CI/CD e validação automatizada

### 11.1 Pipeline mínimo obrigatório

**[OBRIGATÓRIO] CI-01** — Todo PR e todo push na branch principal executam, nesta ordem e falhando no primeiro erro:

| # | Etapa | Comando |
|---|---|---|
| 1 | Validar configuração e lockfile | `poetry check --lock` |
| 2 | Instalar dependências do lock | `poetry install --no-interaction` |
| 3 | Lint (inclui imports) | `poetry run ruff check .` |
| 4 | Verificar formatação | `poetry run ruff format --check .` |
| 5 | Testes unitários + cobertura ≥ 50% | `poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50` |
| 6 | Build estrito da documentação | `poetry run mkdocs build --strict` |

**[OBRIGATÓRIO] CI-02** — A CI usa a versão do Python de `.python-version` e uma versão fixa do Poetry compatível com `requires-poetry`.

**[OBRIGATÓRIO] CI-03** — Nenhuma etapa usa `pip` para instalar dependências do projeto. O Poetry é instalado pelo instalador oficial ou pelo pipx.

**[OBRIGATÓRIO] CI-04** — A branch principal é protegida: merge só com CI verde e pelo menos uma aprovação de revisão.

**[RECOMENDADO] CI-05** — Testes de integração rodam em um job separado (`poetry run pytest tests/integration -m integration`) com os recursos necessários (serviços em contêiner, ambiente de homologação). Esse job pode ser obrigatório em PRs que alteram `repositories/` ou `integrations/`.

**[RECOMENDADO] CI-06** — Use cache do ambiente virtual com chave baseada no hash do `poetry.lock`.

### 11.2 Execução local equivalente

```bash
poetry check --lock
poetry install
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50
poetry run mkdocs build --strict
```

Se todos os comandos passarem localmente, a CI deve passar também. Uma divergência entre os dois indica diferença de ambiente e precisa ser investigada, não contornada.

### 11.3 GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]

env:
  POETRY_VERSION: "2.2.1"

jobs:
  qualidade:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Instalar Poetry
        run: pipx install "poetry==${POETRY_VERSION}"

      - name: Configurar Python
        id: python
        uses: actions/setup-python@v5
        with:
          python-version-file: ".python-version"
          cache: "poetry"

      - name: Selecionar interpretador
        run: poetry env use "${{ steps.python.outputs.python-path }}"

      - name: Validar pyproject.toml e poetry.lock
        run: poetry check --lock

      - name: Instalar dependências
        run: poetry install --no-interaction

      - name: Ruff lint
        run: poetry run ruff check .

      - name: Ruff format
        run: poetry run ruff format --check .

      - name: Testes unitários e cobertura
        run: >-
          poetry run pytest tests/unit
          --cov=meu_projeto
          --cov-report=term-missing
          --cov-fail-under=50

      - name: Documentação
        run: poetry run mkdocs build --strict
```

> O `pipx` já vem instalado nos runners `ubuntu-latest` do GitHub. O cache `poetry` do `setup-python` exige que o Poetry seja instalado **antes** dessa etapa.

### 11.4 GitLab CI

```yaml
# .gitlab-ci.yml
default:
  image: python:3.12

variables:
  POETRY_VERSION: "2.2.1"
  POETRY_VIRTUALENVS_IN_PROJECT: "true"

cache:
  key:
    files: [poetry.lock]
  paths: [.venv/]

qualidade:
  stage: test
  before_script:
    - curl -sSL https://install.python-poetry.org | python3 - --version "$POETRY_VERSION"
    - export PATH="$HOME/.local/bin:$PATH"
    - poetry check --lock
    - poetry install --no-interaction
  script:
    - poetry run ruff check .
    - poetry run ruff format --check .
    - poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50
    - poetry run mkdocs build --strict
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

### 11.5 Outras plataformas

Para Azure Pipelines, Jenkins, Bitbucket ou outras, aplique os mesmos requisitos:

1. Imagem ou agente com a versão de Python de `.python-version`.
2. Poetry instalado em versão fixa pelo instalador oficial ou pelo pipx.
3. Os seis comandos da seção 11.1, na mesma ordem, falhando no primeiro erro.
4. Cache opcional do `.venv` com chave no hash do `poetry.lock`.
5. Status da CI obrigatório para o merge.

**[OPCIONAL] CI-07** — Hooks de `pre-commit` com `ruff check --fix` e `ruff format` adiantam o feedback. Eles não substituem a CI.

---

## 12. Git, revisão de código e manutenção

### 12.1 Regras

| ID | Nível | Regra |
|---|---|---|
| GIT-01 | **[OBRIGATÓRIO]** | Nada é integrado na branch principal sem PR, revisão e CI verde. |
| GIT-02 | **[RECOMENDADO]** | Commits pequenos e coesos, que compilam e passam nos testes. Mensagem no imperativo explicando o quê e por quê. Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`) é recomendado. |
| GIT-03 | **[RECOMENDADO]** | PRs pequenos (idealmente menos de ~400 linhas alteradas, sem contar o lock), com um objetivo. Refatoração e mudança funcional ficam em PRs separados quando possível. |
| GIT-04 | **[OBRIGATÓRIO]** | A descrição do PR traz: contexto e motivação, o que mudou, como foi testado (comandos executados), impactos (dados, contratos, configuração, dependências) e como fazer rollback quando for relevante. |
| GIT-05 | **[OBRIGATÓRIO]** | O repositório não contém segredos, `.env` reais, `.venv/`, caches, relatórios de cobertura, `site/`, dados de produção nem arquivos temporários. |
| GIT-06 | **[OBRIGATÓRIO]** | Mudanças em dependências (`pyproject.toml`/`poetry.lock`) e em configuração de ferramentas (`[tool.ruff]`, `[tool.pytest]`, `[tool.coverage]`, CI) são destacadas na descrição do PR e revisadas explicitamente. |
| GIT-07 | **[OBRIGATÓRIO]** | Mudanças incompatíveis (contrato de saída, schema, CLI, variáveis de ambiente) são sinalizadas no PR, registradas no `CHANGELOG.md` e versionadas conforme SemVer quando o projeto é consumido por outros. |
| GIT-08 | **[RECOMENDADO]** | A versão em `[project].version` é atualizada com `poetry version <patch\|minor\|major>`. |

### 12.2 `.gitignore` de referência

```gitignore
# Ambientes e configuração local
.venv/
.env
.env.*
!.env.example
poetry.toml.local

# Python
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/

# Ferramentas
.ruff_cache/
.pytest_cache/
.mypy_cache/
.coverage
.coverage.*
coverage.xml
htmlcov/

# Documentação gerada
site/

# Dados e artefatos locais
dados/
*.db
*.parquet
*.log

# Editores e SO
.idea/
.vscode/*
!.vscode/settings.json
.DS_Store
Thumbs.db
```

> O `poetry.toml` gerado por `poetry config ... --local` pode ser versionado, se o time quiser padronizar `virtualenvs.in-project = true`. Ele não pode conter credenciais. Para tokens de repositórios privados, use `poetry config http-basic.<repo>` **sem** `--local`, ou variáveis de ambiente.

### 12.3 Foco da revisão de código

1. **Corretude**: o código faz o que o PR diz? Casos de borda, nulos, fuso horário, precisão decimal, idempotência.
2. **Segurança**: segredos, dados pessoais em logs, SQL parametrizado, validação de entrada.
3. **Testes**: os cenários relevantes estão cobertos? Os testes falhariam se o código estivesse errado?
4. **Arquitetura**: respeita as camadas da seção 1.4? Introduz acoplamento ou abstração desnecessária?
5. **Legibilidade**: nomes, tamanho das funções, docstrings e tipos.
6. **Operação**: logs suficientes para diagnosticar, reprocessamento seguro, impacto em volume e memória.
7. **Documentação**: atualizada conforme a mudança.

### 12.4 Checklist de pull request

**Autor (antes de pedir revisão):**

- [ ] O PR tem objetivo único, e a descrição traz contexto, mudanças, testes executados e impactos.
- [ ] `poetry check --lock` passou.
- [ ] `poetry run ruff check .` passou sem novas supressões injustificadas.
- [ ] `poetry run ruff format --check .` passou.
- [ ] `poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50` passou.
- [ ] Os testes de integração relevantes foram executados (ou o PR explica por que não).
- [ ] `poetry run mkdocs build --strict` passou.
- [ ] Novos comportamentos têm testes de sucesso, entrada inválida, limite e falha.
- [ ] A documentação e o `CHANGELOG.md` foram atualizados quando aplicável.
- [ ] Nenhum segredo, dado pessoal, arquivo temporário ou artefato gerado foi versionado.
- [ ] Novas dependências têm justificativa, foram adicionadas via `poetry add`, e `pyproject.toml` e `poetry.lock` estão no mesmo commit.
- [ ] Mudanças incompatíveis estão sinalizadas.

**Revisor:**

- [ ] A lógica está correta, inclusive em bordas (vazio, nulo, duplicado, fuso, decimal).
- [ ] As etapas de extração, validação, transformação, carga e orquestração estão separadas.
- [ ] Escritas são idempotentes e transacionais quando aplicável.
- [ ] Integrações têm timeout, retry restrito a falhas transitórias e paginação completa.
- [ ] As exceções são específicas e preservam a causa, sem `except` genérico fora do ponto de entrada.
- [ ] Os logs são estruturados, sem segredos e sem dados pessoais, e não são emitidos por registro em laços.
- [ ] Os testes verificam comportamento, não implementação, e falhariam se o código estivesse errado.
- [ ] Não há abstrações prematuras, código morto nem duplicação relevante.
- [ ] Mudanças de configuração de ferramentas e de dependências foram justificadas.
- [ ] A CI está verde.

---

## 13. Regras para agentes de IA

Estas regras valem para qualquer agente de IA (assistente de código, agente autônomo, bot de revisão) que crie, modifique, revise ou teste código nos projetos do time. Elas se somam a todas as regras anteriores.

### 13.1 Antes de alterar

| ID | Nível | Regra |
|---|---|---|
| IA-01 | **[OBRIGATÓRIO]** | Ler este documento e aplicá-lo antes de qualquer alteração. |
| IA-02 | **[OBRIGATÓRIO]** | Inspecionar a estrutura existente (`pyproject.toml`, `src/`, `tests/`, `docs/`, CI) e reaproveitar os padrões já adotados no projeto: nomes, idioma, organização, bibliotecas. |
| IA-03 | **[OBRIGATÓRIO]** | Quando o projeto divergir deste documento, aplicar o padrão nos arquivos tocados pela tarefa e **relatar** as demais divergências, sem corrigi-las fora do escopo. |
| IA-04 | **[OBRIGATÓRIO]** | Pedir esclarecimento quando os requisitos forem conflitantes ou ambíguos de um jeito que impeça uma implementação segura (ex.: regra de negócio indefinida, risco de perda de dados, mudança de contrato). |

### 13.2 Durante a alteração

| ID | Nível | Regra |
|---|---|---|
| IA-05 | **[OBRIGATÓRIO]** | Fazer alterações pequenas, modulares e coerentes com a arquitetura (seção 1.4). |
| IA-06 | **[OBRIGATÓRIO]** | Não reescrever arquivos ou módulos inteiros sem necessidade. Não reformatar nem renomear código fora do escopo da tarefa. |
| IA-07 | **[OBRIGATÓRIO]** | **Nunca usar `pip`** de nenhuma forma. Instalar, remover e atualizar dependências apenas com `poetry add`, `poetry remove` e `poetry update`. |
| IA-08 | **[OBRIGATÓRIO]** | Não introduzir dependências sem justificativa explícita no relatório (o que resolve, por que a biblioteca padrão ou as dependências existentes não bastam). |
| IA-09 | **[OBRIGATÓRIO]** | Não editar o `poetry.lock` à mão. |
| IA-10 | **[OBRIGATÓRIO]** | Não desabilitar, afrouxar ou contornar verificações (regras do Ruff, `fail_under`, `--strict`, testes marcados como `skip`/`xfail`, `# noqa`, `# pragma: no cover`) sem justificativa técnica e autorização explícita. |
| IA-11 | **[OBRIGATÓRIO]** | Escrever ou atualizar testes para todo comportamento novo ou alterado. |
| IA-12 | **[OBRIGATÓRIO]** | Atualizar a documentação (`docs/`, `README.md`, `CHANGELOG.md`) quando houver mudança de comportamento, configuração, variáveis de ambiente ou forma de execução. |
| IA-13 | **[OBRIGATÓRIO]** | Nunca incluir segredos reais, dados pessoais ou dados de produção em código, testes, fixtures ou documentação. |
| IA-14 | **[OBRIGATÓRIO]** | Quando faltar no projeto a configuração de uma ferramenta obrigatória (Ruff, Pytest/cobertura, MkDocs), propor e implementar a **configuração mínima** coerente com a seção 3, dentro do escopo da tarefa, e relatar isso. |

### 13.3 Validação e relatório

**[OBRIGATÓRIO] IA-15** — Depois de alterar código, executar no mínimo:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50
```

Quando a documentação ou o `mkdocs.yml` forem alterados, executar também `poetry run mkdocs build --strict`. Quando dependências forem alteradas, executar também `poetry check --lock`.

**[OBRIGATÓRIO] IA-16** — Nunca afirmar que um teste, lint, build ou validação foi executado sem tê-lo executado de fato. Se não foi possível executar (ferramenta ausente, sem acesso a rede, serviço externo indisponível), dizer isso explicitamente.

**[OBRIGATÓRIO] IA-17** — O relatório final do agente contém:

```markdown
## Resumo
<o que foi alterado e por quê>

## Arquivos alterados
- src/meu_projeto/...: <motivo>

## Comandos executados
| Comando | Resultado |
|---|---|
| `poetry run ruff check .` | ✅ sem problemas |
| `poetry run ruff format --check .` | ✅ |
| `poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50` | ✅ 42 passed, cobertura 68% |
| `poetry run mkdocs build --strict` | ⚠️ não executado: docs não alteradas |

## Dependências
<adicionadas/removidas e justificativa, ou "nenhuma alteração">

## Limitações e pendências
<o que não foi validado, divergências do skill.md encontradas fora do escopo, decisões que precisam de confirmação>
```

**[OBRIGATÓRIO] IA-18** — Se uma verificação falhar e não puder ser corrigida dentro do escopo, o agente informa a falha com a saída relevante e não declara a tarefa concluída.

---

## 14. Checklist de conformidade

Use este checklist para adotar o padrão em um projeto novo, auditar projetos existentes e decidir se um PR está pronto para integração.

| # | Item | Como verificar |
|---|---|---|
| 1 | [ ] Estrutura `src/` com pacote em `snake_case` configurada em `[tool.poetry].packages` | Inspeção do `pyproject.toml` e de `src/` |
| 2 | [ ] Projeto modular, com extração, validação, transformação, carga e orquestração separadas | Revisão da arquitetura (`docs/architecture.md`) |
| 3 | [ ] Imports absolutos e sem dependências circulares | `poetry run ruff check .` (`TID252`) e revisão |
| 4 | [ ] Dependências gerenciadas apenas pelo Poetry, sem uso de `pip` em docs, scripts, Dockerfiles ou CI | `git grep -nE "pip (install\|uninstall\|freeze)\|-m pip"` sem ocorrências |
| 5 | [ ] `pyproject.toml` centraliza metadados, dependências, Ruff, Pytest e Coverage | Ausência de `setup.py`, `setup.cfg`, `ruff.toml`, `pytest.ini`, `.coveragerc` |
| 6 | [ ] `poetry.lock` versionado e consistente | `poetry check --lock` |
| 7 | [ ] `.python-version` e `requires-python` definidos e coerentes | Inspeção |
| 8 | [ ] Ruff lint configurado e aprovado | `poetry run ruff check .` |
| 9 | [ ] Ruff format aprovado | `poetry run ruff format --check .` |
| 10 | [ ] Organização de imports (`I`) habilitada no `select` e validada | `[tool.ruff.lint].select` contém `"I"` |
| 11 | [ ] Pytest configurado com `--strict-markers` e marcador `integration` | `[tool.pytest.ini_options]` |
| 12 | [ ] Cobertura de testes unitários ≥ 50% | `poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50` |
| 13 | [ ] Testes de integração separados e marcados | `poetry run pytest tests/integration -m integration` |
| 14 | [ ] MkDocs Material configurado, com `nav` explícita e páginas mínimas | Inspeção de `mkdocs.yml` e `docs/` |
| 15 | [ ] Build estrito da documentação aprovado | `poetry run mkdocs build --strict` |
| 16 | [ ] Credenciais e dados sensíveis protegidos (sem segredos no repositório, `repr=False`, logs sem dados pessoais) | Secret scanning e revisão |
| 17 | [ ] Configuração validada na inicialização | Teste de `carregar_configuracao` com variáveis ausentes |
| 18 | [ ] Logging estruturado com identificador de execução | Execução local e inspeção dos logs |
| 19 | [ ] Pipeline de CI executando todas as verificações obrigatórias, com branch principal protegida | Configuração da CI e regras da branch |
| 20 | [ ] `.gitignore` cobrindo `.venv/`, caches, `htmlcov/`, `site/`, `.env` | Inspeção |
| 21 | [ ] `README.md` e `docs/development.md` atualizados | Revisão |
| 22 | [ ] PR revisado, aprovado e com CI verde | Plataforma de Git |

**Critério de pronto para integração:** todos os itens aplicáveis marcados. Um item não atendido exige exceção justificada e aprovada no PR (seção 0.1). Sem isso, o código **não está pronto para integração**.

---

## 15. Referência rápida de comandos

```bash
# Ambiente
poetry --version
poetry config virtualenvs.in-project true --local
poetry env use 3.12
poetry install
poetry sync
poetry env info

# Dependências
poetry add <pacote>
poetry add --group dev <pacote>
poetry remove <pacote>
poetry update <pacote>
poetry show --outdated
poetry check --lock

# Qualidade
poetry run ruff check .
poetry run ruff check . --fix
poetry run ruff format .
poetry run ruff format --check .

# Testes
poetry run pytest tests/unit
poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50
poetry run pytest tests/unit --cov=meu_projeto --cov-report=html --cov-fail-under=50
poetry run pytest tests/integration -m integration

# Documentação
poetry run mkdocs serve
poetry run mkdocs build --strict

# Execução
poetry run python -m meu_projeto.cli --data-referencia 2026-10-12
poetry run meu-projeto --data-referencia 2026-10-12

# Sequência completa equivalente à CI
poetry check --lock && poetry install && \
poetry run ruff check . && poetry run ruff format --check . && \
poetry run pytest tests/unit --cov=meu_projeto --cov-report=term-missing --cov-fail-under=50 && \
poetry run mkdocs build --strict
```
