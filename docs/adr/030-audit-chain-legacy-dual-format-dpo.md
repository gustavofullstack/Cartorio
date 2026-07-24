# ADR-030: Audit chain legacy dual-format — decisão DPO sobre as 158 entradas trigger-written

**Data:** 2026-07-24
**Status:** PROPOSTA — aguardando sign-off cartorio-lgpd + decisão DPO
**Autor:** cartorio-chief (swarm G9) — evidências coletadas por audit-chain-verifier
**Superfície:** `app/services/audit*.py`, `alembic/versions/2026_07_24_0028-fix-fn-auto-audit-ts-consistency.py`
**Commit sob review:** `a84303bc` (fix(audit): root cause chain break)
**Regra P0:** `audit_log` é append-only. **Nunca** reescrever ou reencadear histórico unilateralmente.

## Contexto

Em 2026-07-24, `POST /api/v1/audit/verify` em produção retornava
`{"chain_ok": false, "last_valid_position": 667}`.

Root cause comprovada (dupla):

1. **Canonicalização divergente**: o trigger PL/pgSQL `fn_auto_audit` (migração
   0020, 2026-07-09) monta o bloco canônico com `v_payload::text` (formato
   `jsonb::text`: ordem (len, bytewise), separadores com espaço), enquanto o
   verificador Python usa `json.dumps(sort_keys=True, separators=(",",":"))`.
   Entradas escritas pelo trigger **nunca** recomputam no verificador Python.
2. **Timestamp hasheado ≠ armazenado**: o trigger hasheava
   `to_char(clock_timestamp(), ...)` mas gravava `NOW()` na coluna
   (divergência de microssegundos), tornando parte das entradas legacy
   impossível de re-verificar mesmo com mirror de formato.

**Evidência forense de NÃO-tampering:** `prev_hash` linkage 100% contínuo nas
1130 entradas. As 158 divergências são exclusivamente entradas sistemáticas
escritas pelo trigger desde 2026-07-09 — divergência de **formato**, não
adulteração de conteúdo.

## Fix implementado (commit a84303bc)

- **`audit.py`**: mirror `_compute_hash_sql_trigger` + fallback em
  `verify_chain` **somente** para entradas marcadas como trigger-written que
  recomputam EXATAMENTE no formato SQL. Link quebrado continua fail-closed.
- **Migração 0028** (originalmente numerada 0022; re-id por colisão de heads
  no grafo Alembic — ver nota W0 no próprio arquivo): trigger passa a hashear
  o MESMO `NOW()` gravado na coluna `timestamp` → entradas futuras sempre
  re-verificáveis no formato Python.
- **Testes:** `tests/test_audit_trigger_canonical_p0.py` — 14 testes (formato
  jsonb::text, canonical SQL, fallback verify_chain, tamper fail-closed,
  contrato estático da migração).

## Decisão requerida do DPO — entradas legacy (158)

Opções avaliadas:

| Opção | Descrição | Consequência |
|---|---|---|
| **A — Dual-format (RECOMENDADA, default)** | Manter histórico intacto; verificador aceita formato SQL apenas para entradas legacy trigger-written | Zero risco de destruição probatória; cadeia verifica ponta a ponta; complexidade do verificador +1 caminho controlado e testado |
| B — Anotação | Adicionar metadata fora da cadeia (tabela auxiliar) marcando as 158 como "formato legacy conhecido" | Histórico intacto, mas verificação ponta a ponta exige join externo |
| C — Re-cadeamento | Reescrever hashes das 158 e encadear novamente | **VIOLA append-only**; destrói valor probatório (LGPD art. 37, CNJ Prov. 74); quebra reprodução forense |

**Recomendação técnica: Opção A (default = no rewrite).** Nenhuma entrada do
`audit_log` será reescrita, independentemente da decisão final; se o DPO
preferir B, implementa-se a tabela auxiliar como ADR-031 sem alterar A.

## Evidências anexas (reproduzível)

- `uv run pytest --no-cov -q tests/test_audit_trigger_canonical_p0.py` → **14/14 passed**
- Família audit*/pii* (9 arquivos): **230 passed** (1.21s)
- `ruff check .` → All checks passed; `mypy app/` → 0 errors
- Prod baseline pré-deploy: `POST /api/v1/audit/verify` →
  `{"chain_ok":false,"last_valid_position":667}` (esperado — fix não deployado)
- Pós-deploy obrigatório: re-rodar verify em prod → esperado `chain_ok=true`
  (GO/NO-GO do release)

## Rollback

- Código: revert do commit `a84303bc` (verificador volta a falhar nas 158 —
  comportamento anterior conhecido, sem perda de dados).
- Migração 0028: `alembic downgrade 0027` restaura trigger anterior
  (divergência de ts retorna apenas para entradas futuras).

## Consequências

- Verificador passa a ter DOIS caminhos de canonicalização (Python + mirror
  SQL). O caminho SQL é restrito a entradas legacy identificadas; qualquer
  entrada nova que só recomputa em SQL indica regressão do trigger e deve
  falhar auditoria.
- Dead-man's switch (15 min) volta a reportar `chain_ok=true` após deploy.

**Sign-off cartorio-lgpd:** ______________  **Data:** ____/____/______
**Decisão DPO (A/B/C):** ______  **Data:** ____/____/______
