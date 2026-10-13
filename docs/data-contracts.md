# Contratos de dados

## Camada bruta

Uma tabela por endpoint da OpenF1, com o **mesmo nome do endpoint** e as colunas com o nome dos campos da API. O contrato de cada tabela é a `dataclass` correspondente em `src/f1/domain/modelos.py`, que é a fonte da verdade (campos, tipos e obrigatoriedade).

| Tabela | Entidade | Granularidade | Partição | Observações |
|---|---|---|---|---|
| `meetings` | `Meeting` | fim de semana | `year` | |
| `sessions` | `Sessao` | sessão | `year` | `session_type` ∈ `Practice`, `Qualifying`, `Race` |
| `drivers` | `Piloto` | piloto × sessão | `session_key` | sem `country_code` (depreciado) |
| `laps` | `Volta` | volta | `session_key` | `segments_sector_*` como `INTEGER[]` |
| `stints` | `Stint` | stint | `session_key` | `compound` pode ser nulo |
| `pit` | `PitStop` | passagem pelo pit | `session_key` | sem `pit_duration` (depreciado); `stop_duration` só desde o GP dos EUA 2024 |
| `session_result` | `ResultadoSessao` | piloto × sessão | `session_key` | na classificação, `duration`/`gap_to_leader` viram `*_q1`, `*_q2`, `*_q3` |
| `starting_grid` | `GridLargada` | piloto | `session_key` | publicado na sessão de **classificação** |
| `weather` | `Clima` | minuto | `session_key` | |
| `race_control` | `ControleProva` | mensagem | `session_key` | |
| `position` | `Posicao` | mudança de posição | `session_key` | |
| `intervals` | `Intervalo` | ~4 s | `session_key` | só corridas |
| `overtakes` | `Ultrapassagem` | ultrapassagem | `session_key` | só corridas; pode estar incompleto |
| `team_radio` | `RadioEquipe` | mensagem | `session_key` | só a URL do MP3 |
| `championship_drivers` | `CampeonatoPiloto` | piloto | `session_key` | beta; só corridas |
| `championship_teams` | `CampeonatoEquipe` | equipe | `session_key` | beta; só corridas |
| `car_data` | `DadosCarro` | ~3,7 Hz | `session_key` + `driver_number` | opcional (`--com-telemetria`) |
| `location` | `Localizacao` | ~3,7 Hz | `session_key` + `driver_number` | opcional (`--com-telemetria`) |

### Tipos

| Python | DuckDB | Regra de validação |
|---|---|---|
| `int` | `INTEGER` | inteiro JSON; recusa texto e booleano |
| `Decimal` | `DECIMAL(18, 3)` | número finito |
| `float` | `DOUBLE` | número |
| `str` | `VARCHAR` | texto |
| `bool` | `BOOLEAN` | booleano JSON |
| `datetime` | `TIMESTAMP` (UTC) | ISO 8601; sem fuso, assume UTC |
| `StrEnum` | `VARCHAR` | valor do domínio do enum |
| `tuple[int \| None, ...]` | `INTEGER[]` | lista |
| `Gap` | `<campo>_segundos DECIMAL(18, 3)` + `<campo>_voltas INTEGER` | número de segundos **ou** `"+N LAP(S)"` |

**Gap:** o líder tem `segundos = 0`. Em `intervals`, o `null` da API (líder) vira `0`. Em `session_result`, um gap nulo (abandono, por exemplo) deixa as duas colunas nulas.

## Camada analítica

Recalculada por inteiro pelo comando `f1 analitico`, a partir das tabelas brutas da sessão. As entidades ficam em `src/f1/domain/analitico.py`.

| Tabela | Granularidade | Conteúdo |
|---|---|---|
| `ritmo_piloto` | piloto × sessão | voltas totais e válidas, melhor volta e seu número, ritmo médio das voltas representativas (com tempo, fora do pit-out e fora de SC/VSC) |
| `estrategia_piloto` | piloto × sessão | compostos em ordem, voltas por stint, número de paradas, tempo total no pit lane e parado |
| `telemetria_volta` | piloto × volta | amostras, velocidade máxima e média, acelerador médio, % de acelerador pleno (≥ 99), % de freio, % de DRS aberto (10, 12 ou 14) |

**Períodos de SC/VSC:** começam na volta da mensagem `... DEPLOYED` de `race_control` (categoria `SafetyCar`) e terminam, inclusive, na volta de `... IN THIS LAP` ou `... ENDING`. Um VSC convertido em SC mantém o início do VSC.

**Telemetria por volta:** cada volta vai do seu `date_start` até o `date_start` da volta seguinte. A última termina em `date_start + lap_duration`. Amostras fora de qualquer volta são ignoradas.

## Quarentena

| Coluna | Conteúdo |
|---|---|
| `id_execucao` | identificador da execução (o mesmo dos logs) |
| `endpoint` | endpoint de origem |
| `particao` | por exemplo `session_key=9606` ou `session_key=9606/driver_number=1` |
| `registro` | registro original em JSON |
| `motivo` | campo e regra violada |
| `registrado_em` | instante UTC da execução |
