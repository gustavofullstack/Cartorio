# Onboarding - Cartorio Chatbot

> **10 passos para um dev novo estar produtivo em < 2 horas.**
> Atualizado: 2026-06-24

## Pre-requisitos

- macOS ou Linux
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager Python)
- Docker (para Postgres + Redis locais)
- Git

## 10 passos

### 1. Clone o repo (5 min)

```bash
git clone git@github.com:gustavofullstack/Cartorio.git
cd Cartorio
```

### 2. Setup Python (3 min)

```bash
# Instala uv (se nao tem)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sincroniza deps
cd backend
uv sync --all-extras
```

### 3. Setup banco + Redis locais (5 min)

```bash
# Postgres (porta 5432)
docker run -d --name cartorio-pg \
  -e POSTGRES_USER=cartorio \
  -e POSTGRES_PASSWORD=cartorio \
  -e POSTGRES_DB=cartorio \
  -p 5432:5432 postgres:16

# Redis (porta 6379)
docker run -d --name cartorio-redis \
  -p 6379:6379 redis:7
```

### 4. Setup .env (5 min)

```bash
# Copia template
cp backend/.env.example backend/.env

# Edita e preenche:
# - DATABASE_URL (postgres://cartorio:cartorio@localhost:5432/cartorio)
# - REDIS_URL (redis://localhost:6379/0)
# - OPENCODE_GO_API_KEY (pedir pra Gustavo)
# - CHATWOOT_API_KEY (pedir pra Gustavo - N8N)
# - N8N_API_KEY (pedir pra Gustavo)
# - EVOLUTION_API_KEY (pedir pra Gustavo - WhatsApp)
```

### 5. Roda migrations (2 min)

```bash
cd backend
uv run alembic upgrade head
```

### 6. Roda testes (5 min)

```bash
uv run pytest -v
# Esperado: 400+ passed, coverage >= 90%
```

Se vermelho, ver [FAQ](FAQ.md) ou pedir ajuda no Telegram da squad.

### 7. Sobe API local (3 min)

```bash
uv run uvicorn app.main:app --reload --port 8000
# OU
make dev
```

Abre http://localhost:8000/docs (Swagger UI).

### 8. Instala pre-commit hook (5 min)

```bash
# Instala pre-commit
pip install pre-commit

# Ativa hooks no repo
cd ..
pre-commit install
pre-commit install --hook-type commit-msg

# Testa
pre-commit run --all-files
```

### 9. Le 5 docs ESSENCIAIS (30 min)

Em ordem de prioridade:

1. [README.md](../README.md) - 5min (visao geral)
2. [ARCHITECTURE.md](ARCHITECTURE.md) - 10min (diagramas + decisoes)
3. [DATA_FLOW.md](DATA_FLOW.md) - 10min (PII + LGPD)
4. [API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md) - 5min (curl examples)
5. [mega-plano-100-tasks](superpowers/plans/2026-06-24-mega-plano-100-tasks.md) - 5min (visao de produto)

Bonus se tiver tempo:
- [FAQ.md](FAQ.md) - troubleshooting
- [RUNBOOK_VPS.md](RUNBOOK_VPS.md) - comandos de prod
- [AGENTS.md](../.harness/AGENTS.md) - 3 reins (dev, n8n, lgpd)
- [MEMORY.md](../.harness/memory/MEMORY.md) - licoes cross-rein

### 10. Faz 1 PR end-to-end (60 min)

Para validar que entendeu o ciclo completo, faça uma PR de teste:

a) **Branch**:
```bash
git checkout -b chore/onboarding-test
```

b) **Mudanca minima** (ex: adicionar 1 funcao em `app/services/pii.py`):
```python
# Em backend/app/services/pii.py, adicionar:

def is_valid_brazilian_phone(phone: str) -> bool:
    """Valida telefone brasileiro (10 ou 11 digitos com DDD)."""
    digits = re.sub(r"\D", "", phone)
    return bool(re.match(r"^[1-9][1-9]9?\d{8}$", digits))
```

c) **Teste** (em `backend/tests/test_pii.py`):
```python
def test_is_valid_brazilian_phone():
    assert is_valid_brazilian_phone("(34) 98888-7777") is True
    assert is_valid_brazilian_phone("34988887777") is True
    assert is_valid_brazilian_phone("123") is False
```

d) **Verifica**:
```bash
cd backend
uv run pytest tests/test_pii.py::test_is_valid_brazilian_phone -v
uv run ruff check .
uv run mypy app/services/pii.py
```

e) **Commit + push**:
```bash
git add .
git commit -m "feat(pii): is_valid_brazilian_phone helper

Util para validacao de telefone antes de chamar LLM.
Adicionado como parte do onboarding para validar ciclo end-to-end.

Modified by [seu nome]"
git push origin chore/onboarding-test
```

f) **Abre PR** no GitHub. O template `.github/pull_request_template.md` vai aparecer preenchido. Preenche TODOS os checklists.

g) **Espera review** de Gustavo ou cartorio-dev. Apos merge, sua primeira contribuicao esta em prod!

## Apos o onboarding

Voce ja sabe o suficiente para:
- Rodar a API local
- Entender o fluxo de dados
- Fazer PR com qualidade
- Achar respostas no FAQ

Proximos passos (se for cartorio-dev):
- Ler ADRs (`docs/adr/README.md`)
- Pegar 1 task do mega-plano
- Comecar a fazer commits no fluxo normal

## Quem sou eu no projeto?

- **cartorio-dev**: backend Python (FastAPI + SQLAlchemy + LGPD)
- **cartorio-n8n**: workflows N8N + Evolution/Chatwoot integration
- **cartorio-lgpd**: compliance + RIPD + DPA + auditoria

Cada rein tem um AGENTS.md em `.harness/reins/<nome>/agent.md`.

## Duvidas?

- Slack/Telegram: squad cartorio
- Issues: https://github.com/gustavofullstack/Cartorio/issues
- Gustavo: pietra@cartorio

Modified by ZCode/Mavis - 2026-06-24
