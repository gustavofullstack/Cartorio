# SUPER GOALS G8 — Integração Total & Hardening Extremo Cartório
**Versão:** G8.0 — 2026-07-17
**Meta única:** Stack 100% integrado e resiliente em produção (FastAPI, Telegram, Chatwoot, LobeChat, Redis, Postgres/Supabase, MCPs, WebSockets, Webhooks, Tailscale, Traefik/Cloudflare DNS, OpenClaw Agent, Tools & Skills, CI/CD, Observability) com qualidade SOLID/DRY/KISS, tipagem forte e cobertura de testes de 96%+.

---

## META (North Star)

> **Até 2026-08-15:** Fechamento de todas as 100 tasks em 25 squads no ambiente local e preparação de go-live completo sem nenhum gap P0 em homologação e produção, com cobertura total global de testes ≥96%, verificação rigorosa de RLS/LGPD no banco, e estabilidade de 72 horas em produção comprovada por monitoramento de radar.

---

## GOALS SUPER ROBUSTOS (G8.1 – G8.12)

| ID | Goal | % Inicial | Target | Evidence / Verification Method |
|----|------|-----------|--------|--------------------------------|
| **G8.1** | **API Core & WS Hardening** | 90% | 100% | Testes de concorrência com 100+ WebSocket streams e controle de buffering de logs. |
| **G8.2** | **Telegram Multi-Turn Resilience** | 80% | 100% | Redis Dialog History com limite dinâmico de tokens ativo e validado em 10 cenários complexos. |
| **G8.3** | **Chatwoot HITL Handoff** | 70% | 100% | Desativação instantânea do bot no Redis e transição automática ao atendente via webhook Chatwoot. |
| **G8.4** | **LobeChat & OpenClaw Sync** | 75% | 100% | Roteamento dinâmico via Traefik e sincronização automática de prompts sistêmicos. |
| **G8.5** | **Redis Caching & Idempotency** | 90% | 100% | Políticas de expiração (TTL) e eviction e hash nos CPFs de chaves no Redis. |
| **G8.6** | **Database & RLS Compliance** | 85% | 100% | Índices otimizados, dumps automatizados com criptografia e RLS verificado em 100% das tabelas. |
| **G8.7** | **MCP Tools & Interceptors** | 90% | 100% | Cobertura total de testes mockados das tools MCP e interceptor de PII de saída. |
| **G8.8** | **Webhooks, DLQ & Expiry** | 85% | 100% | DLQ estruturado com TTL de descarte de falhas velhas e criptografia de payloads armazenados. |
| **G8.9** | **Tailscale VPN & MagicDNS Security** | 70% | 100% | Probe de latência interna e MagicDNS limitando acessos de dados a canais de rede privados. |
| **G8.10** | **Traefik Proxy & DNS Verification** | 80% | 100% | Script integrado de verificação automática do status do DNS no Cloudflare e logs do Traefik limpos de PII. |
| **G8.11** | **SOLID Architecture & Quality Code** | 88% | 100% | Camada de controle sem lógica de negócio e acoplamento desacoplado avaliado. |
| **G8.12** | **CI/CD, Radar & 72h Stability** | 90% | 100% | Pipeline CI verde com cobertura ≥96% e 72 horas contínuas de estabilidade sem quedas no radar. |

---

## SUPER OBJETIVO (Scrum / MVP)

| Sprint | Foco | Done when |
|--------|------|-----------|
| **G8-S1** | WS concorrência + Telegram Multi-turn | 100 conexões WS simultâneas sem queda e histórico dinâmico ativo. |
| **G8-S2** | Chatwoot HITL + OpenClaw/LobeChat | Webhook Chatwoot corta bot e redireciona mensagens ao escrevente. |
| **G8-S3** | Redis, Postgres & RLS Hardening | Banco de dados otimizado e RLS validado em 100% das tabelas com PII. |
| **G8-S4** | MCP, Webhooks & DLQ Cripto | DLQ criptografado e interceptor MCP filtrando CPFs. |
| **G8-S5** | Tailscale, DNS, Traefik & CI/CD | Rotas estritamente privadas via Tailscale e verificação de DNS automatizada no CI. |
| **G8-S6** | SOLID, DRY/KISS, Tipagem Forte | Refatoração de controllers para services, mypy strict 100% e Pydantic strict. |
| **G8-S7** | Radar, Postman & Swagger Sync | Coleção Postman sincronizada via script e radar expandido em 100% de status. |
| **G8-S8** | PII Scrubbing, Audit Chain & Emolumentos | Recálculo de hashes da cadeia e precisão matemática de emolumentos MG 2026. |
| **G8-S9** | Validador G8 e 72h de Estabilidade | Scripts de validação final executando verde e 72h de uptime provado. |

---

## DEFINITION OF READY / DONE (canônico)

**Documento completo (DoR + DoD + honesty gate):** [`docs/G8_DOR_DOD.md`](docs/G8_DOR_DOD.md)  
Precedente G7: [`docs/G7_DOR_DOD.md`](docs/G7_DOR_DOD.md) · Plano: [`SUPER_PLANO_G8_100_TASKS.md`](SUPER_PLANO_G8_100_TASKS.md)

### Honesty gate (resumo)

`[x]` / % / “wave COMPLETED” **só** com evidência: **artefato (código|docs) + testes/verificação PASS + lesson ou PROGRESS honesto**.  
Orquestrador paper-tick (Lesson 216) **não** conta. HOLD-SUI = `[~]`, não fake green.

### DoD por task / wave (checklist rápido)

Cada wave de 4 tarefas **só é declarada DONE** se:

1. **Linting**: `uv run ruff check app/` (ou `make lint`) sem erros na superfície tocada.
2. **Tipagem**: `uv run mypy app/` sem falhas novas (se tocou `app/`).
3. **Testes**: pytest da área **PASS** com comando reproduzível (preferir `unset PYTHONPATH` + venv backend — Lesson 219).
4. **Sem vazamento de segredos**: scanner/review; zero secrets no diff.
5. **Progresso honesto**: append em `PROGRESS.md` com IDs + paths + N passed + `Modified by Gustavo Almeida` — **proibido** bloco COMPLETED sem evidência.
6. **Lesson**: `.harness/memory/lesson-XXX-…md` em mudanças críticas / multi-rein / anti-pattern.
7. **Plano**: `SUPER_PLANO_G8_100_TASKS.md` checkbox `[x]` **somente** após 1–6.

Detalhe, DoR, anti-padrões e DoD por goal G8.1–G8.12 → **[`docs/G8_DOR_DOD.md`](docs/G8_DOR_DOD.md)**.

## SUPER PROGRESSO (honestidade — Wave 35–37 · 2026-07-17)

| Métrica | Valor |
|---|---|
| Tasks G8 evidenced | **23/100** (Wave 35–37 REAL) |
| % progress honesto | **23%** |
| Wave 32 | G8.05.T1 · G8.06.T1 (Lesson 217 — Redis TTL + DB indexes) |
| Wave 33 | G8.07.T2 · G8.07.T3 · G8.05.T2 · G8.01.T4 (test_g8_wave33 + Lesson 216) |
| Tests Wave 32+33 | 27 + 43 + 13 + 21 = **104 passed** |
| Wave 37 | G8.02.T3 debounce · G8.05.T4 idempotency stress · G8.16.T2 DoR/DoD |
| G8 suite (local) | **156 passed**, 1 skipped (subset waves 33–37) |
| G7 residual SUI | 8 [~] |
| Prod radar | red (SUI) |


---

**Modified by Gustavo Almeida + Antigravity AI orquestrador — 2026-07-17**  
(SUPER_GOALS_G8.md estruturado e pronto para execução)  
**G8.16.T2:** DoR/DoD canônico em [`docs/G8_DOR_DOD.md`](docs/G8_DOR_DOD.md) — Modified by Gustavo Almeida
