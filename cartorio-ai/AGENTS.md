# cartorio-ai · AGENTS.md

Camada de conhecimento, identidade e governança dos agentes do **2º Serviço Notarial de Uberlândia**.
Este diretório NÃO contém código de produção — o backend vive em `../backend/` e a orquestração de
reins em `../.harness/`. Aqui ficam os documentos que definem **quem os agentes são, como pensam,
o que podem e o que nunca podem fazer**.

## Fonte de verdade operacional

1. `../AGENTS.md` (raiz) — spec compacto: stack, comandos `make`, regras P0, gotchas.
2. `../.harness/AGENTS.md` — operacional completo (standards, reins, tasks, validators).
3. `../SUPER_PLANO_G9_100_TASKS.md` — plano ativo de 100 tasks (estado em `planning/TASKS.md`).
4. Este núcleo — síntese viva, derivada dos itens acima; em conflito, a raiz vence.

## Regras P0 herdadas (violou = parar tudo)

1. **HITL obrigatório** — protocolo nasce `DRAFT`; escrevente valida. Bot nunca decide isenção,
   urgência, validação jurídica ou emissão de certidão/escritura.
2. **PII nunca raw** — CPF/RG/protocolo/escritura mascarados antes de qualquer LLM pública, log
   ou storage externo (3 camadas: Pydantic validators → Sentry `before_send` → `MaskingFilter`).
3. **Audit log append-only** — SHA256 chain + HMAC; edição retroativa invalida a cadeia.
4. **Secrets nunca commitados** — `.env` no `.gitignore`; rotação de chaves SÓ com ordem expressa
   do dono (Gustavo Almeida).
5. **Sem fallback de chave literal** — `scripts/check_no_literal_keys.py` bloqueia padrões conhecidos.
6. **Conventional Commits** terminando com `Modified by Gustavo Almeida`; branch a partir de `master`.

## Workflow obrigatório (ciclo de mudança)

`analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória`.
Pular etapa = bug, especialmente em `audit*` ou `pii*` (exige sign-off `cartorio-lgpd`).

## Reins do time

- `cartorio-dev` — backend FastAPI / SQLAlchemy / audit / PII.
- `cartorio-n8n` — workflows n8n / Evolution / OpenClaw / multi-canal / deploy.
- `cartorio-lgpd` — LGPD / RIPD / retenção / privacy policy / erasure rights.
- Mudança em `audit*`/`pii*`: dev implementa + lgpd revisa e assina.

## Comandos (sempre via Makefile da raiz)

```bash
make dev        # uvicorn :8000 reload
make test-fast  # pytest sem coverage (loop de dev)
make qa         # lint + test (mesmo gate do CI)
make -C backend smoke   # /health, /ready, /api/v1/health/radar
```
