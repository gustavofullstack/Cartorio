# D21 — Privacy by Design — Checklist de Revisão

> **Status:** ✅ DONE 2026-07-02 (lesson 139d)
> **Aplicar:** Em todo novo endpoint, feature, ou refactor de produção
> **Base legal:** LGPD art. 46 + 47 + boas práticas ANPD

---

## 📋 9 Itens Obrigatórios

| # | Item | Verificação | LGPD art. |
|---|---|---|---|
| 1 | **Finalidade específica** declarada | `purpose` field em todos os endpoints | 6º IX |
| 2 | **Necessidade** (minimalidade) | Apenas dados estritamente necessários | 6º III |
| 3 | **Base legal** explícita | `legal_basis` em responses/audit | 7º |
| 4 | **PII scrub** antes de LLM externa | `pii.scrub()` em todo payload | 50 |
| 5 | **Audit log** completo | `AuditService.log()` em toda mutação | 37 |
| 6 | **Retenção** definida | Job retenção cobre o caso | 16 |
| 7 | **Direitos titular** acessíveis | Endpoint LGPD correspondente | 18 |
| 8 | **IP truncado** em responses | `/24` IPv4, `/48` IPv6 | 50 |
| 9 | **Sem default permissivo** | Opt-in explícito para coletas extras | 8º |

---

## 🔍 Uso (PR Review obrigatório)

```markdown
## PR [NUMBER] — Privacy by Design Checklist

- [ ] Item 1: Finalidade específica
- [ ] Item 2: Necessidade
- [ ] Item 3: Base legal
- [ ] Item 4: PII scrub (pii.scrub() aplicado?)
- [ ] Item 5: Audit log (AuditService.log() em mutação?)
- [ ] Item 6: Retenção (job cobre o caso?)
- [ ] Item 7: Direitos titular (endpoint LGPD existe?)
- [ ] Item 8: IP truncado
- [ ] Item 9: Sem default permissivo
```

---

## 📋 Templates de Resposta

### Endpoint OK (autorizado merge)

```markdown
✅ Privacy by Design — todos os 9 itens verificados
- Finalidade: <purpose>
- Necessidade: <campos_coletados>
- Base legal: LGPD art. Xº <inciso>
```

### Endpoint com issues

```markdown
⚠️ Privacy by Design — itens pendentes:
- Item 4: PII scrub NÃO aplicado em <campo_x>
- Item 9: Existe default permissivo — mudar para opt-in

Bloqueio de merge até correção.
```

---

## 📚 Referências

- LGPD art. 46 (medidas de segurança)
- LGPD art. 47 (sistemas de tratamento)
- ANPD Guia Orientativo — Boas Práticas (2023)
- Provimento 74/2018 CNJ

---

## 🔄 Revisão

- Trimestral pelo cartorio-lgpd
- Auditoria anual externa (D25)
- Owner: cartorio-lgpd
