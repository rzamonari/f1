# F1: pipeline de dados da OpenF1

Pipeline em Python que extrai dados históricos de Fórmula 1 da [API OpenF1](https://openf1.org/docs/), valida contra contratos explícitos, transforma e grava em um banco analítico **DuckDB** local. O banco serve de base para análises de ritmo de corrida, estratégia de pneus, pit stops, clima e telemetria.

## Escopo

- Dados históricos, de 2023 em diante: gratuitos e sem autenticação.
- Ingestão por **ano** (catálogo de meetings e sessões) e por **sessão** (`session_key`), com reprocessamento idempotente.
- Telemetria (`car_data`, `location`) opcional, lida em janelas de tempo, por piloto.
- Camada analítica derivada: ritmo por piloto, estratégia e telemetria por volta.
- Execução por CLI (`f1`), localmente ou em um agendador.
- Dashboard Streamlit com as 5 voltas mais rápidas por circuito.

## O que o projeto não faz

- **Tempo real** (MQTT/WebSocket): exige assinatura paga e OAuth2. As variáveis `F1_OPENF1_USUARIO`/`F1_OPENF1_SENHA` estão reservadas para essa evolução.
- Download dos áudios de `team_radio`: só a URL do MP3 é guardada.
- Chamadas à API a partir do dashboard: ele só lê o DuckDB.

## Próximos passos

- [Primeiros passos](getting-started.md): instalar e rodar a primeira ingestão.
- [Arquitetura](architecture.md): módulos, fluxo, partições e decisões técnicas.
- [Contratos de dados](data-contracts.md): o que cada tabela contém.
- [Operação](operations.md): agendamento, reprocessamento e volumes.
