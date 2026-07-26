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

1. **Transport iMessage (runtime canônico LIVE):** Hermes profile `cartorio`
   (`~/.hermes/profiles/cartorio`) + Photon sidecar — LaunchAgent
   `ai.hermes.gateway-cartorio`, sidecar `127.0.0.1:8793`, projeto Spectrum
   `CARTORIO BOT TEST` (`438527e1-…`). Dois consumidores no mesmo projeto são proibidos.

2. **Scaffold / contratos TS (`services/spectrum-gateway`):** SDK `spectrum-ts`,
   contratos canônicos, `ChannelCapabilities.inbound_scope`
   (`allowlist|public|unknown`), dedupe 24h, PII scrub, ConsentRegistry.
   Referência typechecked — **não** é o processo LIVE do Cartório OS.
   `apps/spectrum-gateway` não existe (fantasma de relatório).

3. **Policy Engine:**
   - Governa consentimento, política de outbound e supressão na authority layer.
   - Shared/test line = LIMITED_INBOUND (`inbound_scope=allowlist`).
   - `ALLOW_ALL_INBOUND` / `PHOTON_ALLOW_ALL_USERS` **não** fazem bypass da
     allowlist do provider. PUBLIC_INBOUND só com linha dedicada Business.
   - Outbound proativo bloqueado sem base legal ou humana.

4. **Hermes Agent Execution Engine (profile cartorio):**
   - Model `kimi-k3` (Kimi Coding Plan), MCP client, session isolation, redaction.
   - Integração com PII scrubbing 3-camadas (API) e HITL DRAFT.

5. **FastMCP Authority Layer:**
   - 14 tools na API FastAPI do Cartório em `/mcp`. Hermes/OpenClaw nunca
     bypassam a API para mutações notariais.

---

## 3. Consequências & Compliance

- **LGPD:** Sanitização em tempo real de CPF (`123.***.***-00`), RG, telefone e e-mail antes e depois da chamada LLM.
- **HITL:** Protocolos nascem estritamente no status `DRAFT`.
- **DDoS / Anti-Abuse:** Rate limiting por `space_id` e `client_ip`.
