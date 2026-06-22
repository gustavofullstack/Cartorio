# Cartorio - Chatbot Autonomo

Bot WhatsApp/Telegram/Web para cartorio com compliance LGPD, audit log imutavel e human-in-the-loop em acoes juridicas.

## Stack

| Camada | Tecnologia | Papel |
|--------|-----------|-------|
| Mensageria | OpenClaw + Evolution API | Gateway WhatsApp/Telegram, multi-canal |
| Workflow | n8n + n8n-runner | Orquestracao visual, integracoes |
| Database | Supabase (Postgres + Storage + Auth) | Persistencia principal |
| LLM | LiteLLM (Claude Opus 4.5 / GPT-5.5) | Raciocinio + PII scrubbing local |
| Backend regras | FastAPI + SQLAlchemy 2.0 (este repo) | Logica cartoraria + audit log + PII |
| LLM local | Llama 3.1 8B (a definir) | PII detection pre-API publica |

## Estrutura

```
cartorio/
├── backend/                # FastAPI - logica cartoraria + audit
│   ├── app/
│   │   ├── api/v1/         # endpoints HTTP
│   │   ├── models/         # 5 tabelas core + audit_log
│   │   ├── services/       # audit (hash chain), pii, emolumento
│   │   └── main.py
│   ├── tests/              # pytest, 90%+ coverage
│   └── pyproject.toml
├── infra/
│   ├── n8n-workflows/      # JSON exports dos workflows
│   └── supabase/           # schema.sql
└── docs/
    ├── ARCHITECTURE.md
    ├── ROADMAP.md
    └── LGPD.md
```

## Quick start

```bash
cd backend
uv sync                                          # instala deps
cp .env.example .env                             # preenche credenciais
pytest                                           # roda testes (90%+ coverage)
uv run uvicorn app.main:app --reload --port 8000
```

## Garantias "nao pode errar"

1. **Audit log tamper-evident** — cada entrada referencia SHA256 da anterior (blockchain-style). Edicao retroativa invalida a cadeia. HMAC-signed alem do hash chain.
2. **PII scrubbing** — CPF/RG/telefone/email sao mascarados antes de ir pra LLM publica. Logs guardam apenas hash + scrubbed text.
3. **Human-in-the-loop** — bot qualifica, humano executa qualquer acao em documento juridico.
4. **LGPD by design** — soft delete, consentimento explicito, retencao configuravel, DPO designado.
5. **Versionamento rigoroso** — Conventional Commits, 90%+ test coverage, code review obrigatorio.

## Status

MVP skeleton — Sprint 0 (foundation). Veja `docs/ROADMAP.md` para o plano de 12 semanas.

## Equipe

- Pietra (Pietra/Mavis) — orquestracao + decisao de produto
- ceo-assistant — roadmap estrategico + compliance
- coder/udiapods-fe-mobile — implementacao

Modified by Gustavo Almeida
