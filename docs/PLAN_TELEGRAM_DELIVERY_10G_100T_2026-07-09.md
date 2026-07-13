# Plano — Entrega Bot Telegram (validacao) → WhatsApp depois

**Data:** 2026-07-09  
**Foco 100%:** Telegram test delivery  
**Depois:** WhatsApp (Evolution)  
**Agents cmux:** Antigravity-Gemini-3.5-High · OpenCode-MiniMax-M3-High · Grok-Build-Grok-4.5-High · Claude-Code-MiniMax-M3-High  
**Repo/branch:** Cartorio / master (mesmo MacBook Pro)

---

## Estado atual (evidencia 2026-07-09)

| Item | Status | Evidencia |
|------|--------|-----------|
| API health | OK v0.6.0 | `GET /health` |
| Webhook Telegram | LIVE | `api.2notasudi.com.br/api/v1/telegram/webhook`, pending=0, sem last_error |
| Bot | @test_cartorio_bot | getMe 200 |
| Comandos canonicos | 7 | start menu agendar protocolo humano cancelar lgpd |
| Agent free-text | OK | agent_replies > 0, scheduled debounce |
| Callbacks | OK | cmd:agendar / servico:* logs reais |
| HITL /humano API | **FIXED live** | fn_auto_audit + atendimento_id=5 |
| HITL msg ticket # | **fix no repo** | precisa deploy |
| Agendamento FK cliente | **fix no repo** | precisa deploy |
| Evolution | 0/1 | WhatsApp bloqueado — **proposital fora do escopo** |
| N8N | offline/ausente | **nao bloqueia** Telegram self-contained |
| Pytest Telegram | **157 passed** | local |

---

## 10 Goals

| ID | Goal | % | Gate |
|----|------|---|------|
| G1 | Webhook Telegram 100% estavel (sem last_error, pending=0) | 100 | getWebhookInfo |
| G2 | 7 comandos canonicos respondem <2s (DM) | 95 | humano real + metrics |
| G3 | Inline buttons (callback) 100% | 95 | logs + response_sent |
| G4 | HITL /humano cria ticket real com ID numerico | 90 | API live; deploy msg |
| G5 | Fluxo agendar completo (servico→data→hora→confirm) | 70 | ensure cliente no repo |
| G6 | Grupo supergroup -1004331849032 anti-spam + mid-flow | 90 | orient 1x/5min |
| G7 | Agent AI linguagem natural (MiniMax tools) | 85 | agent_replies |
| G8 | Suite pytest Telegram >= 157 + coverage app gate | 95 | 157 green |
| G9 | Docs validacao humana + memory + PROGRESS | 100 | este plano |
| G10 | WhatsApp Evolution (so apos G1–G9) | 0 | scale 1/1 + e2e |

---

## 100 Tasks (por goal, 10 cada)

### G1 Webhook (T001–T010)
1. getWebhookInfo url canonica  
2. pending_update_count=0  
3. allowed_updates message+callback+my_chat_member  
4. Firewall 80/443 DOCKER-USER ACCEPT  
5. Health `/api/v1/telegram/health`  
6. Metrics endpoint vivo  
7. debug/last-updates buffer  
8. set-commands menu BotFather  
9. secret_token opcional documentado  
10. Alert se last_error_message aparecer  

### G2 Comandos DM (T011–T020)
11. /start LGPD notice  
12. /menu atalhos  
13. /agendar servicos  
14. /protocolo pede numero  
15. /humano pede descricao  
16. /cancelar limpa state  
17. /lgpd texto DPO  
18. comando invalido → ignored_command + menu  
19. rate limit IDLE only  
20. typing indicator antes de reply  

### G3 Callbacks (T021–T030)
21. cmd:agendar  
22. cmd:protocolo  
23. cmd:humano  
24. cmd:menu  
25. servico:N  
26. agendar:confirmar  
27. answerCallbackQuery  
28. metrics callbacks_ok  
29. keyboard labels HITL  
30. group callbacks  

### G4 HITL (T031–T040) — P0
31. ~~fn_auto_audit hash+hmac~~ DONE live  
32. ~~POST /atendimento 200~~ DONE  
33. payload external_id/contexto (repo)  
34. ticket_id = atendimento_id (repo)  
35. nao mostrar #N/A se falhar (repo)  
36. hitl_created metric  
37. deploy imagem API  
38. validacao humana DM  
39. audit_log row com hash  
40. cartorio-lgpd review trigger  

### G5 Agendar (T041–T050)
41. ensure cliente_id FK (repo)  
42. devolver cliente_id no atendimento (repo)  
43. data hoje/amanha/DD-MM  
44. hora HH:MM  
45. confirmar sim/nao  
46. conflito 409 message  
47. id agendamento na msg  
48. testes state machine  
49. deploy  
50. validacao humana  

### G6 Grupo (T051–T060)
51. supergroup id -1004331849032  
52. migrate_to_chat_id retry  
53. anti-spam orient 5min  
54. mention @bot free-text  
55. mid-flow data/hora no grupo  
56. per-user conv key  
57. my_chat_member join/leave  
58. reacao eyes  
59. nao floodar  
60. doc VALIDACAO grupo  

### G7 Agent (T061–T070)
61. free-text debounce 1.2s  
62. MiniMax tools path  
63. PII scrub pre-LLM  
64. max response 800  
65. strip emojis texto  
66. fallback se LLM down  
67. agent_errors metric  
68. typing refresh 4s  
69. idempotency update_id  
70. logs sem PII  

### G8 Testes (T071–T080)
71. test_telegram_webhook  
72. test_telegram_state_machine  
73. test_telegram_send  
74. test_telegram_bus_helpers set(ex=)  
75. test_telegram_e2e  
76. HITL regressao #N/A  
77. coverage gate 90%  
78. ruff clean  
79. mypy app/  
80. CI green  

### G9 Docs/Memory (T081–T090)
81. VALIDACAO_TELEGRAM_AMANHA update  
82. Lesson 160  
83. MEMORY.md index  
84. PROGRESS.md cycle  
85. ROADMAP Fase 3 Telegram  
86. GUIA 1000 pontos refresh  
87. este PLAN 10G/100T  
88. comentar codigo critico  
89. session brain 2026-07-09  
90. handoff cmux agents  

### G10 WhatsApp (T091–T100) — so depois G9
91. evolution scale 0→1  
92. CHATWOOT_ENABLED  
93. webhook Evolution dual parse  
94. instance WhatsApp QR  
95. e2e smoke whatsapp  
96. templates Meta  
97. rate limit WhatsApp  
98. PII same 3-layer  
99. HITL same path  
100. go-live WhatsApp  

---

## Proximo passo imediato (ordem)

1. **Deploy** API com fixes telegram.py + router (G4/G5).  
2. Validacao humana no app (roteiro docs/VALIDACAO_TELEGRAM_AMANHA).  
3. So entao Evolution (G10).

Modified by Gustavo Almeida
