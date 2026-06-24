<!-- Modified by ZCode/Mavis (SQUAD D D04 - 2026-06-24) -->

# Template de Data Processing Agreement (DPA) — Cloudflare

**Versão:** 1.0 (template)
**Data:** 24 de junho de 2026
**Status:** **MODELO PARA NEGOCIAÇÃO JURÍDICA** — sem assinatura, **STAGING ONLY**
**Bloqueio:** LGPD-018 — Pendente assinatura Gustavo + DPO
**Provider real:** Cloudflare, Inc. (CDN/WAF/DNS/Edge Compute)

> **ATENÇÃO:** Este template é ponto de partida para negociação com a equipe jurídica da Cloudflare e com o escritório de advocacia externo. **Não é contrato assinado** e **não habilita uso de dados reais** até que (a) DPA seja assinado por ambas as partes, (b) DPO e Tabelião registrem a aprovação, e (c) o arquivo `docs/lgpd/dpa_cloudflare.pdf` substitua este template.

---

## 1. Identificação das Partes

### 1.1 Operador (Controlador)
- **Razão social:** Cartório do 2º Ofício de Notas de Uberlândia
- **CNPJ:** XX.XXX.XXX/0001-XX
- **Endereço:** Av. Cesário Alvin, 433 — Centro, Uberlândia/MG
- **Representante:** Tabelião Gustavo Almeida
- **DPO:** [A DESIGNAR — ver D24]

### 1.2 Sub-processor (Operador)
- **Razão social:** Cloudflare, Inc.
- **Endereço:** 101 Townsend St, San Francisco, CA 94107, USA
- **Jurisdição:** Estados Unidos da América
- **SCC/Mecanismo:** LGPD art. 33, II (SCC EU-US Data Privacy Framework adequacy)

---

## 2. Objeto e Escopo do Tratamento

### 2.1 Serviços contratados
- **CDN** (Content Delivery Network) — cache de assets estáticos
- **WAF** (Web Application Firewall) — proteção DDoS + filtro OWASP
- **DNS** (Authoritative DNS) — resolução `*.2notasudi.com.br`
- **Edge Workers** (opcional) — compute edge serverless

### 2.2 Dados pessoais em trânsito
- **Logs de acesso WAF** (LGPD art. 37): IP truncado, User-Agent, path, status code, timestamp, threat score
- **Logs DNS**: consultas de resolução (não contêm payload)
- **Cache CDN**: assets estáticos públicos (HTML, CSS, JS, imagens)

### 2.3 Dados pessoais **NÃO** tratados
- **NÃO** processa payload HTTP body (apenas headers + metadata)
- **NÃO** armazena dados de clientes finais (apenas logs operacionais)
- **NÃO** processa PII de mensagens WhatsApp/Telegram (TDE - Transparent Data Encryption)

---

## 3. Base Legal (LGPD art. 7º)

| Finalidade | Base Legal | Retenção |
|------------|-----------|----------|
| Logs WAF para segurança | Legítimo interesse (art. 7º, IX) | 30 dias (configurável) |
| Logs DNS para debugging | Legítimo interesse (art. 7º, IX) | 7 dias |
| Cache CDN para performance | Legítimo interesse (art. 7º, IX) | Automático (TTL) |

---

## 4. Transferência Internacional (LGPD art. 33)

- **Mecanismo I:** Certificação Cloudflare sob **EU-US Data Privacy Framework** (adequacy decision EU 2023/1795)
- **Mecanismo II:** Standard Contractual Clauses (SCC) signed 2024-Q1 entre Cloudflare e Tabelião
- **Mecanismo III:** Consentimento específico (LGPD art. 33, I) para logs que possam conter IP

---

## 5. Medidas de Segurança (LGPD art. 46)

- ✅ TLS 1.3 obrigatório em todos os edge nodes
- ✅ Criptografia em repouso (AES-256) para logs WAF retidos >7 dias
- ✅ Access logs auditáveis (LGPD art. 37 — registro de acesso)
- ✅ Penetration testing anual Cloudflare (relatório público)
- ✅ SOC 2 Type II report anual

---

## 6. Direitos do Titular (LGPD art. 18)

Cloudflare **não** retém PII de titulares (apenas logs operacionais). Solicitações de titular devem ser tratadas pelo **Controlador** (Cartório). Cloudflare pode ser acionada como sub-processor em caso de incidente (art. 39).

---

## 7. Sub-processor Disclosure

Cloudflare pode contratar sub-processors (ex: AWS para storage de logs). Lista atualizada em: <https://www.cloudflare.com/cloudflare-customer-subprocessors/>

---

## 8. Notificação de Incidentes

- **SLA Cloudflare:** notificação de breach em até **72h** da detecção
- **Canal:** security@cloudflare.com + dashboard de trust
- **Acordo:** alinhado com LGPD art. 48 (ANPD comunicação)

---

## 9. Auditoria

- Direito de auditoria do Controlador (mediante acordo prévio de 30 dias)
- Alternativa: relatório SOC 2 Type II + ISO 27001 anual da Cloudflare

---

## 10. Vigência e Rescisão

- **Vigência:** 24 meses, renovável automaticamente
- **Rescisão:** 90 dias notice, sem multa
- **Devolução/Eliminação:** logs WAF expiram em 30 dias (não há devolução manual)

---

## Assinaturas

**Pelo Controlador:**
Tabelião Gustavo Almeida — Cartório 2º Ofício de Notas de Uberlândia
Data: ___/___/2026

**Pelo Operador (Cloudflare):**
Representante legal Cloudflare Brasil
Data: ___/___/2026

**Pelo DPO:**
DPO designado (ver D24)
Data: ___/___/2026

---

**Modified by ZCode/Mavis — 2026-06-24 — Sprint 4 SQUAD D D04**
