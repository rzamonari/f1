# Configuração

Toda a configuração vem de variáveis de ambiente, lidas e validadas **uma vez**, no início da execução (`f1.config.settings.carregar_configuracao`). Uma variável obrigatória ausente ou um valor inválido interrompe o processo antes de qualquer leitura ou escrita. A mensagem de erro cita o nome da variável, nunca o valor.

| Variável | Obrigatória | Padrão | Exemplo | Segredo |
|---|---|---|---|---|
| `F1_AMBIENTE` | sim | — | `dev`, `hml`, `prd` | não |
| `F1_CAMINHO_BANCO` | sim | — | `./dados/f1.duckdb` | não |
| `F1_API_BASE_URL` | não | `https://api.openf1.org/v1` | | não |
| `F1_TIMEOUT_S` | não | `30` | timeout de leitura por requisição (a conexão tem 5 s) | não |
| `F1_MAX_TENTATIVAS` | não | `4` | tentativas por requisição, contando a primeira | não |
| `F1_PAUSA_ENTRE_REQUISICOES_S` | não | `0.5` | pausa após cada requisição | não |
| `F1_JANELA_TELEMETRIA_MIN` | não | `10` | tamanho da janela de `car_data`/`location` | não |
| `F1_LIMITE_TAXA_REJEICAO` | não | `0.05` | entre `0` e `1`, por endpoint e partição | não |
| `F1_MARGEM_APOS_SESSAO_MIN` | não | `60` | espera após `date_end` antes de ingerir a sessão | não |
| `F1_NIVEL_LOG` | não | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | não |
| `F1_OPENF1_USUARIO` / `F1_OPENF1_SENHA` | não | — | reservadas para o tempo real (não usadas nesta versão) | **sim** |

## Desenvolvimento local e produção

- **Local:** `.env.example` (versionado, só com valores fictícios) serve de modelo. O `.env` real não é versionado.
- **Produção:** os valores vêm das variáveis do agendador ou do gerenciador de segredos da plataforma. As credenciais da OpenF1, quando o tempo real for implementado, ficam só no gerenciador de segredos.

## Exemplo de teste de configuração

```python
from f1.config.settings import carregar_configuracao

configuracao = carregar_configuracao({"F1_AMBIENTE": "dev", "F1_CAMINHO_BANCO": "f1.duckdb"})
```
