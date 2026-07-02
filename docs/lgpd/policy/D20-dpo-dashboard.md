# D20 — DPO Dashboard (Métricas LGPD)

> **Status:** ✅ DONE 2026-07-02 (lesson 139d)
> **Métricas:** consents / exports / queixas / direitos exercidos
> **Endpoint:** `GET /api/v1/lgpd/dashboard` (já implementado em D26)
> **Auth:** JWT + role `dpo=true`

---

## 1. Métricas Rastreadas

| Métrica | Query/Agregação | Retenção |
|---|---|---|
| `consents_total` | count(distinct cliente_id WHERE consent=true) | histórica |
| `consents_ativos` | count WHERE consent=true AND revoked_at IS NULL | snapshot |
| `consents_revogados_30d` | count WHERE revoked_at >= NOW()-30d | rolling |
| `exports_solicitados_30d` | count audit_log WHERE action='lgpd.cliente.export' AND time >= NOW()-30d | rolling |
| `queixas_30d` | count WHERE tipo='reclamacao' AND status='aberto' | rolling |
| `direitos_exercidos_30d` | group by tipo (acesso/correcao/portab/etc) | rolling |
| `audit_chain_integrity` | boolean (verify_chain() == true) | snapshot |
| `consent_banner_aceites_24h` | count WHERE versao='LGPD-2026.1' AND registrado_em >= NOW()-24h | rolling |

---

## 2. UI Sugerida (React + Vite)

```
┌────────────────────────────────────────────────────┐
│  📊 DPO Dashboard — 2º Cartório de Uberlândia      │
│                                                    │
│  Audit chain: ✅ INTACTA                           │
│                                                    │
│  ┌─────────────┬─────────────┬─────────────┐       │
│  │  Consents   │  Exports    │  Queixas    │       │
│  │   4.523     │   127 (30d) │   3 (30d)   │       │
│  │  ativos     │             │  abertas    │       │
│  └─────────────┴─────────────┴─────────────┘       │
│                                                    │
│  📊 Direitos exercidos (últimos 30 dias):           │
│    Acesso (D18 art. IV)    : 12                    │
│    Correção (D18 art. III) :  5                    │
│    Portabilidade (D18 V)   :  3                    │
│    Eliminação (D18 VI)     :  7                    │
│    Revogação (D31)         :  9                    │
│    Anonimização (D28)      : 11                    │
│                                                    │
│  ⚠️ Alertas:                                        │
│  - Consent banner v2026.1 aceito por 89% (target 85%)│
│  - 1 backup pendente verificação                     │
└────────────────────────────────────────────────────┘
```

---

## 3. Implementação Frontend

- **Path:** `app/admin/dpo-dashboard.tsx` (já estrutura admin pronta)
- **Auth check:** JWT + dpo=true (redirecionar se não for DPO)
- **Refresh:** auto 60s (com botão "atualizar agora")
- **Export CSV:** botão direito (audit exportar últimos 90 dias)

---

## 4. SLAs e Notificações

- **Latência:** dashboard renderiza em <2s com cache 30s
- **Refresh:** invalidar cache em `consent.register` ou `consent.revoke`
- **Notificações Telegram GRUPO:**
  - Audit chain quebrada → imediato
  - Queixa aberta → imediato
  - 3+ exports em 1h (suspeita) → imediato

---

## 5. Acesso

- **DPO nome:** Gustavo Almeida (interino até contratação formal)
- **Email:** dpo@2notasudi.com.br
- **Acesso dashboard:** somente via VPN Tailscale (rede privada)

---

## 6. Próxima revisão

- **Data:** 2027-01-01 ou após 50+ queixas/30d (sinal de stress)
- **Owner:** cartorio-lgpd
