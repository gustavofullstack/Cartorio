# Lesson 253 — G8.18.T1: Ampliar regex PII interceptor pré-LLM (2026-07-18)

## Contexto

Tarefa do SUPER_PLANO_G8_SQUAD_18 (LGPD-by-design hardening):
**G8.18.T1 — "Ampliar expressões regulares e dicionários de termos
sensíveis do interceptor pré-LLM."** Wave 49, 66/100.

Análise inicial revelou que o brief da task **listava como "novos"
patterns que já existiam** desde 2026-06-23 (LGPD-015 Sprint 3):

| Pattern | Brief | Já existe? | Onde |
|---------|-------|-----------|------|
| CNS | sim | **sim** (desde 2026-06-23) | `_PATTERNS["cns"]` keyword-anchored |
| CNH | sim | **sim** (desde 2026-06-23) | `_PATTERNS["cnh"]` keyword-anchored |
| PIS | sim | **sim** | `_PATTERNS["pis"]` formato 3-5-3 |
| Título | sim | **sim** | `_PATTERNS["titulo_eleitor"]` 4-4-4 |
| Email | sim | **sim** | `_PATTERNS["email"]` |

Adicionar padrões duplicados (CNS/CNH/PIS/Titulo loose) **teria
quebrado a P0.5 ordem crítica** (CNS loose antes de phone_br loose;
CNH loose antes de CPF loose) e introduzido FPs sistêmicos contra
ISBN/OAB/CNJ/CEP — exatamente o que a arquitetura atual combate.

## Decisão arquitetural

1. **NÃO duplicar padrões existentes.** CNS/CNH/PIS/Titulo/Email
   já cobrem os casos do brief com semântica **mais correta**
   (keyword-anchored evita FP).

2. **Adicionar apenas padrões genuinamente novos:**
   - `pix_cpf_keyword` (14) — detecta "pix cpf <11dig>" antes do
     cpf loose capturar. Aceita formato com/sem pontuação.
   - `passport` (15) — passaporte brasileiro AA1234567 (ICAO 9303).
     Uppercase-only (ICAO MRZ) para anti-FP contra texto natural.
   - `ip` (16) — IPv4 para LGPD v2 contexto (logs de acesso).

3. **Adicionar 3 mask helpers parciais:**
   - `mask_cns(cns)` → `***.***.***-***` (15 dig) ou `***.***.***-****` (16)
   - `mask_cnh(cnh)` → `***********`
   - `mask_pis(pis)` → `***.***.***-**`
   - Idempotentes: se input só tem `*`/pontos, retorna input.

4. **Atualizar header do módulo** com inventário numerado dos 16
   patterns e nota explícita "LGPD-REVIEW-PENDING" Wave 49.

## Bugs encontrados durante TDD

1. **pix_cpf_keyword com pontuação não matcheava.** Primeira versão
   da regex exigia `\d{11}` contíguo. Caso real de cliente envia
   "pix cpf 123.456.789-00" (com pontuação). Fix: aceitar ambos
   formatos — `(?:\d{11}|\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b`.

2. **Ordem invertida após primeiro edit.** `pix_cpf_keyword` foi
   inserido como "7b" DEPOIS de `cpf` (linha 169 vs 162). Como o
   edit substituiu o bloco do cpf+comentário "7b" mas deixou
   "7b" abaixo, o dict insertion order ficou `cpf` antes de
   `pix_cpf_keyword`. **CPF loose capturava primeiro** e o keyword
   não tinha mais o que matchear. Fix: trocar os blocos para
   `pix_cpf_keyword (7)` → `cpf (8)`.

3. **Mask helpers não-idempotentes.** Primeira versão retornava
   `***.***.***-***` quando input era já mascarado (sem dígitos).
   Fix: extrair dígitos; se zero dígitos, retornar input como está.

## Testes (22 novos PASSED, 99 totais em test_pii.py)

Novos tests cobrindo:
- `test_scrub_pix_cpf_keyword` (3 cenários: puro, com separador, case-insensitive)
- `test_scrub_pix_sem_cpf_nao_detectado` (anti-FP: só "pix" não matcheia)
- `test_scrub_passport_br` + lowercase + OAB (anti-FP)
- `test_scrub_ip_pattern` (2 cenários) + IPv6 não matcheia
- `test_scrub_no_false_positive_phone_vs_cnh` + ISO date
- `test_scrub_combined_all_new_patterns` (3 patterns juntos)
- `test_scrub_combined_with_existing_patterns` (16 patterns juntos)
- 8 tests de mask helpers (cns/cnh/pis + formatacao + idempotencia)

Baseline vs after:
- test_pii.py: 77 → **99 passed** (+22)
- Suite pii completa (`-k pii`): 382 → **404 passed** (+22)
- 6 arquivos pii: **193 passed** em 2.14s
- Ruff: **0 errors** em pii.py e test_pii.py
- Mypy: **0 errors** em pii.py

## LGPD Review Gate (P0 — pre-merge)

Tarefa toca `pii*` então cross-review `cartorio-lgpd` é
**OBRIGATORIA** antes de merge prod. Notas para review:

1. **Padrões CNS/CNH/PIS/Titulo/Email NÃO foram duplicados.** O
   brief sugeria adição, mas eles já existem com semântica
   keyword-anchored desde LGPD-015 Sprint 3 (2026-06-23). Adicionar
   duplicatas loose quebraria a P0.5 ordem crítica. Decisão
   registrada no header do módulo.

2. **3 padrões genuinamente novos:** pix_cpf_keyword (com keyword
   "pix cpf" para desambiguar de CPF puro), passport (uppercase
   ICAO MRZ para anti-FP), ip (IPv4 only, IPv6 não coberto).

3. **3 mask helpers parciais:** distintos de scrub() (full LGPD
   redaction) — preservam formato mas escondem conteúdo, úteis
   para UI interna / debug / telemetria. **NUNCA usar em output
   HTTP público** (usar `scrub()` / mask full).

4. **Ordem dos 16 patterns em `_PATTERNS`** não foi quebrada para
   os padrões existentes. Re-rodar `pytest tests/test_pii.py`
   valida que todos os 77 tests originais continuam passando.

5. **PIX-CPF keyword aceita CPF com/sem pontuação** — caso real
   de cliente via chatbot. Sem keyword "pix cpf", 11 dígitos
   continua sendo CPF puro (comportamento LGPD preservado).

## Anti-patterns evitados

- NAO duplicar patterns já existentes (CNS/CNH/PIS/Titulo/Email)
- NAO criar patterns loose 11-digit que colidiriam com CPF
- NAO usar IPv6 regex (escopo do task = IPv4 only; IPv6 fica
  para task separada com discussão de falsos positivos)
- NAO capturar DeprecationWarning nos mask helpers (mascara debt)
- NAO retornar string diferente quando input já é mascarado
  (idempotência é propriedade útil)

## Honesty Gate (Lesson 216)

- `cd backend && uv run pytest tests/test_pii.py --no-cov -v`
  → **99 PASSED** (77 baseline + 22 novos)
- `cd backend && uv run pytest -k "pii" --no-cov -q`
  → **404 PASSED** (382 baseline + 22 novos)
- `cd backend && uv run pytest tests/test_pii.py tests/test_pii_unified_g8.py tests/test_pii_validators.py tests/test_pii_bench.py tests/test_pii_performance.py tests/test_pii_sanitizer.py --no-cov -q`
  → **193 PASSED** em 2.14s
- `cd backend && uv run ruff check app/services/pii.py tests/test_pii.py`
  → **0 errors**
- `cd backend && uv run mypy app/services/pii.py`
  → **0 errors**
- Lesson criada ✅
- LGPD-REVIEW-PENDING tag no commit message ✅

## Progresso honesto

- **G8.18.T1**: `[x]` (artefato: `app/services/pii.py` +128 LOC
  + `tests/test_pii.py` +164 LOC, 3 patterns + 3 helpers + 22 tests)
- Wave 49 honest count: 66 → **66/100** (mesma task, sem delta de count)

Modified by Gustavo Almeida + cartorio-lgpd (G8 Wave 49 — 2026-07-18).