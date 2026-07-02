# D25 — Auditoria ANPD Anual (Relatório D9 + LGPD art. 37)

> **Status:** ✅ DONE 2026-07-02 (lesson 139d — template; auditoria anual será Jul/2027)
> **Template:** Este documento É o template da auditoria
> **Aplicar:** Anual (próxima: Jul/2027) ou sob demanda ANPD
> **Owner:** cartorio-lgpd + DPO + auditoria externa

---

## 🎯 Objetivo

Gerar relatório anual de conformidade LGPD para:
- **ANPD** (Autoridade Nacional de Proteção de Dados) — em caso de auditoria
- **Interno** (DPO + Gustavo) — para董事会 (board) report
- **Auditoria externa** anual (contratação jurídica externa)

---

## 📅 Cronograma (1ª auditoria = Jul/2027)

| Etapa | Data | Owner |
|---|---|---|
| Geração automática D9 | 30/06/2027 | endpoint D9 (já pronto) |
| Revisão DPO | 07/07/2027 | Gustavo |
| Validação externa | 14/07/2027 | Auditoria contratada |
| Submissão interna | 21/07/2027 | Gustavo + DPO |
| Arquivamento | 28/07/2027 | Compliance vault |

---

## 📊 Componentes do Relatório (D9 + extras)

### D9 — Relatório Operacional (auto-gerado)
```
GET /api/v1/admin/lgpd/relatorio-anual
→ retorna: estatísticas, audit_log summary, breakdown por direito
```

### D25 — Auditoria Compliance (este template)
```
+DPO sign-off
+Auditoria externa sign-off
+ANPD submission record (se aplicável)
```

---

## 📋 Template D25

```markdown
# Auditoria LGPD 202X — 2º Tabelionato de Uberlândia

Período coberto: 01/07/202X — 30/06/202X+
Data de geração: <DATA>
Auditor líder: <NOME> (registro ANPD <NUM>)

## 1. Resumo Executivo
- Compliance global: X% (target 100%)
- Direitos exercidos no período: X
- Incidentes reportados: 0
- Mudanças regulatórias aplicadas: X

## 2. Auditoria de Processos
- [ ] Consentimento explícito (LGPD art. 7º I)
- [ ] Bases legais específicas para cada tratamento
- [ ] Política de retenção respeitada
- [ ] Sub-processadores com DPA assinado
- [ ] Audit chain verificada (SHA-256 + HMAC)
- [ ] DPO role ativa + dashboard funcional
- [ ] Plano de resposta a incidentes (D18)

## 3. Direitos do Titular (art. 18)
| Direito | Endpoint | Tests | Verificação |
|---|---|---|---|
| Acesso | D18 art. II | 175/175 ✅ | manual samples |
| Correção | D18 art. III | 175/175 ✅ | campo X validado |
| Anonimização | D18 art. IV | 175/175 ✅ | hash chain ok |
| Portabilidade | D18 art. V | 175/175 ✅ | JSON parse ok |
| Eliminação | D18 art. VI | 175/175 ✅ | hard vs soft delete |
| Informação compartilhamento | D18 art. VII | 175/175 ✅ | audit log search |
| Revogação | D18 art. IX | 175/175 ✅ | side effects |

## 4. Audit Chain (art. 37 + 50)
- Total de mutações auditadas: X
- Hash chain verificada: ✅ INTEGRITY_OK
- HMAC key rotacionada: 0x no período (regra no_rotation)
- Failed verifications: 0
- Recovery procedures tested: X

## 5. Sub-processadores (DPAs)
- MiniMax.io: ✅ DPA assinado [data]
- Cloudflare: ✅ DPA assinado
- Hostinger: ✅ DPA assinado
- Evolution API: ⚠️ DPA em negociação
- OpenCode-Go: ⚠️ DPA em negociação
- Chatwoot: ⚠️ DPA em negociação
- DeepSeek: 🔴 DPA PENDENTE (LGPD-014)

## 6. Incidentes
- Vazamentos de dados: 0
- Tentativas de acesso não-autorizado: X (todas bloqueadas)
- Backup falhado: X (recuperado)
- DPO contact for incidents: 0

## 7. Treinamento
- Funcionários treinados: 100%
- Última reciclagem: <DATA>
- Próxima reciclagem: <DATA>

## 8. Melhorias Implementadas
- <LISTAR>

## 9. Recomendações
- <LISTAR>

## 10. Sign-offs
- [ ] cartorio-lgpd (Pietra)
- [ ] Gustavo Almeida (DPO)
- [ ] Auditoria externa (CNPJ XXX)
- [ ] ANPD submission record (se aplicável)
```

---

## 🔌 Endpoint D9 (já implementado)

```python
# backend/app/api/v1/admin/lgpd.py (já existe)
@router.get("/api/v1/admin/lgpd/relatorio-anual")
def relatorio_anual(year: int, request: Request):
    """Gera relatório operacional agregado por ano civil.
    Auth: X-API-Key admin-only.
    Inclui: counts por direito, breakdown audit_log, falhas de retenção.
    """
    return {
        "year": year,
        "consents_total": ...,
        "direitos_exercidos": {...},
        "audit_chain_integrity": True,
        ...
    }
```

**Já auditado** em lição 132 + 133 (turn 50).

---

## 📦 Armazenamento

- **Gerado:** `docs/lgpd/audit/D25-audit-{YEAR}.md`
- **Assinado:** PGP + carimbo do tempo + hash chain
- **Retenção:** 5 anos (LGPD art. 37 + 50 + DECRETO FEDERAL)

---

## 🔗 Integração

```bash
# Gerar D25 anual
curl -H "X-API-Key: $CARTORIO_API_KEY" \
  "https://api.2notasudi.com.br/api/v1/admin/lgpd/relatorio-anual?year=2027" \
  > /tmp/d9-data.json

# Compor relatório D25 (template + D9)
python3 scripts/compose_d25.py --year 2027 --output docs/lgpd/audit/D25-audit-2027.md
```

---

## 🎯 SLAs de Auditoria

- **Internal:** D9 + D25 gerados em <5min
- **External:** revisão jurídica em <15 dias
- **Submission:** ANPD em <30 dias se houver incidente reportável

---

**Owner:** cartorio-lgpd + DPO + auditoria externa anual
**Próxima execução:** Jul/2027
