# STATUS — Cartório 2º Notas Uberlândia (snapshot 2026-07-06 17:50 BRT)

## Infra PROD (7 serviços)

| Serviço | URL | HTTP | Latência | Status |
|---|---|---|---|---|
| API FastAPI | api.2notasudi.com.br | 200 | 92ms | 🟢 UP v0.6.0 |
| Flow N8N | flow.2notasudi.com.br | 404 | 113ms | 🟡 UP só webhook |
| WhatsApp Evolution | whatsapp.2notasudi.com.br | 200 | 389ms | 🟡 instance close |
| Chatwoot easypanel | cartorio-chatwoot.dfgdxq.easypanel.host | timeout | 8s | 🔴 DOWN hoje |
| OpenClaw | agent.2notasudi.com.br | 200 | 422ms | 🟢 UP |
| Supabase | supbase.2notasudi.com.br | 404 | 98ms | 🟡 401 esperado |
| EasyPanel | easypanel.2notasudi.com.br | 200 | 191ms | 🟢 UP |

## Gates qualidade

| Gate | Status |
|---|---|
| ruff check | 🟢 0 errors |
| mypy app/ | 🟢 0 errors (121 files) |
| pytest | 🟢 1792 passed + 23 novos LGPD |
| coverage | 🟢 ≥90% |

## DNS (pendente UI Gustavo)

- 🔴 chatwoot.2notasudi.com.br (NXDOMAIN)
- 🔴 n8n.2notasudi.com.br (NXDOMAIN)
- 🔴 supabase.2notasudi.com.br (NXDOMAIN)

## Tasks operacionais (TASKS.md)

- DONE: 127/444 (28.6%)
- OPEN: 317/444 (71.4%)
- Sprint ativo: 47 (Squad 81/136 60%)

## Pendências SUI Gustavo (4 ações manuais, ~20min)

1. DNS Hostinger: 3 A records
2. WhatsApp TriQ Hub: scan QR
3. Telegram bot: /start no celular
4. Chatwoot easypanel: investigar timeout 8s

Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-06 17:50 BRT
