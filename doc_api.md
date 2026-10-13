# OpenF1 API — Guia de Referência

> Resumo da documentação oficial: <https://openf1.org/docs/> e <https://openf1.org/auth.html>

## 1. Visão geral

A **OpenF1** é uma API aberta com dados de Fórmula 1: telemetria, tempos de volta, posições, pit stops, rádio, clima, controle de prova etc.

- **URL base:** `https://api.openf1.org/v1/<endpoint>`
- **Dados históricos (2023 em diante):** gratuitos, **sem autenticação**.
- **Dados em tempo real:** exigem assinatura paga (patrocínio do projeto) e autenticação.

## 2. Uso geral

### Formato de resposta
- **JSON** por padrão.
- **CSV:** adicione `csv=true` → `/v1/sessions?year=2023&csv=true`

### Filtros
- Qualquer atributo do endpoint pode ser usado como parâmetro de URL.
- Operadores: `=`, `>`, `<`, `>=`, `<=`
  - `/v1/car_data?driver_number=55&session_key=9159&speed>=315`
- **Vários valores:** repita o parâmetro → `driver_number=4&driver_number=81`
- Valores com espaço podem ser passados direto (ex.: `flag=BLACK AND WHITE`), ou codificados (`%20`).
- Campos do tipo **array não podem ser filtrados**.

### Datas
- Use operadores no campo `date` (ou `date_start`): `date>=2023-09-01&date<=2023-09-30`
- Aceita ISO 8601 (`2023-09-16T13:03:35.200`) e diversos outros formatos.

### Palavra-chave `latest`
- `meeting_key=latest` e `session_key=latest` apontam para o evento/sessão mais recente (ou em andamento).

### Observações
- `sessions` e `meetings` são atualizados diariamente à meia-noite UTC.
- A cobertura de `team_radio` caiu bastante a partir de 2026.

## 3. Autenticação e tempo real

### Token (OAuth2 password flow)
```bash
curl -X POST https://api.openf1.org/token \
  -d "username=SEU_USUARIO" -d "password=SUA_SENHA"
```
Resposta: `{ "access_token": "...", "expires_in": 3600, "token_type": "bearer" }`

- O token expira em **1 hora** — renove quando necessário.
- Envie nas requisições REST: `Authorization: Bearer <access_token>`
- Faça essa troca **no backend**; nunca exponha credenciais/token no front-end.
- Autenticação aumenta os limites de taxa (a documentação **não** publica valores numéricos).

### Streaming (MQTT / WebSocket)
| Protocolo | Endereço |
|-----------|----------|
| MQTT (TLS) | `mqtt.openf1.org:8883` |
| WebSocket  | `wss://mqtt.openf1.org:8084/mqtt` |

- Login: usuário = qualquer string não vazia (ex.: e-mail); senha = `access_token`.
- **Tópicos** = caminho do endpoint: `v1/laps`, `v1/location`, `v1/sessions`… (suporta curinga `#`).
- Mensagens têm os mesmos campos do REST, mais:
  - `_id`: ID crescente (ordenação cronológica)
  - `_key`: identifica atualizações do mesmo objeto
- Recomendação: MQTT para backend, WebSocket para navegador.

## 4. Hierarquia das chaves

```
Meeting (meeting_key)        → fim de semana de GP ou teste
  └── Session (session_key)  → TL1, TL2, TL3, Quali, Sprint, Corrida...
        └── driver_number    → dados por piloto
```

Fluxo típico: `meetings` → `sessions` → (`drivers`, `laps`, `car_data`, ...) filtrando por `session_key` e `driver_number`.

## 5. Resumo dos endpoints

| Endpoint | Descrição | Observação |
|----------|-----------|------------|
| `/car_data` | Telemetria do carro (velocidade, RPM, marcha, acelerador, freio, DRS) | ~3,7 Hz |
| `/championship_drivers` | Classificação do campeonato de pilotos | Beta, só corridas |
| `/championship_teams` | Classificação do campeonato de construtores | Beta, só corridas |
| `/drivers` | Informações dos pilotos por sessão | |
| `/intervals` | Gap para o líder e para o carro à frente | ~4 s, só corridas |
| `/laps` | Tempos de volta, setores e speed traps | |
| `/location` | Posição aproximada (x, y, z) do carro na pista | ~3,7 Hz |
| `/meetings` | Fins de semana de GP / testes | |
| `/overtakes` | Ultrapassagens (trocas de posição) | Só corridas, pode ser incompleto |
| `/pit` | Passagens pelo pit lane | |
| `/position` | Posição dos pilotos ao longo da sessão | |
| `/race_control` | Bandeiras, safety car, incidentes, status da sessão | |
| `/sessions` | Sessões de um fim de semana | |
| `/session_result` | Resultado final da sessão | Minutos após publicação oficial |
| `/starting_grid` | Grid de largada | Minutos após publicação oficial |
| `/stints` | Períodos com o mesmo jogo de pneus | |
| `/team_radio` | Rádio piloto–equipe (MP3) | Incompleto |
| `/weather` | Condições climáticas da pista | A cada 1 min |

> Quase todos os endpoints possuem `meeting_key` e `session_key`.

## 6. Detalhes por endpoint

### 6.1 `/car_data` — Telemetria
| Campo | Descrição |
|-------|-----------|
| `date` | Timestamp (UTC) |
| `driver_number` | Número do piloto |
| `brake` | 100 = pressionado, 0 = solto |
| `drs` | 0/1 = desligado, 8 = elegível, 10/12/14 = aberto (outros: desconhecido) |
| `n_gear` | Marcha 0–8 (0 = neutro) |
| `rpm` | Rotação do motor |
| `speed` | Velocidade (km/h) |
| `throttle` | Acelerador (%) |

```
/v1/car_data?driver_number=55&session_key=9159&speed>=315
```

### 6.2 `/championship_drivers` — Campeonato de pilotos (beta)
Campos: `driver_number`, `points_start`, `points_current`, `position_start`, `position_current`.
```
/v1/championship_drivers?session_key=9839&driver_number=4&driver_number=81
```

### 6.3 `/championship_teams` — Campeonato de construtores (beta)
Campos: `team_name`, `points_start`, `points_current`, `position_start`, `position_current`.
```
/v1/championship_teams?session_key=9839&team_name=McLaren
```

### 6.4 `/drivers` — Pilotos
| Campo | Descrição |
|-------|-----------|
| `driver_number` | Número do piloto |
| `full_name`, `first_name`, `last_name` | Nome |
| `broadcast_name` | Nome usado na transmissão (ex.: `M VERSTAPPEN`) |
| `name_acronym` | Sigla de 3 letras (ex.: `VER`) |
| `team_name` | Equipe |
| `team_colour` | Cor da equipe (hex `RRGGBB`) |
| `headshot_url` | Foto do piloto |
| `country_code` | **Depreciado** (removido após 2026) |

```
/v1/drivers?driver_number=1&session_key=9158
```

### 6.5 `/intervals` — Intervalos (só corridas)
| Campo | Descrição |
|-------|-----------|
| `gap_to_leader` | Segundos até o líder (`+N LAP` se retardatário; `null` para o líder) |
| `interval` | Segundos até o carro à frente (mesmas convenções) |

```
/v1/intervals?session_key=9165&interval>0&interval<0.005
```

### 6.6 `/laps` — Voltas
| Campo | Descrição |
|-------|-----------|
| `lap_number` | Número da volta |
| `date_start` | Início aproximado da volta |
| `lap_duration` | Tempo da volta (s) |
| `duration_sector_1/2/3` | Tempo de cada setor (s) |
| `i1_speed`, `i2_speed` | Velocidade nos pontos intermediários (km/h) |
| `st_speed` | Velocidade no speed trap (km/h) |
| `is_pit_out_lap` | Volta de saída do pit |
| `segments_sector_1/2/3` | Mini-setores: 2048 amarelo, 2049 verde, 2051 roxo, 2064 pit lane, 0 indisponível (não disponível em corridas) |

```
/v1/laps?session_key=9161&driver_number=63&lap_number=8
```

### 6.7 `/location` — Localização
Campos: `date`, `driver_number`, `x`, `y`, `z`. Origem arbitrária; indica o progresso na pista, não a posição lateral.
```
/v1/location?session_key=9161&driver_number=81&date>2023-09-16T13:03:35.200&date<2023-09-16T13:03:35.800
```

### 6.8 `/meetings` — Eventos (fins de semana)
| Campo | Descrição |
|-------|-----------|
| `meeting_key` | ID do evento |
| `meeting_name`, `meeting_official_name` | Nome curto / oficial |
| `year` | Ano |
| `location`, `country_name`, `country_code`, `country_key`, `country_flag` | Local / país |
| `circuit_key`, `circuit_short_name` | Circuito |
| `circuit_type` | `Permanent`, `Temporary - Street`, `Temporary - Road` |
| `circuit_image`, `circuit_info_url` | Imagem / dados do circuito |
| `date_start`, `date_end`, `gmt_offset` | Datas e fuso |
| `is_cancelled` | Cancelado? |

```
/v1/meetings?year=2026&country_name=Singapore
```

### 6.9 `/overtakes` — Ultrapassagens (só corridas)
Campos: `date`, `overtaking_driver_number`, `overtaken_driver_number`, `position` (posição do piloto que ultrapassou). Inclui trocas por pit stop e punições pós-prova.
```
/v1/overtakes?session_key=9636&overtaking_driver_number=63&overtaken_driver_number=4&position=1
```

### 6.10 `/pit` — Pit stops
| Campo | Descrição |
|-------|-----------|
| `lap_number` | Volta do pit |
| `lane_duration` | Tempo total no pit lane (s) |
| `stop_duration` | Tempo parado (s) — a partir do GP dos EUA 2024 |
| `pit_duration` | **Depreciado**, alias de `lane_duration` (removido após 2026) |

```
/v1/pit?session_key=9877&stop_duration<2.3
```

### 6.11 `/position` — Posições
Campos: `date`, `driver_number`, `position` (começa em 1). Registra a posição inicial e cada mudança.
```
/v1/position?meeting_key=1217&driver_number=40&position<=3
```

### 6.12 `/race_control` — Controle de prova
| Campo | Descrição |
|-------|-----------|
| `category` | `SessionStatus`, `CarEvent`, `Drs`, `Flag`, `SafetyCar`... |
| `flag` | `GREEN`, `YELLOW`, `DOUBLE YELLOW`, `CHEQUERED`, `BLACK AND WHITE`... |
| `scope` | `Track`, `Driver`, `Sector`... |
| `sector` | Setor afetado |
| `driver_number` | Piloto envolvido |
| `lap_number` | Volta (corridas) |
| `qualifying_phase` | 1–3 (só quali) |
| `message` | Texto da mensagem |

```
/v1/race_control?flag=BLACK AND WHITE&driver_number=1&date>=2023-01-01&date<2023-09-01
```

### 6.13 `/sessions` — Sessões
Campos: `session_key`, `session_name` (ex.: `Sprint Qualifying`), `session_type`, `meeting_key`, `year`, `date_start`, `date_end`, `gmt_offset`, `is_cancelled`, `location`, `country_*`, `circuit_key`, `circuit_short_name`.
```
/v1/sessions?country_name=Belgium&session_name=Sprint%20Qualifying&year=2023
```

### 6.14 `/session_result` — Resultado da sessão
| Campo | Descrição |
|-------|-----------|
| `position` | Posição final |
| `number_of_laps` | Voltas completadas |
| `duration` | Melhor volta (treino/quali), tempo total (corrida) ou array Q1–Q3 |
| `gap_to_leader` | Segundos, `+N LAP(S)` ou array Q1–Q3 na quali |
| `dnf`, `dns`, `dsq` | Booleanos (`dnf`/`dns` só em quali e corrida) |

```
/v1/session_result?session_key=7782&position<=3
```

### 6.15 `/starting_grid` — Grid de largada
Campos: `position`, `driver_number`, `lap_duration` (volta de classificação).
```
/v1/starting_grid?session_key=7783&position<=3
```

### 6.16 `/stints` — Stints de pneus
| Campo | Descrição |
|-------|-----------|
| `stint_number` | Número do stint (começa em 1) |
| `compound` | `SOFT`, `MEDIUM`, `HARD`, `INTERMEDIATE`, `WET`... |
| `lap_start`, `lap_end` | Primeira e última volta do stint |
| `tyre_age_at_start` | Idade do pneu (voltas) no início do stint |

```
/v1/stints?session_key=9165&tyre_age_at_start>=3
```

### 6.17 `/team_radio` — Rádio
Campos: `date`, `driver_number`, `recording_url` (MP3). Seleção parcial divulgada pela F1.
```
/v1/team_radio?session_key=9158&driver_number=11
```

### 6.18 `/weather` — Clima
| Campo | Descrição |
|-------|-----------|
| `air_temperature` | Temperatura do ar (°C) |
| `track_temperature` | Temperatura da pista (°C) |
| `humidity` | Umidade (%) |
| `pressure` | Pressão (mbar) |
| `rainfall` | Chuva |
| `wind_direction` | Direção do vento (0–359°) |
| `wind_speed` | Velocidade do vento (m/s) |

```
/v1/weather?meeting_key=1208&wind_direction>=130&track_temperature>=52
```

## 7. Exemplos rápidos

### curl
```bash
# Sessão mais recente
curl "https://api.openf1.org/v1/sessions?session_key=latest"

# Sessões de 2023 em CSV
curl "https://api.openf1.org/v1/sessions?year=2023&csv=true" -o sessions_2023.csv
```

### Python (`requests`)
```python
import requests

BASE_URL = "https://api.openf1.org/v1"

def get(endpoint: str, **params):
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

# Última sessão
session = get("sessions", session_key="latest")[0]
print(session["session_name"], session["location"], session["year"])

# Pilotos e voltas de um piloto nessa sessão
drivers = get("drivers", session_key=session["session_key"])
laps = get("laps", session_key=session["session_key"], driver_number=1)

# Operadores (>=, <=) precisam ir na chave do parâmetro
fast = requests.get(f"{BASE_URL}/car_data?session_key=9159&driver_number=55&speed>=315").json()
```

> Dica: operadores como `>=` fazem parte do nome do parâmetro (`speed>=315`), por isso é mais simples montá-los direto na URL do que via `params`.
