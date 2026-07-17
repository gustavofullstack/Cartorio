# LobeChat + OpenClaw Import Checklist (G7.06.T1/T2/T3)

**Artifacts**

| Item | Path |
|------|------|
| Agent import JSON | `infra/lobechat/agent_cartorio_import.json` |
| OpenClaw bot config | `infra/openclaw/cartorio-bot.openclaw.json` |
| STATUS snapshot | `infra/lobechat/STATUS.md` |
| E6 spec | `docs/openclaw/E6-cartorio-bot-spec.md` |

---

## Segurança (Wave 21)

- `apiKey` no import JSON deve ser **placeholder** `${OPENCLAW_GATEWAY_TOKEN_OR_PASSWORD}`  
  (**corrigido** se havia senha literal commitada — rotacionar se exposta).
- Preencher key só no UI EasyPanel / LobeChat, nunca no git.

---

## G7.06.T1 — LobeChat env

| Var | Valor |
|-----|--------|
| `OPENAI_API_KEY` | operator/token OpenClaw real (não `sk-xxxx`) |
| `OPENAI_PROXY_URL` / custom base | `https://agent.2notasudi.com.br/v1` |
| Model list | `openclaw`, `openclaw/main` |

## G7.06.T2 — Import UI

1. Abrir LobeChat (`agent.2notasudi.com.br` ou URL EasyPanel)
2. Import agents → selecionar `agent_cartorio_import.json`
3. Conferir provider baseURL → OpenClaw
4. Teste: mensagem "quanto custa procuração" → deve chamar API (não inventar)

## G7.06.T3 — OpenClaw cartorio-bot

1. Operator token com scopes `operator.read|write` (Lesson 177: scopes=[] bloqueia create)
2. Montar `cartorio-bot.openclaw.json` em `/home/node/.openclaw/`
3. `agents.list` deve incluir `cartorio-bot`
4. CORS já aceita `.2notasudi.com.br` (Lesson 170)

---

## Validação local (sem UI)

```bash
python3 -c "import json; json.load(open('infra/lobechat/agent_cartorio_import.json'))"
python3 -c "import json; d=json.load(open('infra/openclaw/cartorio-bot.openclaw.json')); assert d['name']=='cartorio-bot'"
# no secrets
rg -n 'sk-|@Techno|password.*=.*[A-Za-z0-9]{12}' infra/lobechat/ infra/openclaw/ || true
```

---

**Modified by Gustavo Almeida — G7 Wave 21**
