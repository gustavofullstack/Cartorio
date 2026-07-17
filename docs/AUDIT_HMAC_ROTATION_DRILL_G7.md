# Audit HMAC Key Rotation Drill (G7.02.T4)

**NÃO executar em produção sem janela de manutenção.**  
Audit chain assina cada entry com `AUDIT_HMAC_KEY`. Troca ingênua **quebra**
`verify_chain` / validação HMAC de entries antigas.

---

## Modelo de risco

| Cenário | Efeito |
|---------|--------|
| Rotacionar key única sem dual-verify | verify_chain / HMAC check falha em entries antigas |
| Dual-key (current + previous) | entries novas com key N; verify tenta N depois N-1 |
| Perder key antiga | impossível revalidar era anterior (anexar report forense) |

---

## Drill dry-run (staging / local)

1. **Snapshot**
   ```bash
   # export last N audit positions + chain tip
   curl -sS -X POST -H "X-API-Key: $CARTORIO_API_KEY" \
     https://api.2notasudi.com.br/api/v1/audit/verify
   ```
2. **Gerar key nova** (não commitar)
   ```bash
   openssl rand -hex 32
   ```
3. **Staging only:** set `AUDIT_HMAC_KEY_PREV=$OLD` + `AUDIT_HMAC_KEY=$NEW`
4. **Código necessário (se ainda não existir dual-key em verify):**
   - `AuditService._compute_hmac` usa current
   - `verify_hmac` tenta current, fallback PREV
   - Hoje (2026-07-16): implementação single-key — **drill documenta gap**
5. **Inserir 1 entry de teste** com key nova
6. **verify_chain** deve continuar ok para hashes (hash chain ≠ HMAC key)
7. **Rollback:** restaurar env antigo

---

## Diff hash chain vs HMAC

- **SHA256 chain** (`prev_hash` + payload + timestamp): independente da HMAC key  
- **HMAC signature**: depende da key do servidor  

Rotação de HMAC key **não** invalida a chain de hash, mas invalida checks de
assinatura se o código comparar só com a key atual.

---

## Cadência

- Rotação HMAC audit: **só com ADR + cartorio-lgpd sign-off**
- Preferir rotação de `CARTORIO_API_KEY` / webhook secrets (G7.10.T3) a rotação de audit HMAC
- Review gate: `cartorio-lgpd` + `cartorio-dev`

---

## Checklist dry-run (marcar)

- [ ] Staging com volume de audit real sample
- [ ] Dual-key code path merged (se for rotacionar)
- [ ] Backup DB antes
- [ ] verify_chain green pré/pós
- [ ] Lesson MEMORY após drill real

**Status G7.02.T4:** documentação + gap dual-key explícito (não forçar rotação prod).

**Modified by Gustavo Almeida + cartorio-lgpd — G7 Wave 20**
