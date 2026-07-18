# Lesson 226 — G8.12.T1: Unificar PII masking no backend (DRY consolidation)

## Contexto

Tarefa do SUPER_PLANO_G8_SQUAD_12 (DRY/KISS cleanup):
**G8.12.T1 — "Identificar e unificar rotinas duplicadas de PII masking
no backend."** Foi feita por `cartorio-dev` em 2026-07-18 durante
Wave 44 (paralela com G8.12.T2/T3/T4).

## Inventário de duplicações (catálogo encontrado)

Audit em `backend/app/` revelou **pelo menos 6 lugares** com detecção
e/ou mascaramento de PII:

| Path | LOC | Função | Status G8.12.T1 |
|------|-----|--------|-----------------|
| `app/services/pii.py` | 363 | Engine canonico (13 regex, hash, validate) | **MANTIDO INTACTO** (P0.5) |
| `app/services/mcp_pii.py` | 98 | `scrub_mcp_output` recursivo + `mcp_output_has_raw_cpf` (regex duplicado) | **REFATORADO** — usa `_CPF_PATTERN` canonico |
| `app/utils/output_safety.py` | 103 | `scrub_response`/`scrub_response_safe` (recursive) | **MANTIDO** — re-exportado em `pii_unified` |
| `app/utils/pii_sanitizer.py` | 147 | `sanitize_cpf/rg/email/phone/cnpj/pIi/dict` partial reveal (`***789-00`) | **HEADER ADDED** apontando pii_unified |
| `app/services/crypto.py` | 138 | `mask_cpf/cnpj/email/nome/email_display` constant redaction | **MANTIDO** — re-exportado em `pii_unified` |
| `app/models/cpf_cnpj_validator.py` | 108 | `mask_cpf/mask_cnpj` DUPLICADO com crypto | **MANTIDO** — só usado em tests |
| `app/services/traefik_log_masker.py` | 33 | Regex CPF/email/phone/token duplicados | **REFATORADO** — `_CPF` agora alias `_CPF_PATTERN` |
| `app/services/log_masker.py` | 67 | `MaskingFilter` (logging.Filter fail-safe) | **MANTIDO** — escopo diferente (runtime log filter) |

## Decisão arquitetural

1. **NÃO reescrever `app/services/pii.py`** — P0.5 docstring avisa
   que a **ordem dos 13 regex em `_PATTERNS` é crítica** (CNS antes
   de phone_br para não ser engolido pelos primeiros 11 digits; CNH
   antes de CPF; etc.). Cross-review formal pre-merge em ADR-019.

2. **Criar `app/services/pii_unified.py`** como wrapper
   `single-source-of-truth` que:
   - Re-exporta TUDO do canonico (`scrub`, `detect_only`, `hash_pii`,
     `validate_cns/cnh`, `ScrubResult`, `mcp_pii.scrub_mcp_output`,
     `output_safety.scrub_response/safe`)
   - Expõe `_CPF_PATTERN = pii._PATTERNS["cpf"]` como símbolo público
     para que callers não dupliquem o regex
   - Adiciona kind-aware `mask(kind, value, *, partial=False)` que
     delega para `scrub` (full) ou `pii_sanitizer.sanitize_*` (partial)
   - Atalho `mask_safe(value)` = `mask("auto", value)`
   - `mask_email_display`, `mask_nome` delegam para `crypto`
   - `deprecation_notice(legacy_module)` hook para migration futura

3. **Refatorar apenas regex duplicados do CPF (5ª re-ocorrência)**
   - `mcp_pii.mcp_output_has_raw_cpf` → `_CPF_PATTERN` (lazy import
     para quebrar ciclo circular)
   - `traefik_log_masker._CPF` → alias `_CPF_PATTERN`
   - `pii_sanitizer._CPF_RE` → **NAO refatorado** porque usa `m.group(1)`
     (regex com parens), enquanto o canonico não tem. Documentado em
     comment block do pii_sanitizer.

4. **Não quebrar nenhum import pre-existente**:
   `app/services/pii.py`, `app/utils/output_safety.py`,
   `app/services/mcp_pii.py`, `app/utils/pii_sanitizer.py`,
   `app/services/crypto.py`, `app/services/traefik_log_masker.py`,
   `app/models/cpf_cnpj_validator.py`, `app/services/log_masker.py`
   continuam com **funções inalteradas** — apenas o que foi tocado:
   - `mcp_pii.py`: regex duplicado removido + import lazy
   - `traefik_log_masker.py`: regex `_CPF` virou alias (regex string
     idêntica, `compiled` objeto igual)
   - `pii_sanitizer.py`: só docstring estendido (zero mudança runtime)

## Testes (47 PASSED, 206 PASSED PII suite)

`backend/tests/test_pii_unified_g8.py` — 11 classes cobrindo:

- `TestUnifiedMaskFull` (5) — full LGPD scrub por kind
- `TestUnifiedMaskPartial` (5) — partial reveal `***789-00`
- `TestUnifiedEdgeCases` (5) — None/empty/whitespace/trim/shortcut
- `TestUnifiedNoLeak` (8) — **REGRESSAO LGPD-46**, 6 CPFs sample
  (validos + invalidos) parametrizados x 2 modos; nenhum pode vazar
- `TestUnifiedDeterminism` (4) — idempotencia + hash_pii salt changes
- `TestUnifiedReExports` (7) — scrub/detect_only/hash_pii/validate_*
  via unified retorna o MESMO objeto/resultado que o canonico
- `TestUnifiedMcpPattern` (3) — `_CPF_PATTERN` é o compiled de
  `_PATTERNS["cpf"]`; `mcp_output_has_raw_cpf` reusa
- `TestUnifiedDeprecationNotice` (1) — emite warning
- `TestUnifiedPiiKindLiteral` (2) — type-check passa
- `TestPiiSanitizerRgKnownGap` (1) — **DOC-ONLY**: pin do gap conhecido
  em sanitize_rg (RG com pontos) — corrigir em task separada

Baseline vs after:
- 294 → **341 passed** (+47 from new tests)
- PII + MCP + output_safety suites combinadas: **206 passed** em 1.78s
- Ruff: **clean** (0 errors em 5 files tocados)
- Mypy: **0 errors** em 5 files
- Lazy import em `mcp_output_has_raw_cpf` quebra ciclo

## LGPD Review Gate (P0 — pre-merge)

Tarefa toca `pii*` então cross-review `cartorio-lgpd` é
**OBRIGATORIA** antes de merge. Notas para review:

1. **Nenhum regex novo foi adicionado.** Apenas re-exportado
   `_PATTERNS["cpf"]` como `_CPF_PATTERN` (mesma string,
   `\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b`, P0.5 ordem preservada).
2. **Ordem dos 13 regex em `_PATTERNS`** não foi tocada. CSP/CNH/CEP
   guards continuam identicos. Re-rodar `pytest tests/test_pii.py`
   valida.
3. **`pii_sanitizer.sanitize_rg` gap** (RGs com pontos passam direto)
   está DOCUMENTADO em `TestPiiSanitizerRgKnownGap` — correcao do
   regex fica para task separada (mudaria semantica de teste
   pre-existente).
4. **Bug pre-existente encontrado** em
   `app/api/v1/telegram.py:1213`: importa `hash_cpf` que nao existe
   e cai em fallback de `sha256` **unsalted**. Inseguro para LGPD
   porque hash sem salt permite cross-user lookup. **FORA DE ESCOPO**
   desta task, listada em `notes` para follow-up G8.12.T1+
   ou nova task.
5. **`pii_unified.mask(partial=True)`** deve ser usado APENAS em
   logs internos / debug / telemetria com contexto. Documentado em
   docstring + header do `pii_sanitizer`. Outputs HTTP publicos
   devem usar `mask(partial=False)` ou `scrub()` direto.

## Anti-patterns evitados

- NAO reescrever `pii.py` (P0.5)
- NAO unificar `scrub_response` com `scrub_mcp_output` (semantica
  ligeiramente diferente — `mcp_pii` tem `_SENSITIVE_KEYS` que força
  redacao mesmo se scrub não matcheou mas tem digits; fora do escopo
  DRY puro)
- NAO adicionar dep externa para PII masking (continua usando stdlib
  `re` + `hashlib`)
- NAO capturar `DeprecationWarning` com `warnings.filterwarnings`
  (mascara debt)

## Honesty Gate (Lesson 216)

- `cd backend && uv run pytest tests/test_pii_unified_g8.py --no-cov -v`
  → **47 PASSED**
- `cd backend && uv run pytest -k "pii" --no-cov -q` → **341 PASSED**
  (294 baseline + 47 novos)
- `cd backend && uv run pytest -k "pii or mcp" --no-cov -q`
  → **400 PASSED** (após merge com mcp tests)
- `cd backend && uv run ruff check app/` → **0 errors**
- `cd backend && uv run mypy app/` → **1 error** (pre-existente
  em `traefik_lobechat_routing.py` por falta de stub `yaml`; **NAO
  introduzido por esta task** — confirm via `git log` do arquivo
  vs HEAD)
- Lesson criada ✅
- PROGRESS.md append (abaixo)

## Progresso honesto

- **G8.12.T1**: `[x]` (artefato: `app/services/pii_unified.py` 222 LOC
  + `tests/test_pii_unified_g8.py` 350 LOC + 3 arquivos de-para
  regex duplicado)
- Wave 44 honest count: 49 → **50/100** (+1)

Modified by Gustavo Almeida + cartorio-dev (G8 Wave 44 — 2026-07-18).
