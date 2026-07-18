# Secrets Scanner Compose — G8.23.T2 (Wave 52)

> Pipeline orquestrado de detecção de credenciais. Compõe 3 scanners
> (custom + gitleaks + trufflehog) em um único gate executado por
> pre-commit, `make secrets-scan` e GitHub Actions.

LGPD Art. 46 — zero credenciais commitadas. P0 incident se vazar
(PII + secrets compartilham a mesma categoria de risco).

## Arquitetura

```
                  ┌──────────────────────────────────────┐
                  │  scripts/check_no_literal_keys_      │
                  │  compose.py (este wrapper)           │
                  └──────────────────┬───────────────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                │                    │                    │
        ┌───────▼────────┐  ┌────────▼──────┐  ┌─────────▼─────────┐
        │ literal_keys   │  │   gitleaks    │  │    trufflehog     │
        │ (custom 20+)   │  │  (binary)     │  │  (binary, opt-in) │
        └───────┬────────┘  └────────┬──────┘  └─────────┬─────────┘
                │                   │                    │
                └───── fail-fast ───┴────── skipped ────┘
                                     │
                                     ▼
                              exit 0 / 1 / 2
```

| Scanner      | Cobre                                                       | Velocidade | Default |
|--------------|-------------------------------------------------------------|------------|---------|
| literal_keys | 20+ patterns (lin_api_*, sk-*, sk-cp-*, AKIA, JWTs, ENV)   | ~300 ms    | ON      |
| gitleaks     | 100+ padrões genéricos (entropy + regex)                   | ~100 ms    | ON      |
| trufflehog   | Alta precisão (valida credenciais via chamadas reais)       | ~30 s      | opt-in  |

## Invocation

### Hook pre-commit (`.pre-commit-config.yaml`)

```yaml
- id: secrets-scan-compose
  name: Secrets scan compose (G8.23.T2) — literal_keys + gitleaks
  entry: python3 scripts/check_no_literal_keys_compose.py --severity critical --report-only
  language: system
  pass_filenames: false
  always_run: true
```

Roda em TODO commit (`always_run: true`), mas só bloqueia severidade
`critical` (modo `--report-only` reporta violações sem falhar, para
não atrapalhar fluxo de feature branch). O gate real fica no CI.

### Makefile (raiz)

| Target                  | Comando                                                              | Quando usar                       |
|-------------------------|----------------------------------------------------------------------|-----------------------------------|
| `make secrets-scan`     | `python3 scripts/check_no_literal_keys_compose.py`                   | Dev loop / local debug            |
| `make secrets-scan-strict` | `... --severity critical --no-fail-fast`                          | Auditoria manual pré-PR           |
| `make secrets-scan-trufflehog` | `... --scanner trufflehog --scanner literal_keys`              | Auditoria semanal (high precision)|

### CLI direta

```bash
# Pipeline default (literal_keys + gitleaks, fail-fast).
python3 scripts/check_no_literal_keys_compose.py

# Smoke test só do literal_keys (sem gitleaks).
python3 scripts/check_no_literal_keys_compose.py --scanner literal_keys

# Strict mode (severity=critical, sem fail-fast).
python3 scripts/check_no_literal_keys_compose.py --severity critical --no-fail-fast

# Trufflehog ligado (lento, alta precisão).
python3 scripts/check_no_literal_keys_compose.py --scanner trufflehog

# Saída machine-readable.
python3 scripts/check_no_literal_keys_compose.py --json | jq '.[].status'

# Wipe cache local.
python3 scripts/check_no_literal_keys_compose.py --clear-cache
```

## CI/CD

```yaml
# .github/workflows/ci.yml — step secrets-scan (G8.14.T3 + G8.23.T2).
- name: Secrets scan (compose — Wave 52)
  run: python3 scripts/check_no_literal_keys_compose.py --severity critical --no-fail-fast --all-files
```

Gate: exit ≠ 0 → CI vermelho → PR bloqueado. Severity `critical` no CI
(local pode rodar `low` para reportar medium/low sem bloquear dev).

## Cache

| Flag           | Default | Significado                                                  |
|----------------|---------|--------------------------------------------------------------|
| `--no-cache`   | off     | Bypassa cache, re-executa todos os scanners                  |
| `--cache-ttl`  | 300 s   | TTL do cache em segundos                                     |
| `--clear-cache`| -       | Apaga `.cache/secrets_compose/` antes de rodar               |

Chave de cache = sha256(scope + severity + scanners + conteúdo).
Para `--staged`, o conteúdo é o `git diff --cached`. Para `--all-files`,
é o sha256 do snapshot de todos os arquivos rastreados.

## LGPD Art. 46 — P0 se vazar

Categorias detectadas (Wave 48 G8.14.T3, ampliadas em Wave 52):

| Pattern                  | Provider                                |
|--------------------------|-----------------------------------------|
| `lin_api_*`              | Linear API                              |
| `sk-*`                   | OpenAI                                  |
| `sk-proj-*`              | OpenAI Project                          |
| `sk-ant-*`               | Anthropic                               |
| `sk-cp-*`                | MiniMax Coding Plan                     |
| `rnd_*`                  | Render                                  |
| `AQ.*`                   | Azure                                   |
| `gAAAAA*`                | Fernet cipher                           |
| `ghp_*` / `gh[sur]_*`    | GitHub                                  |
| `xox[bpors]-*`           | Slack                                   |
| `AKIA*` / `ASIA*`        | AWS access key                          |
| `AIza*`                  | Google API                              |
| JWT `eyJ...`             | Generic JWT (incluindo `service_role`)  |
| GCP service-account JSON | Google Cloud service account            |
| Telegram bot token       | `\d{10}:[A-Za-z0-9_-]{35}`              |
| ENV fallback literal     | `os.environ.get(K, "<literal>")`        |
| PKCS8 / PKCS1 key        | `-----BEGIN PRIVATE KEY-----`           |

Opt-out (use com moderação):
- Inline: `# noqa: ALLOW_KEY_FALLBACK` (motivo: `<descrever>`)
- Whitelist: `backend/scripts/check_no_literal_keys.baseline`
  (formato: `<path>:<lineno>:<rule>`)

## Testes (25 cases, `backend/tests/test_check_no_literal_keys_compose_g8.py`)

```
test_main_invokes_literal_keys                  PASSED
test_main_invokes_gitleaks_if_available         PASSED
test_main_skips_gitleaks_when_not_installed     PASSED
test_main_fails_fast_on_first_critical          PASSED
test_main_runs_everything_with_no_fail_fast     PASSED
test_main_returns_0_when_clean                  PASSED
test_cli_severity_is_forwarded_to_literal_keys  PASSED
test_cli_report_only_is_forwarded               PASSED
test_cli_default_scanners_excludes_trufflehog   PASSED
test_cli_json_output_is_machine_readable        PASSED
test_scan_result_is_critical_for_violation      PASSED
test_scan_result_is_critical_for_error          PASSED
test_scan_result_not_critical_for_ok            PASSED
test_scan_result_not_critical_for_skipped       PASSED
test_render_text_clean_summary                  PASSED
test_render_text_failure_summary                PASSED
test_cache_key_changes_with_severity            PASSED
test_cache_read_returns_none_when_missing       PASSED
test_cache_round_trip                           PASSED
test_cache_expires_after_ttl                    PASSED
test_clear_cache_wipes_directory                PASSED
test_tool_exists_detects_binary                 PASSED
test_trufflehog_excludes_venv                   PASSED
test_trufflehog_skipped_when_no_binary          PASSED
test_cli_smoke_clean_repo_returns_zero          PASSED
======================================== 25 passed
```

## Histórico

| Wave | Task       | Mudança                                                                  |
|------|------------|--------------------------------------------------------------------------|
| 48   | G8.14.T3   | literal_keys criado (20+ patterns, --severity, baseline)                 |
| 52   | G8.23.T2   | compose wrapper, pre-commit hook, cache, 25 tests                       |

Modified by Gustavo Almeida + cartorio-sre — Wave 52.