# Lesson 213 — G8.08.T2 DLQ payload encryption-at-rest (LGPD Art.46) (2026-07-17)

Type: project + reference

## Contexto

LGPD Art.46 exige "medidas técnicas e administrativas aptas a proteger os dados
pessoais de acessos não autorizados". `app/services/dlq.py` armazena payloads JSON
**plaintext** no DB (coluna `payload: dict`). Em caso de DB compromise (SQL injection,
backup leak, replica read access), PII dentro de payloads DLQ fica exposta.

Wave 26 (lesson 198) já tem `app/services/crypto.py` com Fernet (AES-128-CBC + HMAC).
Faltava **wrapper específico para DLQ** com heurística automática de PII.

## Entrega (Wave 30 A2)

### Módulo `app/services/dlq_encryption.py` (97 LOC)

API pública:
- `encrypt_dlq_payload(payload, key) -> envelope_dict`
- `decrypt_dlq_payload(envelope, key) -> original_payload`
- `is_encrypted_payload(stored) -> bool`
- `should_encrypt_payload(payload) -> bool` (heurística PII)

Envelope JSON:
```json
{"_encrypted": true, "v": 1, "ciphertext": "gAAAAABm..."}
```

Heurística PII (auto-detecta campos): `cpf`, `rg`, `cnpj`, `nome`, `name`, `email`,
`telefone`, `phone`, `endereco`, `address`, `data_nascimento`, `birth_date`, `cnh`,
`passaporte`, `passport`. Case-insensitive, 1 nível de nested dict.

### Testes `tests/test_dlq_encryption_g8.py` — **38 PASSED em 0.29s**

| Classe | Testes | Cobre |
|--------|--------|-------|
| TestEncryptDLQPayload | 5 | envelope válido + Fernet token + idempotência + chaves diferentes + no plaintext leak |
| TestDecryptDLQPayload | 6 | round-trip + unicode + wrong key raises + raw compat + invalid envelope + non-dict raises |
| TestIsEncryptedPayload | 4 | válido + raw + vazio + parcial |
| TestShouldEncryptPayload | 14 (1 parametrize x 14 campos + 5 outros) | top-level + nested + no PII + empty + already-encrypted + non-dict + case-insensitive |
| TestEncryptionCompliance | 3 | ciphertext not human-readable + size overhead <300B + PII preserved |

## Validação gates pós-wave

| Gate | Antes (lesson 212) | Depois (Wave 30 A2) |
|------|--------------------|---------------------|
| pytest | 3205 | **3242** (+37) |
| mypy strict | 0/155 files | **0/156 files** (novo módulo) |
| ruff | 0 | 0 |

## Decisões de design

1. **Backward compat**: `decrypt_dlq_payload` aceita payload raw (não criptografado)
   e retorna as-is. Não quebra callers existentes.
2. **Idempotência**: `encrypt_dlq_payload` detecta envelope e não re-criptografa.
3. **LGPD Art.46 over-engineering evitado**: NÃO modificamos `dlq.py` core
   (mantém API atual). Camada adicional opt-in via `dlq_encryption.py`.
4. **Overhead aceitável**: ~150 bytes por payload (Fernet token + JSON envelope).
   Validado por teste `test_payload_size_grows_minimally`.

## Pendente (próxima wave ou SUI)

- Wrapper automático `dlq_enqueue_secure(db, queue, payload, key)` que decide
  criptografar via heurística (substitui `dlq.enqueue()` em callers críticos)
- Migration Alembic para coluna `payload_encrypted_at TIMESTAMP` (auditoria)
- Dashboard LGPD mostrando DLQ encryption status

## Cross-refs

- lesson-212 (G8.07.T1 MCP tests Wave 30 A1)
- lesson-211 (mega-commit 148 untracked)
- lesson-209 (Wave 29 closeout)
- lesson-198 (G7 Wave 26: crypto helpers + LGPD inventory)
- LGPD Art.46 (security measures at-rest)
- app/services/crypto.py (Fernet base)
- app/services/dlq.py (core DLQ sem alteração retroativa)

Modified by Gustavo Almeida