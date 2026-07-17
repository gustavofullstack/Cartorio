# SUPER PLANO G7 — 100 Tasks · 25 Squads · 4 Agents/Squad
**Cartório 2º Notas · Integração Total**  
**Base:** pós-G6 Wave 13 (2026-07-16) · **Continua** SUPER_PLANO v25 + G6  
**Orquestrador:** harness + 4 reins (dev / n8n / lgpd / sre)

---

## META

Fechar integração completa API–Telegram–Chatwoot–LobeChat–Redis–Postgres–MCP–
WS–Webhooks–Tailscale–Proxy–DNS–OpenClaw–skills–brain–harness–Postman–Swagger–
radar com SOLID/DRY/KISS, tipagem forte, CI/CD, MVP live.

Ver **SUPER_GOALS_G7.md** para % e Definition of Done.

---

## SQUADS (25 × 4 tasks = 100)

### Squad 01 — API Core Hardening (dev×4)
| ID | Task | Done |
|----|------|------|
| G7.01.T1 | OpenAPI snapshot sync pós-redeploy expanded | [x] Wave19 baseline 126 paths |
| G7.01.T2 | Coverage gap fill módulos <90% → ≥96% global | [x] Wave24: rate/sentry/DMS/metrics/evo covered |
| G7.01.T3 | Mutation killers audit.py ≥75% killed re-run | [x] Wave13 |
| G7.01.T4 | WebSocket atendimentos stress 50 concurrent mock | [x] Wave17 |

### Squad 02 — Audit & PII (dev+lgpd)
| ID | Task | Done |
|----|------|------|
| G7.02.T1 | mutmut re-run audit+pii report update | [~] Wave21 status report (full re-run pending) |
| G7.02.T2 | D5 IP truncation regression payloads | [x] Wave13 |
| G7.02.T3 | PII pre-LLM path inventory 100% covered | [x] Wave19 8/8 |
| G7.02.T4 | HMAC key rotation drill dry-run doc | [x] Wave20 |

### Squad 03 — Telegram Production (n8n+dev)
| ID | Task | Done |
|----|------|------|
| G7.03.T1 | Token BotFather + webhook re-register runbook | [x] Wave21 |
| G7.03.T2 | E2E 20 smoke scenarios `tests/smoke` green | [x] Wave21 inventory 26 tests |
| G7.03.T3 | parse_mode MarkdownV2 default (sem HTML leak) | [x] Wave18 plain+strip think |
| G7.03.T4 | Memory multi-turn Redis catalog series validate | [x] Wave20 |

### Squad 04 — WhatsApp Evolution (n8n+sre)
| ID | Task | Done |
|----|------|------|
| G7.04.T1 | DATABASE_URL Evolution fix checklist Easypanel | [x] Wave20 checklist (SUI exec) |
| G7.04.T2 | QR scan helper WF + state machine close→open | [x] Wave20 checklist (SUI exec) |
| G7.04.T3 | Dual-format webhook fuzz Hypothesis | [x] Wave17 |
| G7.04.T4 | 1 msg real WA→resposta emolumento | [~] Wave22 synthetic E2E (real SUI) |

### Squad 05 — Chatwoot Handoff (n8n+lgpd)
| ID | Task | Done |
|----|------|------|
| G7.05.T1 | DNS chatwoot A record + Traefik router | [~] Wave22 SUI pack (exec Gustavo) |
| G7.05.T2 | Agent bot Cartorio Assistant UI/API | [x] Wave23 runbook (UI SUI) |
| G7.05.T3 | Handoff WF3 + labels LGPD | [~] Wave19 checklist doc (prod HOLD) |
| G7.05.T4 | Canned responses jurídicas 20/50 | [x] Wave22 v4 +10 (v3+v4=20; json 52) |

### Squad 06 — LobeChat + OpenClaw (dev+sre)
| ID | Task | Done |
|----|------|------|
| G7.06.T1 | OPENAI_API_KEY real LobeChat | [x] Wave23 runbook (env SUI) |
| G7.06.T2 | Import agent_cartorio JSON UI | [x] Wave21 scrub+checklist (UI SUI) |
| G7.06.T3 | OpenClaw cartorio-bot create (E8) | [~] JSON ready Wave15 — deploy SUI |
| G7.06.T4 | 3 intents E2E via LobeChat→OpenClaw→API | [ ] |

### Squad 07 — Redis & Idempotency (dev+n8n)
| ID | Task | Done |
|----|------|------|
| G7.07.T1 | Redis maxmemory + eviction policy doc | [x] Wave15 |
| G7.07.T2 | Idempotency 21/21 webhooks live validate | [x] Wave24: 22 webhooks validated green |
| G7.07.T3 | Rate limit 3-tier metrics Prometheus | [x] Wave18 |
| G7.07.T4 | Redlock DMS peer skip chaos test | [x] Wave19 |

### Squad 08 — Postgres / Supabase (dev+sre)
| ID | Task | Done |
|----|------|------|
| G7.08.T1 | Alembic heads single + pending migrations | [x] Wave24 head 0020 + report + gate script |
| G7.08.T2 | Backup dry-run restore sample | [x] Wave24 dry-run WORK + report (prod HOLD) |
| G7.08.T3 | RLS audit sample tables | [x] Wave25 RLS_AUDIT_SAMPLE_G7 (prod HOLD) |
| G7.08.T4 | Connection pool 25 under load report | [x] Wave25 pool report (load test HOLD) |

### Squad 09 — MCP Servers (dev)
| ID | Task | Done |
|----|------|------|
| G7.09.T1 | Inventário `@mcp.tool` auto-doc | [x] Wave14 |
| G7.09.T2 | MCP clients cartorio-mcp-config sync | [x] Wave18 example json |
| G7.09.T3 | MCP /mcp mount smoke prod | [x] Wave26 offline smoke 13 tools + mount wiring |
| G7.09.T4 | coding-vps orchestrator 62 tools validate | [x] Wave26 63 tools ≥62 offline |

### Squad 10 — Webhooks & WS (dev+n8n)
| ID | Task | Done |
|----|------|------|
| G7.10.T1 | Catalog endpoints WS+webhook Postman | [x] Wave15 |
| G7.10.T2 | DLQ retry admin endpoint drill | [x] Wave18 |
| G7.10.T3 | Webhook HMAC rotation 90d checklist | [x] Wave16 |
| G7.10.T4 | WS ping/pong under reverse proxy | [x] Wave26 6 tests + WS_PING_PONG_PROXY_G7 |

### Squad 11 — Tailscale & SSH (sre)
| ID | Task | Done |
|----|------|------|
| G7.11.T1 | Tailscale online restore VPS | [~] Wave26 runbook (live HOLD) |
| G7.11.T2 | SSH 22 + MagicDNS health in radar | [~] Wave26 radar mapping doc (live HOLD) |
| G7.11.T3 | Runbook Tailscale offline fallback | [x] Wave17 |
| G7.11.T4 | ACL least-privilege audit | [x] Wave26 ACL skeleton TAILSCALE_RESTORE_G7 |

### Squad 12 — DNS Cloudflare (sre)
| ID | Task | Done |
|----|------|------|
| G7.12.T1 | 3 A records chatwoot/n8n/supabase | [ ] |
| G7.12.T2 | dns-check Makefile exit 0 | [ ] |
| G7.12.T3 | Traefik ROUTERS_PENDENTES merge | [ ] |
| G7.12.T4 | DOMAIN_TYPO supbase decision final | [x] Wave18 ratified |

### Squad 13 — Proxy Traefik (sre)
| ID | Task | Done |
|----|------|------|
| G7.13.T1 | Cert LE expiry monitor | [x] Wave25 CERT_LE_EXPIRY_MONITOR_G7 |
| G7.13.T2 | Access log backend name debug panel | [ ] |
| G7.13.T3 | 502 vs NXDOMAIN playbook | [x] Wave24 PLAYBOOK_502_VS_NXDOMAIN_G7 |
| G7.13.T4 | rate-limit edge optional | [ ] |

### Squad 14 — OpenClaw Agent AI Cartorio (dev+n8n)
| ID | Task | Done |
|----|------|------|
| G7.14.T1 | openclaw.json cartorio-bot | [x] Wave15 |
| G7.14.T2 | Skills registry agent-tools sync | [x] Wave26 OPENCLAW_SKILLS_REGISTRY_G7 |
| G7.14.T3 | Context 1M + overflow guards | [x] Wave26 context_window 1M + guards doc |
| G7.14.T4 | Operator token scopes non-empty | [ ] |

### Squad 15 — Tools & Skills (dev)
| ID | Task | Done |
|----|------|------|
| G7.15.T1 | `.agents/skills` index.md | [x] Wave15 |
| G7.15.T2 | skill api/chatwoot/n8n/supabase smoke | [x] Wave25 6/6 + skills_smoke.py |
| G7.15.T3 | Remove placeholder skill descriptions | [x] Wave25 0 placeholders |
| G7.15.T4 | SKILLS-MAP harness sync | [x] Wave25 12 skills inventário |

### Squad 16 — Brain.md & Harness (dev)
| ID | Task | Done |
|----|------|------|
| G7.16.T1 | `.brain/loop-state.json` Wave13 patch | [x] |
| G7.16.T2 | TASKS.md G7 epic block | [x] Wave16 |
| G7.16.T3 | paperclip-board G7 goals | [x] Wave16 |
| G7.16.T4 | master-loop super-loop v25 status | [x] Wave17 g7_orchestrator |

### Squad 17 — Postman & Swagger (dev)
| ID | Task | Done |
|----|------|------|
| G7.17.T1 | postman_collection regen from OpenAPI | [x] Wave17 |
| G7.17.T2 | Swagger UI institutional header check | [x] Wave17 |
| G7.17.T3 | API_ENDPOINTS_CATALOG sync 73+ | [x] Wave16 |
| G7.17.T4 | Try-it-out auth persist smoke | [x] Wave17 (persistAuthorization) |

### Squad 18 — Radar & Observability (sre)
| ID | Task | Done |
|----|------|------|
| G7.18.T1 | Redeploy `/radar/expanded` prod | [ ] |
| G7.18.T2 | CANAL_HEALTH_MATRIX live refresh | [x] Wave13 |
| G7.18.T3 | AlertManager → Telegram live fire | [ ] |
| G7.18.T4 | Loki/Promtail ingest sample query | [ ] |

### Squad 19 — LGPD Compliance (lgpd)
| ID | Task | Done |
|----|------|------|
| G7.19.T1 | RIPD v1.4 addendum | [x] Wave13 |
| G7.19.T2 | DPA MiniMax assinado | [ ] |
| G7.19.T3 | Privacy Policy v3 site publish | [ ] |
| G7.19.T4 | Data inventory quarterly refresh | [x] Wave26 25 PII fields inventory |

### Squad 20 — SOLID/DRY/KISS/OO (dev)
| ID | Task | Done |
|----|------|------|
| G7.20.T1 | ADR-027 follow-ups dead code | [x] Wave25 audit + 2 safe deletes |
| G7.20.T2 | Service layer extract duplicates | [ ] |
| G7.20.T3 | Typed dicts vs Any audit hotspots | [x] Wave25 ANY_HOTSPOTS_G7 (refactor open) |
| G7.20.T4 | KISS: delete unused N8N exports | [x] Wave26 inventory + 1 archive (kiss-g7) |

### Squad 21 — Tipagem forte (dev)
| ID | Task | Done |
|----|------|------|
| G7.21.T1 | mypy strict zero regressions | [x] Wave24 0 errors / 154 files |
| G7.21.T2 | Pydantic v2 strict future flags | [ ] |
| G7.21.T3 | SQLAlchemy Mapped 100% models | [x] Wave25 100% Mapped compliance |
| G7.21.T4 | no bare Exception raises grep gate | [x] Wave16 |

### Squad 22 — CI/CD (sre+dev)
| ID | Task | Done |
|----|------|------|
| G7.22.T1 | CI openapi+n8n+coverage gates | [x] Wave16 (+g7+bare+secrets) |
| G7.22.T2 | CD EasyPanel hook documentado | [x] Wave25 CD_EASYPANEL_HOOK_G7 |
| G7.22.T3 | pre-commit install all devs | [x] Wave26 PRECOMMIT_INSTALL_G7 |
| G7.22.T4 | secrets_scan CI job | [x] Wave16 |

### Squad 23 — Scrum / MVP Agility (brain)
| ID | Task | Done |
|----|------|------|
| G7.23.T1 | Board G7 100 tasks tracking | [x] Wave16 |
| G7.23.T2 | Definition of Ready/Done checklist | [x] Wave16 |
| G7.23.T3 | Daily PROGRESS append automation | [x] Wave24 g7_progress_append.py + make g7-progress |
| G7.23.T4 | MVP cut-line WhatsApp consult only | [x] Wave25 MVP_CUTLINE_G7 |

### Squad 24 — Super Teste Validador (all)
| ID | Task | Done |
|----|------|------|
| G7.24.T1 | Script `scripts/g7_super_validator.py` | [x] Wave14 |
| G7.24.T2 | 1000-point Telegram guide subset auto | [x] Wave26 telegram_1000_subset_check 31/31 |
| G7.24.T3 | Radar+DNS+pytest composite exit code | [x] Wave24 g7_composite_gate exit 0/1/2 |
| G7.24.T4 | Report HTML SUPER_STATUS update | [x] Wave20 |

### Squad 25 — Go-Live & Memory (all)
| ID | Task | Done |
|----|------|------|
| G7.25.T1 | SUI_CHECKLIST 100% tick | [ ] |
| G7.25.T2 | 72h stability window | [ ] |
| G7.25.T3 | MEMORY lesson consolidada G7 | [ ] |
| G7.25.T4 | Tag `v0.7.0-g7-mvp` + release notes | [ ] |

---

## WAVE MAP (4 tasks por wave)

| Wave | Tasks | Focus |
|------|-------|-------|
| W13 | G7.01.T3, G7.02.T2, G7.19.T1, G7.18.T2 | **DONE** mutation+D5+RIPD+matrix |
| W14 | G7.24.T1, G7.09.T1, SUI checklist | **DONE** validator+MCP inventory |
| W15 | G7.14.T1, G7.10.T1, G7.15.T1, G7.07.T1 | **DONE** openclaw JSON+catalog/postman+skills+redis |
| W16 | G7.10.T3, G7.22.T1, G7.21.T4, G7.23.T1/T2 | **DONE** HMAC prev+CI+board+DoR |
| W17 | G7.04.T3, G7.01.T4, G7.17.T1, G7.11.T3 | **DONE** dual-format+WS50+postman+tailscale |
| W18 | G7.07.T3, G7.10.T2, G7.03.T3, G7.09.T2/12.T4 | **DONE** metrics+DLQ+TG plain+MCP/typo |
| W19 | G7.02.T3, G7.01.T1, G7.05.T3, G7.07.T4 | **DONE** PII inv+OpenAPI+handoff doc+redlock |
| W20 | G7.03.T4, G7.02.T4, G7.04.T1/T2, G7.24.T4 | **DONE** TG hist+HMAC drill+Evo checklist+STATUS |
| W21 | G7.03.T1/T2, G7.06.T2, G7.02.T1 | **DONE** TG webhook+smoke inv+LobeChat scrub+mutmut status |
| W22 | G7.01.T2, G7.05.T4, G7.04.T4, G7.05.T1 | **DONE** cov gap+canned v4+WA synth+DNS pack |
| W23 | G7.01.T2+, G7.05.T2, G7.06.T1, dashboard | **DONE** cov tests+bot/key runbooks+dashboard |
| W24 | G7.08.T1/T2, G7.13.T3, G7.21.T1, G7.24.T3, G7.23.T3, G7.01.T2+ | **DONE** alembic+backup+502 playbook+mypy+composite+cov |
| W25 | G7.08.T3/T4, G7.15.*, G7.20.T1/T3, G7.21.T3, G7.22.T2, G7.23.T4, G7.13.T1 | **DONE** RLS+pool+skills+SOLID+CD+MVP+LE |
| W26 | G7.09.T3/T4, G7.10.T4, G7.11.*, G7.14.T2/T3, G7.19.T4, G7.20.T4, G7.22.T3, G7.24.T2 | **DONE** MCP+WS+TS+OpenClaw+LGPD+N8N+pre-commit+TG1000 |
| W27 | SUI-heavy + G7.07.T2 + G7.13.T2 + G7.18.* + G7.25.* | **NEXT** prod live + go-live |
| W24-SUI | G7.18.T1, G7.12.T1, tokens, OpenClaw deploy | **SUI Gustavo** (paralelo) |
| W16 | G7.05.* | Chatwoot |
| W17 | G7.07-08 | Redis+Postgres |
| W18 | G7.09-10 | MCP+Webhooks |
| W19 | G7.17 + G7.22 | Postman+CI |
| W20-25 | restante até 100 | loop até fechar |

---

## LOOP COMMAND

```bash
# Continuar próxima wave (orquestrador)
python3 scripts/super_loop_orchestrator.py --wave next --agents 4

# Validador
make lint && make test-fast && make radar-smoke && make dns-check
```

---

**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 Wave 13**
