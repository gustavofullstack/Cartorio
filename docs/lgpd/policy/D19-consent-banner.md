# D19 — Consent Banner LGPD 2026

> **Status:** ✅ DONE 2026-07-02 (lesson 139d)
> **Versão:** LGPD 2026.1
> **Base legal:** Lei 13.709/2018 (LGPD) art. 7º I + 8º
> **Aplicar em:** Web (cartório.2notasudi.com.br), Bot Telegram, Bot WhatsApp, Presencial (totem/check-in)

---

## 1. Banner Web (Padrão)

```
┌─────────────────────────────────────────────────────────────┐
│  🔒 Seus dados pessoais estão protegidos pela LGPD        │
│                                                             │
│  Ao continuar, você consente com o tratamento dos seus     │
│  dados pessoais para:                                       │
│                                                             │
│  ✓ Atendimento cartorário (obrigação legal — Prov. 74/2018)│
│  ✓ Comunicação sobre seus processos                        │
│  ✓ Melhoria dos nossos serviços                            │
│                                                             │
│  Você pode REVOGAR este consentimento a qualquer momento.   │
│  📧 dpo@2notasudi.com.br | 📞 (34) 9999-9999                │
│                                                             │
│  [ ☐ Li e concordo ]    [ Saber mais ]    [ Recusar ]       │
└─────────────────────────────────────────────────────────────┘
```

**Requisitos técnicos:**
- Versão 2026.1 com fingerprint de aceite (timestamp + IP truncado /24)
- Checkbox obrigatório antes de continuar
- Link "Saber mais" → D23 (Privacy Policy v2)
- Botão "Recusar" mantém serviços obrigatórios (LGPD art. 7º II)

---

## 2. Mensagem Bot Telegram/WhatsApp (consentimento inicial)

```
🔒 Antes de continuarmos, preciso do seu consentimento LGPD.

Ao aceitar, autorizo o 2º Cartório de Notas a:
  ✓ Armazenar meu nome, CPF, RG para atendimento
  ✓ Enviar atualizações dos meus protocolos
  ✓ Processar pagamentos via Woovi/Pix

Posso revogar a qualquer momento via este chat ou e-mail
dpo@2notasudi.com.br.

Base legal: Lei 13.709/2018 (LGPD) art. 7º, I.

[ SIM ]   [ NÃO ]   [ VER POLÍTICA COMPLETA ]
```

---

## 3. Implementação Backend (consent_log table)

```sql
CREATE TABLE consent_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id UUID REFERENCES clientes(id),
    versao_banner VARCHAR(20) NOT NULL,  -- 'LGPD-2026.1'
    aceite BOOLEAN NOT NULL,
    ip_truncado INET,                    -- /24 IPv4, /48 IPv6
    user_agent_hash VARCHAR(64),          -- SHA-256 do UA
    canal VARCHAR(20) NOT NULL,           -- 'web', 'telegram', 'whatsapp', 'presencial'
    contexto JSONB,                       -- {page, referrer, etc}
    registrado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_consent_log_cliente ON consent_log(cliente_id);
CREATE INDEX idx_consent_log_versao ON consent_log(versao_banner);
```

---

## 4. Métricas de aceite

- Taxa de aceite: target >85% em interações web
- Taxa de revogação: target <5% em 30 dias
- 100% das revogações processadas em <5min (D31)

---

## 5. Auditoria

- Log de aceite com audit_action = `consent.banner.aceito`
- Log de revogação com audit_action = `consent.banner.revogado`
- Retenção: 5 anos (LGPD art. 37 + 50 + Provimento 74/2018)

---

## 6. Próxima revisão

- **Data:** 2027-01-01 (anual) ou em caso de mudança legislativa
- **Owner:** cartorio-lgpd
- **Reviewers:** Gustavo Almeida + DPO

---

**Aprovações:**
- [ ] cartorio-lgpd (Pietra) — autor
- [ ] Gustavo Almeida — DPO nominal
