# D23 — Site Privacy Policy v2 (LGPD 2026)

> **Status:** ✅ DONE 2026-07-02 (lesson 139d)
> **Versão:** 2.0 (LGPD 2026)
> **Aplicar:** Site principal, dashboard admin, portal de agendamento
> **Owner:** cartorio-lgpd + revisão jurídica externa anual

---

## 📜 Versão Completa (Publicável)

### 1. Quem somos

```
2º Tabelionato de Notas e Protesto de Uberlândia
CNPJ: XX.XXX.XXX/0001-XX
Endereço: Av. XXXX, XXX, Uberlândia/MG, CEP 38.XXX-XXX
Telefone: (34) 9999-9999
Email: contato@2notasudi.com.br

Encarregado de Tratamento de Dados (DPO):
Nome: Gustavo Almeida (interino)
Email: dpo@2notasudi.com.br
Telefone: (34) 9999-9999
```

### 2. Quais dados pessoais coletamos

| Categoria | Exemplos | Base legal | Finalidade |
|---|---|---|---|
| Identificação | Nome, CPF, RG, CNH, passaporte | art. 7º II | Provimento 74/2018 (obrigação legal) |
| Contato | Email, telefone, endereço | art. 7º II + V | Notificações processo |
| Pagamento | Dados de transação Woovi/Pix | art. 7º V | Execução do serviço |
| Navegação | IP (truncado /24), user-agent | art. 7º IX | Segurança + analytics |
| Comunicações | Mensagens WhatsApp/Telegram | art. 7º I | Consentimento |

### 3. Para que usamos

- **Execução do serviço cartorário** (obrigação legal): escrituras, procurações, certidões, protestos
- **Comunicação**: atualizações de protocolo, agendamentos, recibos
- **Cobrança**: processar pagamentos e emitir notas fiscais
- **Segurança**: prevenir fraudes, cumprir obrigações legais
- **Marketing** (só com consentimento): informativo sobre serviços opt-in

### 4. Quanto tempo guardamos

| Tipo de dado | Retenção | Base legal | Após retenção |
|---|---|---|---|
| Protocolos lavrados | 5 anos | LGPD art. 7 II + Prov. 74/2018 | Anonimização |
| Mensagens WhatsApp/Telegram | 365 dias | LGPD art. 7 I (consentimento) | Exclusão ao revogar |
| Audit logs | 5 anos | LGPD art. 37 + 50 | Manter (sem PII) |
| Dados de pagamento | 5 anos | Legislação fiscal | Exclusão após prescrição |
| Marketing opt-in | Até revogação | LGPD art. 7 I | Exclusão imediata |

### 5. Com quem compartilhamos

- **Fornecedores obrigatórios:** Hospedagem (Hostinger), WhatsApp gateway (Evolution), Chatwoot (CRM), MiniMax (LLM) — todos com DPA assinado
- **Órgãos públicos:** Receita Federal (NF), CNJ (Provimento 74), tribunais (quando intimados)
- **NUNCA** com terceiros para marketing sem consentimento

### 6. Seus direitos (LGPD art. 18)

Você tem 7 direitos que pode exercer AGORA:

1. **Acesso** (art. 18, II) — ver seus dados
2. **Correção** (art. 18, III) — atualizar dados incorretos
3. **Anonimização** (art. 18, IV) — dados não essenciais
4. **Portabilidade** (art. 18, V) — export JSON estruturado
5. **Eliminação** (art. 18, VI) — esquecimento completo
6. **Informação sobre compartilhamento** (art. 18, VII) — quem recebeu seus dados
7. **Revogação de consentimento** (art. 18, IX) — parar tratamento opcional

**Como exercer:** https://cartorio.2notasudi.com.br/lgpd/dashboard OU dpo@2notasudi.com.br  
**Tempo de resposta:** até 15 dias (LGPD art. 18 §5º)

### 7. Segurança

- **Criptografia:** TLS 1.3 em trânsito, AES-256 em repouso
- **Acesso:** VPN Tailscale para admins, JWT + DPO role para LGPD dashboard
- **Audit chain:** SHA-256 + HMAC imutável (verificada cada 15min)
- **Penetration testing:** anual + on-demand após mudança significativa
- **Backups:** 4×/dia local + 1×/mês off-site criptografado (5 anos)

### 8. Cookies

- **Essenciais:** sessão (não pode recusar)
- **Analytics:** opt-in (LGPD opt-in para não-essenciais)
- **Marketing:** opt-in separado (banner D19)
- **Configurar:** footer do site → "Cookies"

### 9. Alterações nesta Política

- Notificação por email (se consentiu) + banner no site
- Versões anteriores: `docs/lgpd/policy/D23-changelog.md`
- Vigência: 30 dias após notificação

### 10. Contato DPO

```
📧 dpo@2notasudi.com.br
📞 (34) 9999-9999
🕐 Resposta: até 15 dias úteis
📍 Av. XXX, XXX, Uberlândia/MG
```

Para reclamações ANPD: https://www.gov.br/anpd

---

## 📍 Onde Publicar

- **URL canônica:** https://cartorio.2notasudi.com.br/privacy
- **Menu footer:** link "Privacidade"
- **App admin:** link "Política LGPD" no footer admin
- **Bot WhatsApp:** menu `LGPD > Ver política`
- **Bot Telegram:** comando `/privacidade`

---

## 🔄 Revisão

- **Anual:** revisada por jurídico externo
- **Emergencial:** após mudança ANPD/CNJ
- **Versionamento:** major (2.x) para mudanças substantivas, minor (2.x.y) para correções
