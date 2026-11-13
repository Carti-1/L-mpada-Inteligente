# Lâmpada Lab — Etapas 2 e 3

Base de implementação para receber leituras de um ESP32, persistir séries temporais no InfluxDB e documentar a integração com Arduino IoT Cloud. Os detalhes de sensores e pinos dependem do circuito real e devem ser confirmados antes de fechar o firmware.

## Arquitetura

```text
Sensores → ESP32 → API FastAPI → InfluxDB (bucket com retenção)
                    └────────→ Arduino IoT Cloud (variáveis e dashboard)
```

A API recebe timestamp, identificador do dispositivo e leituras de nível do tanque, temperatura, umidade, luminosidade, cor e botão. Cada campo de sensor é opcional, mas cada envio precisa conter ao menos um valor. O Arduino IoT Cloud sincroniza variáveis do dispositivo com os widgets do dashboard; a API usa um token próprio do InfluxDB para persistência.

## Banco de dados

O backend usa a API de escrita e consulta do InfluxDB 2.x. Crie um bucket (por exemplo, `lampada-lab`) e defina uma retenção adequada ao prazo do trabalho. Gere um token com permissões mínimas de leitura e escrita somente nesse bucket. Guarde URL, token, organização e bucket no `.env`; nunca envie esse arquivo ao GitHub.

## Como montar o projeto

1. Instale Python 3.11 ou superior e prepare o InfluxDB 2.x compatível.
2. Na conta Arduino IoT Cloud, crie um Device e uma Thing para o ESP32.
3. Crie as variáveis `temperature` (float), `humidity` (float), `luminosity` (float), `tankLevel` (float), `color` (string) e `buttonState` (boolean). Associe-as aos widgets do dashboard.
4. Copie `firmware/secrets.example.h` para `firmware/secrets.h`, configure a URL interna do backend e a chave da API; complete `readSensors()` com os sensores e pinos do circuito real. Instale ArduinoJson. Não compartilhe credenciais no repositório.
5. Para Grafana, adicione o InfluxDB como fonte de dados usando a organização e o token; crie gráficos por campo e dispositivo. O dashboard do Arduino Cloud e o do Grafana são superfícies distintas.

## Como rodar o backend

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite `.env` com a chave da API e os dados do InfluxDB. Gere uma chave aleatória para `API_KEY`; use token InfluxDB separado e restrito ao bucket. Depois inicie o serviço:

```powershell
py -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Documentação interativa: `http://localhost:8000/docs`. Verificação de disponibilidade: `GET /health`.

## Como enviar e consultar dados

Envie `POST /api/v1/readings` com o cabeçalho `X-API-Key` igual à chave configurada no backend e um JSON como:

```json
{
  "device_id": "lampada-01",
  "timestamp": "2026-11-13T12:00:00Z",
  "tank_level": 42.5,
  "temperature": 25.1,
  "humidity": 61.0,
  "luminosity": 315,
  "color": "azul",
  "button": false
}
```

Consulte `GET /api/v1/readings?range=-24h` com o mesmo cabeçalho. O intervalo aceita formatos como `-30m`, `-24h` ou `-7d`, e a API retorna no máximo 500 leituras recentes.

## Segurança e dados

- `.env`, chaves Arduino e `thingProperties.h` não devem ser versionados.
- Configure HTTPS quando a API sair da rede local.
- A retenção do InfluxDB define por quanto tempo os dados ficam consultáveis.
- O endpoint de consulta exige a chave da API e limita a janela e a quantidade retornada.
- Não incluímos `secrets.h`, tokens, senha Wi-Fi ou credenciais reais neste repositório.

## Etapas e estado

- Etapa 2: API e persistência InfluxDB com configuração por ambiente preparadas; falta configurar o serviço e o bucket da equipe, validar os dados reais do ESP32 e criar os widgets na conta Arduino IoT Cloud.
- Etapa 3: README e estrutura para versionamento preparados. A branch local é `feat/lampada-lab`; publicar no GitHub depende de associar este repositório ao remoto da equipe.
- O edital também menciona Grafana; o README descreve a configuração, mas o dashboard e os dados reais precisam ser montados no ambiente da equipe.
