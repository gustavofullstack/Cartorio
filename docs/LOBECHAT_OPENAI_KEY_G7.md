# LobeChat OPENAI_API_KEY (G7.06.T1)

**Problema:** LobeChat UP com `OPENAI_API_KEY=sk-xxxx` placeholder → UI desiste / 401.  
**Alvo:** apontar para OpenClaw OpenAI-compatible em `https://agent.2notasudi.com.br/v1`.

---

## Env EasyPanel (LobeChat service)

| Variável | Valor |
|----------|--------|
| `OPENAI_API_KEY` | token/password OpenClaw operator (Bearer) |
| `OPENAI_PROXY_URL` ou `OPENAI_BASE_URL` | `https://agent.2notasudi.com.br/v1` |
| Modelos | `openclaw`, `openclaw/main` |

Import agent: `infra/lobechat/agent_cartorio_import.json`  
(`apiKey` no JSON = placeholder `${OPENCLAW_GATEWAY_TOKEN_OR_PASSWORD}` — Wave 21 scrub)

---

## Passos Gustavo (~5 min)

1. EasyPanel → LobeChat → Environment  
2. Substituir `sk-xxxx` pela key real do OpenClaw  
3. Base URL → agent.2notasudi.com.br/v1  
4. Redeploy LobeChat  
5. Import agent JSON se ainda não importado  
6. Teste: “quanto custa procuração” (não inventar valor)

---

## Monitores

Ver `infra/lobechat/monitors.json`:
- `lobechat-http-prod` → `/api/health`
- fallback EasyPanel host
- Telegram alert se DOWN

```bash
# Probe
curl -sS -o /dev/null -w '%{http_code}\n' https://agent.2notasudi.com.br/health
curl -sS -o /dev/null -w '%{http_code}\n' https://lobe.2notasudi.com.br/api/health || true
```

Cross-ref: Lesson 170 (CORS) · 178 (snapshot) · `docs/LOBCHAT_OPENCLAW_IMPORT_G7.md`

**Modified by Gustavo Almeida — G7 Wave 23**
