# AlertManager → Telegram Live Fire (G7.18.T3)

| Campo | Valor |
|-------|--------|
| **Task** | G7.18.T3 — AlertManager → Telegram live fire |
| **Wave** | G7 Wave 27 |
| **Agente** | cartorio-sre |
| **Config base** | [`infra/alertmanager/alertmanager.yml`](../infra/alertmanager/alertmanager.yml) |
| **Routes SLO** | [`infra/alertmanager/slo_alerts_routes.yml`](../infra/alertmanager/slo_alerts_routes.yml) |
| **Secrets** | **HOLD-GUSTAVO** — nunca commitar bot token / chat ids |

---

## 0. TL;DR

- Receivers Telegram **já estão modelados** em `infra/alertmanager/alertmanager.yml` (P0/P1/default + LGPD + N8N).
- Tokens e chat IDs vêm de **arquivos montados** (`bot_token_file` / `chat_id_file`) — não de YAML com literal.
- Este doc: env vars, exemplo de receiver, **como disparar alerta de teste** (`amtool` / API / curl), checklist de deploy.
- **Live fire em prod** = HOLD até Gustavo provisionar secrets + confirmar grupo Telegram.

---

## 1. Pré-requisitos

1. AlertManager rodando (stack monitoring / compose) e alcançável em `http://alertmanager:9093` **na rede Docker** (ou port-forward local).
2. Bot Telegram criado via **@BotFather** (token `123456789:AA...`).
3. Bot adicionado ao(s) grupo(s) destino com permissão de enviar mensagens.
4. Chat IDs numéricos obtidos (ver §3).
5. Prometheus apontando `alerting.alertmanagers` para o AM (ver `infra/prometheus/prometheus.yml`).

### 1.1 Arquivos de secret (padrão do repo)

No container / host (paths do `alertmanager.yml`):

| Path no container | Conteúdo | Placeholder |
|-------------------|----------|-------------|
| `/etc/alertmanager/secrets/telegram_bot_token` | token BotFather | `TELEGRAM_ALERTMANAGER_BOT_TOKEN` |
| `/etc/alertmanager/secrets/telegram_grupo_pietra_chat_id` | chat id grupo Pietra | `TELEGRAM_GRUPO_PIETRA_CHAT_ID` |
| `/etc/alertmanager/secrets/telegram_grupo_lgpd_chat_id` | chat id LGPD | `TELEGRAM_GRUPO_LGPD_CHAT_ID` |
| `/etc/alertmanager/secrets/telegram_grupo_n8n_chat_id` | chat id N8N | `TELEGRAM_GRUPO_N8N_CHAT_ID` |

Permissões sugeridas: `0400`, owner do user do processo AlertManager.  
**Nunca** commitar esses arquivos. Preferir secret store EasyPanel / Docker secret / bind mount fora do git.

---

## 2. Env vars (host / compose)

Use no deploy (nomes canônicos sugeridos — mapear para files no entrypoint):

```bash
# HOLD-GUSTAVO — preencher só no host/secret store, NÃO no git
export TELEGRAM_ALERTMANAGER_BOT_TOKEN='<BOT_TOKEN_FROM_BOTFATHER>'
export TELEGRAM_GRUPO_PIETRA_CHAT_ID='-<GROUP_CHAT_ID>'
export TELEGRAM_GRUPO_LGPD_CHAT_ID='-<GROUP_CHAT_ID_LGPD>'   # opcional se rota LGPD ativa
export TELEGRAM_GRUPO_N8N_CHAT_ID='-<GROUP_CHAT_ID_N8N>'     # opcional

# Opcional: se AM exposto só internamente
export ALERTMANAGER_URL='http://127.0.0.1:9093'
```

Exemplo de materialização em entrypoint (ilustrativo):

```bash
mkdir -p /etc/alertmanager/secrets
printf '%s' "$TELEGRAM_ALERTMANAGER_BOT_TOKEN" > /etc/alertmanager/secrets/telegram_bot_token
printf '%s' "$TELEGRAM_GRUPO_PIETRA_CHAT_ID" > /etc/alertmanager/secrets/telegram_grupo_pietra_chat_id
chmod 400 /etc/alertmanager/secrets/*
```

Docker Compose volume (placeholder):

```yaml
# NÃO commitar valores reais
services:
  alertmanager:
    image: prom/alertmanager:v0.27.0
    volumes:
      - ./infra/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_secrets:/etc/alertmanager/secrets:ro
    command:
      - --config.file=/etc/alertmanager/alertmanager.yml
      - --storage.path=/alertmanager
```

---

## 3. Obter chat id (sem vazar token no shell history)

```bash
# 1) Fale com o bot no privado OU adicione ao grupo e envie /start
# 2) Substitua TOKEN só em env, não em commit
TOKEN="***HOLD***"
curl -fsS "https://api.telegram.org/bot${TOKEN}/getUpdates" | jq '.result[].message.chat | {id, title, type}'
```

Grupos costumam ter `id` **negativo** (ex. `-100xxxxxxxxxx`).  
Guarde só o número no arquivo `*_chat_id`.

Teste manual do bot (opcional, fora do AM):

```bash
curl -fsS -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_GRUPO_PIETRA_CHAT_ID}" \
  -d "text=Cartorio AM smoke $(date -u +%Y-%m-%dT%H:%MZ)" \
  -d "parse_mode=HTML"
```

---

## 4. Receivers (já no repo — referência)

Trecho conceitual (espelha `infra/alertmanager/alertmanager.yml`; **não** duplicar secrets):

```yaml
receivers:
  - name: "telegram-grupo-pietra-p0"
    telegram_configs:
      - bot_token_file: "/etc/alertmanager/secrets/telegram_bot_token"
        chat_id_file: "/etc/alertmanager/secrets/telegram_grupo_pietra_chat_id"
        parse_mode: "HTML"
        send_resolved: true
        message: |
          🔴 <b>P0 ALERTA — {{ .CommonLabels.alertname }}</b>
          Squad: {{ .CommonLabels.squad }}
          {{ .CommonAnnotations.summary }}
```

Rotas:

| Match | Receiver | group_wait | repeat |
|-------|----------|------------|--------|
| `priority: P0` | `telegram-grupo-pietra-p0` | 10s | 1h |
| `priority: P1` | `telegram-grupo-pietra-p1` | 1m | 6h |
| `squad: cartorio-lgpd` | `telegram-grupo-lgpd` | 1m | 12h |
| `squad: cartorio-n8n` | `telegram-grupo-n8n` | 1m | (default) |
| default | `telegram-grupo-pietra-default` | 30s | 4h |

Labels esperadas nos alertas Prometheus: `priority` ∈ {P0,P1,P2}, `squad` ∈ {cartorio-lgpd, cartorio-n8n, cartorio-dev, cartorio-sre}.

---

## 5. Live fire — alerta de teste

### 5.1 Via API AlertManager (curl) — preferido em lab

Gera um alerta sintético **sem** precisar de regra Prometheus:

```bash
AM_URL="${ALERTMANAGER_URL:-http://127.0.0.1:9093}"
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ENDS=$(date -u -v+5M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '+5 minutes' +%Y-%m-%dT%H:%M:%SZ)

curl -fsS -X POST "${AM_URL}/api/v2/alerts" \
  -H 'Content-Type: application/json' \
  -d "[
    {
      \"labels\": {
        \"alertname\": \"CartorioAmTelegramLiveFireTest\",
        \"priority\": \"P0\",
        \"squad\": \"cartorio-sre\",
        \"severity\": \"test\",
        \"instance\": \"livefire-g7-18-t3\"
      },
      \"annotations\": {
        \"summary\": \"G7.18.T3 live fire — ignore if planned\",
        \"description\": \"Teste controlado AlertManager → Telegram. Pode resolver em ~5min.\",
        \"runbook\": \"docs/ALERTMANAGER_TELEGRAM_G7.md\"
      },
      \"startsAt\": \"${NOW}\",
      \"endsAt\": \"${ENDS}\"
    }
  ]"
```

Esperado:

1. HTTP 200 do AM.
2. Em ≤ `group_wait` (P0 = 10s) mensagem no grupo Pietra com 🔴 P0.
3. UI AM (`/#/alerts`) mostra o alerta firing.
4. Após `endsAt`, resolved (se `send_resolved: true`).

### 5.2 Via amtool

```bash
# Instalar: https://github.com/prometheus/alertmanager/releases (amtool)
export AMTOOL_ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://127.0.0.1:9093}"

# Config check
amtool check-config infra/alertmanager/alertmanager.yml

# Ver rotas (qual receiver pega o label set)
amtool config routes test \
  --config.file=infra/alertmanager/alertmanager.yml \
  priority=P0 squad=cartorio-sre alertname=CartorioAmTelegramLiveFireTest

# Listar alertas ativos
amtool alert query

# Silenciar teste acidental (se precisar)
amtool silence add alertname=CartorioAmTelegramLiveFireTest --duration=1h --comment='G7 livefire mute'
```

### 5.3 Via Prometheus rule (integração real)

1. Temporariamente adicionar rule com `expr: vector(1)` e labels `priority: P0` (só em staging).
2. `POST /-/reload` no Prometheus.
3. Aguardar `for:` da rule.
4. Remover rule e reload — **não deixar vector(1) em prod**.

---

## 6. Troubleshooting

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| AM 200 mas sem Telegram | token/chat_id file vazio ou path errado | `docker exec` cat paths (sem logar token no chat) |
| `telegram: unauthorized` | token revogado | regenerar no BotFather |
| `chat not found` | bot não está no grupo / chat id errado | re-add bot; `getUpdates` |
| Alerta some na rota errada | labels `priority`/`squad` ausentes | ajustar `alerts.yml` |
| Spam de repeats | `repeat_interval` curto + alerta não resolve | silence + corrigir expr |
| HTML parse error no TG | `<` `>` crus na annotation | escapar ou simplificar template |

Logs AM:

```bash
docker logs cartorio-alertmanager --tail 100 2>&1 | grep -i telegram
# ou nome real do serviço no swarm
```

---

## 7. Checklist deploy (HOLD-GUSTAVO)

- [ ] Bot criado; token só em secret store
- [ ] Chat ids Pietra (+ LGPD/N8N se usar rotas)
- [ ] Files montados nos paths do YAML
- [ ] `amtool check-config` OK
- [ ] Prometheus → AM connectivity OK
- [ ] Live fire §5.1 em janela acordada (avisar grupo)
- [ ] Confirmar mensagem P0 + resolved
- [ ] Remover alerta de teste / silence se residual
- [ ] **Não** colar token em issue/PR/commit

---

## 8. Relação com outros canais de alerta

| Canal | Doc | Sobreposição |
|-------|-----|--------------|
| Uptime Kuma → Telegram | `infra/monitoring/uptime-kuma/telegram-alerts.md` | Uptime de HTTP externo; AM = métricas/SLO Prometheus |
| N8N workflow alertas | `infra/n8n-workflows/` (ex. 26-alerta-critico) | Workflow-level; não substitui AM |
| Sentry | app `before_send` scrubber | Erros app; PII scrubbed |

Evitar 3 bots diferentes no mesmo grupo sem prefixo claro (P0 AM vs Kuma DOWN). Preferir o mesmo bot com mensagens prefixadas **ou** tópicos/grupos separados.

---

## 9. Segurança / LGPD

- Templates **não** devem incluir labels com CPF, telefone, email de cliente.
- Preferir `instance`, `alertname`, `squad`, summaries técnicos.
- Token Telegram = secret classe alta (equivale a postar em nome do bot).

**Modified by Gustavo Almeida — G7 Wave 27 cartorio-sre**
