<!-- Modified by ZCode/Mavis (SQUAD D D05 - 2026-06-24) -->

# Template de Data Processing Agreement (DPA) — Hostinger (VPS Hosting)

**Versão:** 1.0 (template)
**Data:** 24 de junho de 2026
**Status:** **MODELO PARA NEGOCIAÇÃO JURÍDICA** — sem assinatura, **STAGING ONLY**
**Bloqueio:** LGPD-019 — Pendente assinatura Gustavo + DPO
**Provider real:** Hostinger International Ltd. (VPS KVM2 Ubuntu 24.04)

> **ATENÇÃO:** Este template é ponto de partida para negociação com a equipe jurídica da Hostinger. **Não é contrato assinado** e **não habilita uso de dados reais em produção** até que (a) DPA seja assinado, (b) DPO e Tabelião registrem a aprovação, e (c) o arquivo `docs/lgpd/dpa_hostinger.pdf` substitua este template.

---

## 1. Identificação das Partes

### 1.1 Operador (Controlador)
- **Razão social:** Cartório do 2º Ofício de Notas de Uberlândia
- **CNPJ:** XX.XXX.XXX/0001-XX
- **Endereço:** Av. Cesário Alvin, 433 — Centro, Uberlândia/MG
- **Representante:** Tabelião Gustavo Almeida
- **DPO:** [A DESIGNAR — ver D24]

### 1.2 Sub-processor (Operador)
- **Razão social:** Hostinger International Ltd.
- **Endereço:** 61 Lordou Vironos Street, 6023 Larnaca, Cyprus
- **Jurisdição:** União Europeia (Chipre) + datacenters mundiais
- **Sede servidor:** Brasil (datacenter dedicado São Paulo, quando disponível)
- **IP do servidor:** 187.77.236.77 (Hostinger VPS)
- **Tailscale IP:** 100.99.172.84 (overlay privado)

---

## 2. Objeto e Escopo do Tratamento

### 2.1 Serviço contratado
- **VPS KVM2** — 2 vCPU, 8GB RAM, 100GB SSD, Ubuntu 24.04 LTS
- **Localização do servidor:** datacenter São Paulo (BR) — Datacenter Tier III
- **Sistema operacional:** Ubuntu 24.04 LTS
- **Gerenciamento:** Easypanel (self-hosted, instalado no VPS)

### 2.2 Dados pessoais em trânsito/repouso no VPS
- **API Cartório**: dados de clientes, protocolos, audit log completo (LGPD art. 37)
- **N8N**: workflows, execuções, credentials, environment variables
- **Evolution API**: mensagens WhatsApp criptografadas em repouso
- **Chatwoot**: conversas, contatos, agentes
- **Supabase (14 containers)**: clientes, protocolos, audit chain, PII
- **OpenClaw Gateway**: contexto de conversa, LLM traces
- **Redis**: cache, idempotency keys, sessions, rate limit counters

### 2.3 Medidas de storage
- **Criptografia at-rest**: LUKS no VPS + pgcrypto em colunas sensíveis
- **Criptografia in-transit**: TLS 1.3 (Traefik reverse proxy) — obrigatório
- **Backups**: 4x/dia para S3 + WAL streaming + retenção 30d (ver A14)

---

## 3. Base Legal (LGPD art. 7º)

| Finalidade | Base Legal | Retenção |
|------------|-----------|----------|
| Execução de contrato (serviços cartorários) | art. 7º, V | 5 anos (protocolos) / até revogação (clientes) |
| Cumprimento de obrigação legal | art. 7º, II | 5 anos (CTN, Lei 6.015/73) |
| Logs de auditoria (LGPD art. 37) | Obrigação legal | 5 anos |

---

## 4. Transferência Internacional (LGPD art. 33)

- **Datacenter:** Brasil (não há transferência para jurisdição estrangeira no storage)
- **Painel administrativo Hostinger:** Cyprus/EU (adequacy decision EU-BR pendente, usar SCC EU-BR Module 4)
- **Sub-processor disclosure**: Hostinger pode usar AWS/Azure para backup off-site

---

## 5. Medidas de Segurança (LGPD art. 46)

- ✅ Firewall UFW + Traefik reverse proxy com TLS 1.3
- ✅ SSH key-based only (Tailscale overlay network 100.x.x.x)
- ✅ Fail2ban + rate limiting (Cloudflare WAF em perímetro)
- ✅ Auto-updates Ubuntu 24.04 LTS habilitado
- ✅ Backup criptografado A14 (4x/dia S3 + WAL + restore test mensal)
- ✅ Audit log imutável com hash chain + HMAC (LGPD art. 37)
- ✅ Dead man's switch auditoria (audit_log > 1h sem escrita = alerta)

---

## 6. Direitos do Titular (LGPD art. 18)

Servidor VPS **armazena** PII de titulares. Solicitações de titular (D6-D12) devem ser tratadas **diretamente no banco** (Postgres/Supabase). Hostinger apenas provê a infraestrutura; **não** processa lógica de negócio.

---

## 7. Sub-processor Disclosure

- **Cloudflare** (CDN/WAF/DNS) — DPA D04
- **AWS S3** (backup off-site) — DPA genérico
- **Storj/Backblaze** (opcional, backup S3-compatible)

Lista atualizada em: <https://www.hostinger.com/legal/sub-processors>

---

## 8. Notificação de Incidentes

- **SLA Hostinger (datacenter breach):** notificação em até **48h** da detecção
- **SLA infra (VPS intrusion):** monitorado 24/7 via Easypanel + Grafana
- **Canal:** abuse@hostinger.com + painel de cliente
- **Acordo:** alinhado com LGPD art. 48 (ANPD comunicação em 72h)

---

## 9. Auditoria

- Direito de auditoria do Controlador (acesso SSH via Tailscale)
- Alternativa: SOC 2 Type II + ISO 27001 datacenter
- Testes de penetração anuais (D18)

---

## 10. Vigência e Rescisão

- **Vigência:** 12 meses (anual), renovável
- **Rescisão:** 30 dias notice
- **Devolução/Eliminação:** em rescisão, VPS é destruído e disco criptografado sobrescrito 3x (DoD 5220.22-M)

---

## 11. SLA de Uptime

- **Hostinger VPS:** 99.9% uptime (datacenter Tier III)
- **Compromisso operacional interno:** 99.5% (ver A23)
- **Plano de contingência:** backup cross-region (S3 São Paulo + S3 Frankfurt) para disaster recovery

---

## Assinaturas

**Pelo Controlador:**
Tabelião Gustavo Almeida — Cartório 2º Ofício de Notas de Uberlândia
Data: ___/___/2026

**Pelo Operador (Hostinger):**
Representante legal Hostinger International Ltd.
Data: ___/___/2026

**Pelo DPO:**
DPO designado (ver D24)
Data: ___/___/2026

---

**Modified by ZCode/Mavis — 2026-06-24 — Sprint 4 SQUAD D D05**
