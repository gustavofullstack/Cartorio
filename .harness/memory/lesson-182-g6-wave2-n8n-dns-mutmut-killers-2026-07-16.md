# Lesson 182 — G6 Wave 2: N8N INDEX + DNS checker + mutmut killers (2026-07-16)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com 4 agents/squad em loop. Reality check (skill `prompt-cartorio` v3.0.0 + AGENTS.md):

- Regra do projeto: **1-2 agents maximo em paralelo** (proibido 3+)
- Loop Gustavo (Pietra/Mavis) já criou `backend/tests/test_coverage_gap_fill.py` entre wave 1 e 2
- Plan v25 (F0-F6) já DONE; estamos em **CICLO G6** (pós-F6)

## Entregas Wave 2 (4 commits pushed, 4 G6 tasks DONE)

### `53fd1f6` — `fix(quality): ruff 0 errors + coverage gap fill tests`
- ruff --fix 4 F401 em `tests/smoke/test_evolution_5x.py` (json, SessionLocal, WebhookEvent)
- arquivo novo `tests/test_coverage_gap_fill.py` (3/3 pass, auto-gerado pelo loop Gustavo)
- pytest 2871 → 2871 (mantido)

### `1610d34` — `feat(n8n): INDEX auto-gerado registry 33 WFs (G6.B.T5)`
- `infra/n8n-workflows/INDEX.md`: tabela markdown com 33 WFs (27 ativos, 261 nodes)
- `scripts/n8n_index_gen.py`: regenerador (parsea JSON, extrai name/active/nodes/triggers)
- Stats: webhook trigger mais comum (16 WFs), 9 squads donos, 82% ativos
- pytest 2896 (subiu +25 entre waves, Gustavo loop adicionando)

### `73cb6f2` — `feat(dns): Python DNS health check + report consolidado (G6.D.T5)`
- `scripts/dns_health_check.py`: cross-resolver check (1.1.1.1 + 8.8.8.8 via system)
  - **GOTCHA AF_INET**: `socket.getaddrinfo` default retorna IPv6 primeiro (Happy Eyeballs) — forçar `family=AF_INET` para IPv4 only
- `infra/dns/DNS_HEALTH_REPORT.md`: snapshot 2026-07-16 14:15 BRT
  - 7/10 OK: api/flow/whatsapp/chat/agent/supbase/easypanel
  - 3/10 NXDOMAIN: chatwoot/n8n/supabase (HOLD-GUSTAVO-UI, ~5min)
- Runbook completo em `infra/dns/CLOUDFLARE_RUNBOOK.md` (já existia)

### `99988cf` — `test(audit): 16 mutation killers para audit.py (G6.A.T1.1)`
- Baseline mutmut 2026-07-16: audit.py tinha **42/42 mutantes sobreviventes** (0% killed)
- 16 testes novos que matam 30+ mutantes:
  - 3 canonical block format (sort_keys, separators, zero-fill)
  - 3 compute hash (SHA256, deterministic, prev_hash influence)
  - 2 HMAC (uses settings.audit_hmac_key, messages different)
  - 3 verify_chain (detecta tamper hash, detecta tamper payload, chain intacta)
  - 5 log (chain increments, HMAC inclui actor/action, IPv4 /24, IPv6 /32, actor_type default)
- pytest 2912 (+16 vs wave 1 final)
- **GOTCHA verify_chain retorna tuple(bool, int)**, não dict — primeiros testes falharam por isso

## Métricas finais Wave 2

| Métrica | Wave 1 final | Wave 2 final | Delta |
|---|---|---|---|
| pytest | 2868 | **2912** | +44 |
| mypy | 0 | **0** | mantido |
| ruff | 0 | **0** | mantido |
| coverage | 95% | **95%** (estimado) | mantido |
| lessons | 181 | **182** | +1 |
| unpushed | 0 | **0** | mantido |
| commits today | 4 | **8** | +4 |

## SUI (Só Gustavo Resolve) — 6 ações pendentes

1. **🔴 Cloudflare UI**: criar 3 A records `chatwoot/n8n/supabase.2notasudi.com.br → 187.77.236.77` (proxy ON) — ~5min total
2. **Easypanel UI**: atualizar 3 env vars `DATABASE_URL` em evolution-api/chatwoot/n8n (credenciais admin/supabase)
3. **Telegram BotFather**: regenerar token @TestCartorioBot + atualizar `.secrets/telegram.env`
4. **LobeChat UI**: substituir OPENAI_API_KEY placeholder por chave real
5. **Traefik**: mergear `infra/traefik/ROUTERS_PENDENTES.yaml` (3 routers)
6. **OpenClaw E8**: SSH VPS Hostinger + criar `cartorio-bot` em `/home/node/.openclaw/openclaw.json`

Após SUI 1-2: `make dns-check` + health prod deve mostrar **10/10 OK** + 3 env vars corrigidas.

## Próxima wave (G6 Wave 3 — após Gustavo executar SUI 1-2)

Tasks candidatas (2 agents paralelos max, sequencial o resto):
- **G6.B.T1** workflow validator CI (`scripts/n8n_workflow_validator.py` gate merge)
- **G6.C.T5** Privacy Policy v3 (LiteLLM + MiniMax sub-processors)
- **G6.A.T5** coverage fail-safe script Makefile (gate ≥96%)
- **G6.D.T1** health check expandido `/api/v1/health/radar` (10 domínios JSON)

## Refs

- commits: `53fd1f6`, `1610d34`, `73cb6f2`, `99988cf`
- artefatos: `infra/n8n-workflows/INDEX.md`, `scripts/n8n_index_gen.py`, `scripts/dns_health_check.py`, `infra/dns/DNS_HEALTH_REPORT.md`, `backend/tests/test_audit_mutmut_killers_g6.py`
- report anterior: `docs/MUTMUT_REPORT_G6.md`
- plano G6: `SUPER_PLANO_G6_CONSOLIDACAO.md`

Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 14:25 BRT
