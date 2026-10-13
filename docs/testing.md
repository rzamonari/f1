# Testes e qualidade

## Comandos

```bash
# Unitários com cobertura (piso de 50%, o mesmo da CI)
poetry run pytest tests/unit --cov=f1 --cov-report=term-missing --cov-fail-under=50

# Integração: DuckDB em tmp_path e OpenF1 simulada, sem rede
poetry run pytest tests/integration -m integration

# Fumaça contra a API real (opcional, fora da CI)
F1_TESTES_REDE=1 poetry run pytest tests/integration/test_openf1_real.py -m integration
```

## Organização

```text
tests/
├── conftest.py              # fakes em memória (FonteFake, BancoFake, QuarentenaFake) e fábricas
├── fixtures/
│   └── openf1_amostras.json # respostas reais e reduzidas da OpenF1, uma por endpoint
├── unit/                    # espelha src/f1/
└── integration/
    ├── repositories/        # DuckDB real em tmp_path
    ├── test_cli.py          # CLI de ponta a ponta com httpx.MockTransport
    └── test_openf1_real.py  # só com F1_TESTES_REDE=1
```

## Fixtures da OpenF1

`tests/fixtures/openf1_amostras.json` reúne respostas da API salvas uma vez e reduzidas a poucos registros (sessões 9602, 9606 e 9673 de 2024). São dados públicos de pilotos e equipes. Elas cobrem os casos da API que afetam o contrato:

- `session_result` da classificação, com arrays Q1–Q3;
- `intervals` do líder, com `0.0`;
- `pit` sem `stop_duration` e com o campo depreciado `pit_duration`;
- `drivers` com o campo depreciado `country_code`;
- `race_control` com SC e VSC, incluindo um VSC convertido em SC.

Para atualizar uma amostra, consulte a API com filtros que limitem o volume (por exemplo, `laps?session_key=9673&driver_number=1&lap_number<=3`) e substitua só a chave correspondente.

## Diretrizes

- Testes unitários não acessam rede nem banco. O relógio (`ParametrosSessao.agora`) e o `sleep` do cliente são injetados.
- Todo pipeline tem teste de idempotência: rodar duas vezes e comparar o estado final.
- Prefira os fakes do `conftest.py` a mocks. `FonteFake(..., filtrar_por_igualdade=True)` aplica os filtros `=` como a API.
