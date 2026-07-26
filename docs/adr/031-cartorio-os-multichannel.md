# ADR 031 — Cartório OS: Arquitetura Multicanal Autônoma com OpenClaw, Hermes, Spectrum TS e FastMCP

**Data:** 2026-07-25  
**Status:** Aprovado  
**Autores:** Cartório AI Team, Chief Architect, Security & LGPD Reins  

---

## 1. Contexto & Problema

O **2º Serviço Notarial de Uberlândia (2º Notas UDI)** exige uma infraestrutura de atendimento autônomo de inteligência artificial que opere através de múltiplos canais de mensageria públicos e privados: **iMessage**, **WhatsApp Business**, **Telegram** e **Web Chat**.

Os principais desafios incluem:
1. **Multicanalidade sem Duplicação de Lógica:** Manter um único cérebro de regras notariais e PII sanitization para todos os canais.
2. **Mensageria Pública (Public Inbound):** Inbound público só pode ser anunciado em canal e linha dedicada cujo provider o suporte. Linha compartilhada/teste permanece limitada à allowlist do provider.
3. **Outbound Protegido (Anti-Spam / LGPD):** Mensagens proativas exigem opt-in, contexto operacional ou autorização prévia.
4. **HITL Obrigatório (Human-in-the-Loop):** Nenhuma decisão jurídica final ou emissão notarial pode ocorrer de forma 100% autônoma. Todo pré-protocolo gerado por IA DEVE ter status `DRAFT`.
5. **Cadeia de Auditoria SHA256+HMAC:** Todos os eventos e execuções de ferramentas FastMCP devem ser auditados imutavelmente.

---

## 2. Decisão de Arquitetura

Adotar a arquitetura unificada **Cartório OS**, composta pelos seguintes módulos desacoplados:

1. **Spectrum TS Gateway Layer (`services/spectrum-gateway`):**
   - Runtime em TypeScript/Node/Bun utilizando a SDK `spectrum-ts`.
   - Suporte a múltiplos provedores (`imessage`, `whatsapp`, `telegram`).
   - Contratos canônicos, dedupe de 24h e guardrails de PII. Antes de ativá-lo, deve haver migração controlada do consumidor Photon ativo; dois consumidores para o mesmo projeto são proibidos.

2. **Policy Engine:**
   - Governa consentimento, política de outbound e supressão na authority layer.
   - `ALLOW_ALL_INBOUND` não faz bypass de limitação do provider. Outbound proativo continua bloqueado sem base legal ou humana.

3. **Hermes Agent Execution Engine:**
   - Motor autônomo baseado em MiniMax-M3 (45s hard timeout) com fallback para OpenCode Zen.
   - Integração nativa com PII Scrubber em 3 camadas e FastMCP.

4. **FastMCP Authority Layer:**
   - Consumo de 14 ferramentas autônomas expostas pela API FastAPI do Cartório em `/mcp`.

---

## 3. Consequências & Compliance

- **LGPD:** Sanitização em tempo real de CPF (`123.***.***-00`), RG, telefone e e-mail antes e depois da chamada LLM.
- **HITL:** Protocolos nascem estritamente no status `DRAFT`.
- **DDoS / Anti-Abuse:** Rate limiting por `space_id` e `client_ip`.
