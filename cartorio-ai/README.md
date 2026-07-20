# cartorio-ai

**Camada de identidade, memória e governança dos agentes do Cartório 2º Notas (Uberlândia/MG).**

O projeto Cartório é uma backend API (FastAPI + SQLAlchemy 2.0 + Postgres/Supabase + Redis 8)
com bot WhatsApp/Telegram/Web, LGPD-by-design, audit log imutável (SHA256 chain + HMAC),
PII scrubbing em 3 camadas e human-in-the-loop obrigatório em toda ação jurídica.

Este diretório responde: *quem é o agente, qual sua missão, o que ele lembra, quais limites
de segurança e compliance regem cada decisão.* O código está em `../backend/`; a orquestração
de sprints em `../.harness/`; o plano ativo em `../SUPER_PLANO_G9_100_TASKS.md`.

## Núcleo (completo — 2026-07-20)

| Arquivo | Conteúdo |
|---|---|
| `AGENTS.md` | Regras de operação dos agentes (espelho governado da raiz) |
| `README.md` | Este arquivo |
| `ARCHITECTURE.md` | Mapa do repositório e das integrações |
| `MANIFEST.md` | Inventário e status do pacote |
| `INDEX.md` | Índice navegável do núcleo |
| `BOOTSTRAP.md` | Onboarding de um agente novo em <10 min |
| `ROADMAP.md` | O que falta do layout completo (~400 arquivos) |
| `brain/BRAIN.md` | Como o agente pensa: workflow, honesty gate |
| `identity/SOUL.md` | Propósito e valores inegociáveis |
| `identity/IDENTITY.md` | Identidade operacional, canais, tom |
| `planning/GOALS.md` | Metas ativas (G9) |
| `planning/TASKS.md` | Ponte para o SUPER PLANO G9 |
| `memory/MEMORY.md` | Fatos-chave e ponteiros de memória |
| `security/SECURITY.md` | Modelo de segurança e segredos |
| `compliance/CNJ.md` | Fluxo de exportação CNJ / proteção de dados |

## Estado do projeto (2026-07-20)

- Telegram **funcional em prod**: webhook com secret OK; `/start` → `response_sent=true`;
  texto livre/grupo → `scheduled=true` (debounce async). Regressões A1–A6 diagnosticadas (G9 Squads 01–03).
- LLM: fallback OpenCode Zen (3 contas) integrado; coerência slot↔conta e payload por provider no G9.
- CNJ: endpoint `/api/v1/lgpd/cnj-exports/massive-dump` implementado (streaming + JWT DPO + hash chain).
- Pendências SUI do dono: DNS (3 A records), Tailscale restore, QR WhatsApp, OpenClaw E8.
