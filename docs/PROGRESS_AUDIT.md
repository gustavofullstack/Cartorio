# PROGRESS_AUDIT.md — `scripts/progress_audit.py` (G8.16.T1)

> Auto-persistência de blocos wave no `PROGRESS.md`, com detecção de wave via
> git log + contagem honesta extraída de `SUPER_PLANO_G8_100_TASKS.md`.
> Idempotente: rodar 2× com mesmo `--wave` atualiza o bloco in-place.

Fonte canônica da tarefa: `SUPER_PLANO_G8_100_TASKS.md` Squad 16 → `G8.16.T1`.

## Quickstart

```bash
# 1) Dry-run (imprime bloco, não escreve)
python3 scripts/progress_audit.py --wave 46 \
    --agent sre --honest-pre 50 --honest-post 51 --tests 5 \
    --bullet "**G8.16.T1** PROGRESS audit automation" \
    --bullet "scripts/progress_audit.py + 7 tests" \
    --bullet "Makefile target progress-audit" \
    --dry-run

# 2) Apply (persiste no PROGRESS.md)
python3 scripts/progress_audit.py --wave 46 --apply \
    --agent sre --honest-pre 50 --honest-post 51 --tests 5 \
    --bullet "**G8.16.T1** PROGRESS audit automation"

# 3) Via Makefile
make progress-audit WAVE=46 AGENT=sre PRE=50 POST=51 TESTS=5 \
    BULLET="**G8.16.T1** PROGRESS audit automation"
```

## Formato gerado

O bloco Markdown gerado segue o padrão observado em entradas recentes do
`PROGRESS.md` (ver `## 2026-07-18 — Wave 44 REAL COMPLETED ✅`):

```markdown
## 2026-07-18 — Wave 46 REAL COMPLETED ✅ (cartorio-sre)

- **Honest count:** 50 → **51/100** (+1)
- **G8.16.T1** PROGRESS audit automation
- scripts/progress_audit.py + 7 tests
- **Tests:** 5 passed
Modified by Gustavo Almeida — 2026-07-18T15:00:00.000000+00:00
```

- **Header**: `## YYYY-MM-DD — Wave N REAL COMPLETED ✅ (cartorio-<agent>)`
  - `--date` default = hoje BRT (UTC-3)
  - `--wave` default = maior `Wave N` encontrado em `git log -n50`
- **Honest count**: lido de `SUPER_PLANO_G8_100_TASKS.md` quando `--honest-post`
  não é fornecido (regex `\| (G8\.\d{2}\.T\d+) \| ... \| \[(?P<mark>[ xX~])\]`)
- **Bullets**: cada `--bullet` vira uma linha `- ...` (repetível)
- **Footer**: ISO 8601 UTC, gerado por `datetime.now(timezone.utc).isoformat()`

## CLI Reference

| Flag | Tipo | Default | Descrição |
|------|------|---------|-----------|
| `--wave N` | int | maior do `git log` | número da wave |
| `--date YYYY-MM-DD` | str | hoje BRT | data local usada no header |
| `--agent NAME` | str | `sre` | escopo `cartorio-<NAME>` no header |
| `--honest-pre N` | int | auto | honest count antes |
| `--honest-post N` | int | auto via plano | honest count depois |
| `--tests N` | int | (none) | bullet `**Tests:** N passed` |
| `--bullet "..."` | str (repeatable) | (none) | bullet custom (use `**G8.NN.TM**` para task ID) |
| `--summary "..."` | str | (none) | fallback único bullet |
| `--file PATH` | Path | `PROGRESS.md` | arquivo alvo |
| `--plano PATH` | Path | `SUPER_PLANO_G8_100_TASKS.md` | fonte de honest count |
| `--dry-run` | flag | off | apenas imprime |
| `--apply` | flag | off | persiste (upsert por wave) |
| `--json` | flag | off | envelope JSON antes do bloco Markdown |

Exit codes:
- `0` — sucesso (dry-run OU apply OU JSON)
- `1` — argumento inválido (ex.: sem wave detectável, sem bullet)

## Idempotência

A regex `^## (?P<date>\d{4}-\d{2}-\d{2})\s+—\s+Wave (?P<wave>\d+)` identifica
headers existentes. Quando um bloco com o **mesmo `--wave`** já existe, ele é
**substituído in-place** (mantém a posição na timeline). Blocos de outras
waves permanecem intactos.

Exemplo de repetição segura:

```bash
python3 scripts/progress_audit.py --wave 46 --apply \
    --bullet "first attempt"   # grava
python3 scripts/progress_audit.py --wave 46 --apply \
    --bullet "second attempt"  # substitui
# Resultado: 1× header Wave 46, com "second attempt" — sem duplicata.
```

## Integração com `goal-loop-cron.sh`

`scripts/progress_audit.py` complementa (não substitui) o append automático do
`.harness/loop-engineer/goal-loop-cron.sh`. Enquanto o cron escreve um bloco
genérico `## YYYY-MM-DD HH:MM — LOOP cycle #N` com payload JSON, este helper
produz o bloco canônico `REAL COMPLETED ✅` exigido pelo squad 16.

Sugestão de orquestração no loop-engineer (fora do escopo desta task):

```bash
# No goal-loop-cron.sh, após validar testes verdes:
if [[ "$RES_TEST" == *"PASS"* ]]; then
    WAVE=$(jq -r '.next_wave' "$STATE_DIR/last.json")
    POST=$(grep -c '\[x\]' SUPER_PLANO_G8_100_TASKS.md || echo "?")
    python3 scripts/progress_audit.py --wave "$WAVE" \
        --agent sre --honest-post "$POST" --apply \
        --bullet "Loop cycle $WAVE auto-persisted via goal-loop-cron"
fi
```

## Testes

`backend/tests/test_progress_audit.py` (7 casos, ~0.2s):

- `test_format_wave_block_from_args` — formatação correta do bloco
- `test_idempotent_update_replaces_block` — 2× apply substitui in-place
- `test_extract_honest_count_from_super_plano` — contagem `[x]`/`[ ]`
- `test_format_timestamp_brt` — ISO 8601 UTC + BRT date
- `test_dry_run_does_not_modify_file` — dry-run é no-op em disco
- `test_apply_writes_block_and_then_noop_on_second_run` — apply idempotente
- `test_cli_runs_as_subprocess` — smoke E2E do binário CLI

```bash
cd backend && uv run pytest tests/test_progress_audit.py -v --no-cov
# 7 passed in 0.23s
```

## Constraints honrados

- **Sem segredos** — script só lê `.md` files; zero acesso a `.env`.
- **Append/replace only** — não há `--rewrite-history`. Headers antigos são
  preservados literalmente.
- **Idempotente** — rodar 2× com mesmo `--wave` é safe.
- **Sem rede** — zero chamadas externas; só `git log` local + fs read/write.

## Modified by Gustavo Almeida — cartorio-sre · G8.16.T1 Wave 46
