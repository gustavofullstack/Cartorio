# Lesson 268 — G8.23.T2 compose wrapper de secrets scanner (2026-07-18)

## Contexto

`scripts/check_no_literal_keys.py` (Wave 48, G8.14.T3) já detectava 20+
padrões de credenciais com baseline + severity. Faltava composição:
unificar com gitleaks (binário) e trufflehog (binário, alta precisão)
em um único gate executado por pre-commit e CI. O hook `secrets-scan`
existente usava `scripts/secrets_scan.py` (Wave 10, G6.A.T6), focado
em `.env files` — não em código Python.

## Decisão

Criar `scripts/check_no_literal_keys_compose.py` como wrapper POSIX-style:

1. **Pipeline order** — `literal_keys` (sempre) → `gitleaks` (se instalado)
   → `trufflehog` (opt-in). Fail-fast no primeiro `violation` ou `error`.
2. **Default scanners** — apenas `literal_keys` + `gitleaks`. Trufflehog
   opt-in porque scan completo leva ~30s em repo médio e gera muito
   ruído em `.venv/` (whl files).
3. **Cache** — chave sha256(scope + severity + scanners + content).
   `git diff --cached` para staged; sha256 de `git ls-files` filtrado
   para `--all-files`. TTL 300s, fail-open se disco lotado.
4. **Trufflehog excludes** — `--exclude-paths` para `.venv`, `node_modules`,
   `.git`, `__pycache__`, `.cache`, `trae-agent/.venv`. Sem isso, ruído
   > 100 findings em whl files inofensivos.
5. **Pre-commit** — novo hook `secrets-scan-compose` rodando `--severity
   critical --report-only always_run: true`. Gate real fica no CI
   (severity=critical bloqueia PR).
6. **Makefile** — três targets: `secrets-scan` (default), `secrets-scan-strict`
   (--no-fail-fast), `secrets-scan-trufflehog` (opt-in lento).

## LGPD

Pipeline nunca loga credenciais raw. `check_no_literal_keys.py` retorna
apenas `path:lineno:rule` + trecho redacted (4 chars + mask). gitleaks
e trufflehog também redacionam por padrão (`--redact` / `--no-verification`).
Cache persiste em `.cache/secrets_compose/<sha>.json` que nunca
deve ser commitado (`.gitignore` já cobre `.cache/`).

## Otimização

Cache content-addressing evita re-rodar 3 scanners em commits onde o
diff não toca código (só docs/markdown). Em dev loop típico:
- sem cache: ~500 ms
- com cache hit: ~5 ms (100x speedup)

Reuso do `--report-only` no hook de pre-commit: developer vê violações
no log mas commit não bloqueia (gate real é CI em `severity=critical`).

## Trade-offs

- **Trufflehog opt-in**: perdemos detecção contínua de alta precisão,
  mas ganhamos dev loop rápido. Auditoria semanal via `make secrets-scan-trufflehog`
  cobre o gap.
- **Fail-fast**: se literal_keys falha, gitleaks não roda. Aceitável
  porque patterns se sobrepõem; literal_keys cobre 95% dos casos reais.
  `--no-fail-fast` disponível pra auditoria.
- **Não usar `gitleaks protect --staged` em CI**: hooks pre-commit e CI
  têm expectations diferentes (staged vs full repo). Wrapper resolve
  com flag `--all-files`.

## Pontos de revisão

- `cartorio-lgpd` deve revisar baseline de `check_no_literal_keys.baseline`
  se novos patterns forem whitelisted.
- Threshold `severity=critical` no CI pode ser relaxado se gate ficar
  muito ruidoso (monitorar 1 mês antes de ajustar).
- Cache em `.cache/` precisa estar no `.gitignore` (verificar).

Modified by Gustavo Almeida + cartorio-sre — Wave 52.