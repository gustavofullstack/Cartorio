# D24 — DPO Contato Publicado

> **Status:** ✅ DONE 2026-07-02 (lesson 139d)
> **Aplicar:** Site, dashboard, comprovantes, WhatsApp, Telegram, scripts
> **Owner:** Gustavo Almeida (interino) → contratação formal em 2027

---

## 📍 DPO Atual

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║  👤 Encarregado de Tratamento de Dados (DPO)                 ║
║  ─────────────────────────────────────────────────────────── ║
║                                                                ║
║  Nome: Gustavo Almeida (interino até 2027-Q1)                 ║
║  Email: dpo@2notasudi.com.br                                  ║
║  Telefone: (34) 9999-9999                                     ║
║  Idioma: Português (English on request)                       ║
║                                                                ║
║  Disponível: Segunda a Sexta, 9h-17h BRT                      ║
║  Resposta: até 15 dias úteis (LGPD art. 18 §5º)              ║
║                                                                ║
║  Contato ANPD (em caso de não-resposta):                      ║
║  https://www.gov.br/anpd                                      ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 📍 Onde o Contato Deve Aparecer

### 1. Site Principal
- ✅ Footer de todas as páginas (rodapé fixo)
- ✅ Página `/contato` dedicada
- ✅ Página `/privacidade` (D23)
- ✅ Banner D19 (consentimento)

### 2. App Admin / Dashboard
- ✅ Sidebar (link "DPO")
- ✅ Cabeçalho (badge pequeno canto superior)
- ✅ Footer (com nome + email)
- ✅ Modal de auditoria (contato para reportar)

### 3. Comprovantes / Recibos / Certidões
- ✅ Rodapé impresso contém: "Reclamações: dpo@2notasudi.com.br"
- ✅ QR Code opcional para `https://cartorio.2notasudi.com.br/dpo`

### 4. WhatsApp Business
- ✅ Descrição do negócio: "...DPO: dpo@2notasudi.com.br"
- ✅ Mensagem de boas-vindas: menciona DPO
- ✅ Comando `/dpo` retorna card de contato
- ✅ Comando `/lgpd` retorna card de direitos + contato DPO

### 5. Telegram Bot
- ✅ Mensagem `/start`: menciona DPO no footer
- ✅ Comando `/dpo` retorna contato
- ✅ Comando `/privacidade` retorna URL policy + contato DPO

### 6. Email
- ✅ Assinatura de TODOS os emails: Gustavo Almeida | DPO | dpo@2notasudi.com.br
- ✅ Auto-reply em horário fora: contatar dpo@2notasudi.com.br

### 7. Contratos Físicos
- ✅ Cláusula obrigatória em contratos: "Para reclamações LGPD, contatar dpo@2notasudi.com.br"
- ✅ Versão simplificada em linguagem jurídica

---

## 🔄 Atualização do Contato

Caso mude de DPO:
1. **30 dias antes:** notificar todos os canais (email + banner site + bot)
2. **Email oficial** aos titulares consentidos: novo DPO + email novo
3. **Atualizar policy D23**
4. **Atualizar HTML/PDF/UI** em todos os pontos
5. **Audit log** registrando a mudança

---

## 📚 Histórico

| Período | DPO | Observação |
|---|---|---|
| 2024-2026 | (sem DPO formal) | Operação direta por Gustavo |
| 2026-2027 | Gustavo Almeida (interino) | Período de transição + contratação |
| 2027+ | Profissional externo (TBD) | Contratação formal conforme LGPD art. 41 |

---

## 🔧 Configuração Backend

```python
# app/config.py (já configurado)
dpo_email: str = "dpo@2notasudi.com.br"
dpo_name: str = "Gustavo Almeida (interino)"
dpo_response_sla_days: int = 15  # LGPD art. 18 §5º

# Endpoint para titular contatar DPO
@app.post("/api/v1/lgpd/dpo/contact")
async def dpo_contact(request: Request, ...):
    """Recebe mensagem do titular, cria ticket interno LGPD.
    Audit: actor=cliente, action=lgpd.dpo.contact.
    SLA: 15 dias para resposta (response gerada por DPO).
    """
```

---

**Owner:** Gustavo Almeida (DPO interino)  
**Atualização:** anual ou em 30 dias antes de mudança
