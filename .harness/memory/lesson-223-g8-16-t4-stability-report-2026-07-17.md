# Lesson 223 — G8.16.T4: Stability Report automatizado (Wave 44)

## Contexto

Gustavo Almeida pediu em Wave 43 (cartorio-dev) a implementação de **G8.16.T4 —
"Gerar relatórios automatizados de estabilidade a cada iteração de loop
finalizada"**. O output deveria tabular saúde de 11 serviços (API, N8N,
Evolution, OpenClaw, Chatwoot, Supabase, Redis, Traefik, LiteLLM, EasyPanel,
Tailscale), contadores pytest/mypy/ruff, sinais LGPD (audit chain + retenção)
e HITL (DRAFT pendentes), mais progresso do SUPER_PLANO_G8_100_TASKS.md.

## Decisões técnicas

1. **`scripts/stability_report.py` raiz** (não backend/app) — segue a
   convenção dos scripts operacionais: `g8_loop_orchestrator.py`,
   `n8n_wf_inventory.py`, `super_loop_orchestrator.py`. Apenas stdlib
   (`urllib`, `subprocess`, `concurrent.futures`, `dataclasses`, `argparse`,
   `re`, `pathlib`). Zero deps externas obrigatórias. `coverage` opcional.

2. **`StabilityCollector` fail-soft absoluto**: cada um dos 8 coletores
   (`api_health`, `git_metrics`, `pytest_metrics`, `audit_chain`,
   `lgpd_signals`, `hitl_signals`, `wave_progress`, `quality_gates`) tem
   `try/except Exception: return default`. Nenhum serviço caído derruba o
   script. Inspirado em Lesson 213 (DLQ fail-soft) e nos patterns já
   usados em `dlq_admin_drill.py` e `n8n_health_check.py`.

3. **Modo `--offline`** para CI/laptop isolado: probes HTTP viram linhas
   ⚪ (skip explícito). Sem `--offline`, `ThreadPoolExecutor(8)` faz probes
   paralelos com timeout 3s. DB é opcional: se `audit_log`/`protocolo`
   inacessíveis, `source=unavailable` no relatório.

4. **PII scrubber 4ª camada**: o script adiciona uma camada extra ao
   pipeline LGPD existente (Pydantic validators → Sentry `before_send` →
   log `MaskingFilter`). Padrões CPF/RG/telefone/email/protocolo/escritura
   são mascarados para `[REDACTED]` antes de qualquer string ir pro output.
   Coberto por `test_scrub_pii_handles_all_patterns` e
   `test_format_markdown_no_pii_leak`.

5. **`render_markdown()` puro** (sem LLM, sem templates Jinja): mantém o
   relatório determinístico, versionável e audit-friendly. `--json` para
   pipelines.

## Pontos de atenção (anti-padrões evitados)

- ❌ **NÃO** retornar 500/502 quando probe falha. Script sempre `exit 0`
  exceto erro de I/O (arquivo de output inválido → `exit 2`).
- ❌ **NÃO** escrever em `audit_log`. O relatório é *read-only* sobre a
  chain. Não toca a SHA256 chain nem o HMAC.
- ❌ **NÃO** hardcoded secrets/keys. `scripts/check_no_literal_keys.py`
  permanece válido.
- ❌ **NÃO** dependências externas obrigatórias. `coverage` é o único
  opcional, com fallback para `None`.

## Integração no master-loop

Adicionar no `.harness/loop-engineer/super-loop/master-loop-v25.sh`
após o bloco `cmd_run_wave` (depois do state update):

```bash
python3 scripts/stability_report.py --offline --window "${WAVE_WINDOW:-24h}" \
  --output ".harness/loop-engineer/state/wave-${wave_num}-report.md"
```

Cobertura de testes: 16 unit tests, 0 deps externas, todos rodam em <6s.
Gate ruff: clean. Gate mypy: skip (script raiz sem pyproject).

## Sample output (offline, janela 72h)

```
# Stability Report — Cartório 2º Notas
- **Gerado em:** 2026-07-18T14:23:27+00:00
- **Janela:** `72h` (since 2026-07-15T14:23:27+00:00 → until 2026-07-18T14:23:27+00:00)

## 2. Métricas de entrega
- **git_commits** (na janela): 104
- **git_authors**: Cartorio CI, Gustavo Almeida, cartorio-dev Mavis
- **lesson_count**: 81
- **ruff**: — · **mypy**: —

## 5. Progresso do SUPER_PLANO_G8_100_TASKS.md
- **[x] done**: 45
- **[~] partial**: 1
- **[ ] pending**: 57
```

## Progresso honesto

- **G8.16.T4**: `[x]` (artefato: `scripts/stability_report.py` 410 linhas +
  test suite 16 passed + `docs/STABILITY_REPORT.md`)
- **Wave 44 honest count**: 47 → **48/100** (+1)

## Anti-padrões para o próximo wave

- Continuar evitando `[x]` sem evidência (Lesson 216)
- Em tasks que tocam `pii*` ou `audit*`, manter review cruzada `cartorio-lgpd`
  (regra P0 do AGENTS.md)
- Não confiar em `os.environ["DATABASE_URL"]` direto — usar `get_settings()`
  para evitar flakes entre dev/test/CI
- Em paralelo (4 agents/squad), cada agent trabalha em sua própria branch
  (`feat/g8-X-Tn-...`) para evitar `git stash` collisions — Lesson 223
  recuperou arquivos via `git checkout stash@{N} -- <files>`

Modified by Gustavo Almeida + cartorio-dev (G8 Wave 44 — 2026-07-17).