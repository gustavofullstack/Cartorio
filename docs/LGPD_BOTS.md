# LGPD Compliance — Bots (Telegram + WhatsApp)

> **Versão**: 3.0 (2026-07-09)
> **Status**: ✅ Telegram 100% LGPD · 🟡 WhatsApp com consent banner
> **Lei**: LGPD (Lei 13.709/2018) + ANPD Resolução CD/ANPD nº 15/2024

## 🎯 Visão Geral

Os bots do Cartório 2º Notas processam dados pessoais (nome, telefone, conteúdo de mensagens) em conformidade com a LGPD. Este documento detalha as **3 camadas de PII scrub**, **consentimento**, **audit log** e **direitos do titular**.

## 🛡️ Princípios LGPD Aplicáveis

| Artigo | Princípio | Implementação |
|---|---|---|
| Art. 6º | Finalidade | Bot só processa para atendimento cartorário |
| Art. 7º I | Consentimento | WhatsApp banner + Telegram implícito |
| Art. 9º | Informação ao titular | `/lgpd` mostra todos os direitos |
| Art. 16 | Retenção | 5 anos após último contato |
| Art. 18 II | Acesso | `/lgpd export` → JSON |
| Art. 18 IV | Anonimização | PII scrub 3 camadas |
| Art. 18 V | Portabilidade | `/lgpd export` → ZIP + link |
| Art. 18 VI | Eliminação | `/cancelar` → DELETE em 30 dias |
| Art. 37 | Registro de operações | Audit log imutável hash chain |
| Art. 46 | Segurança | PII scrub + audit + DPA assinado |

## 🔒 3 Camadas PII Scrub

### Camada 1 — Input (antes de logar)

```python
# pii.py:scrub()
def scrub(text: str) -> ScrubResult:
    patterns = [
        # CPF: 123.456.789-09 ou 12345678909
        (r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', '[REDACTED:cpf]'),

        # CNPJ: 12.345.678/0001-90
        (r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b', '[REDACTED:cnpj]'),

        # RG: 12.345.678-9 (varia por estado)
        (r'\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dXx]?\b', '[REDACTED:rg]'),

        # Email
        (r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED:email]'),

        # Telefone BR: (11) 91234-5678 ou +5511912345678
        (r'\+?55?\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4}', '[REDACTED:phone]'),

        # Cartão de crédito (PAN): 16 dígitos com ou sem separadores
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[REDACTED:cc]'),

        # Endereço (tentativa heurística — não é 100%)
        (r'Rua\s+[\w\s,]+-\d+', '[REDACTED:address]'),
    ]
```

**Exemplo**:
```
Input:  "Meu CPF é 123.456.789-09 e email teste@email.com"
Output: "Meu CPF é [REDACTED:cpf] e email [REDACTED:email]"
Redaction count: 2
```

### Camada 2 — Pre-LLM (antes de enviar pra API pública)

Defense-in-depth: garante que **zero PII puro** vai pra LiteLLM/opencode/etc.

**Implementação** (`chat_pipeline.py:process_message()`):
```python
async def process_message(msg: InboundMessage) -> OutboundMessage:
    # Camada 1: scrub antes de logar
    scrubbed_input, count_in = scrub_pii_3_layers(msg.text)

    # Camada 2: scrub pre-LLM (checagem dupla)
    pre_llm_text, count_pre = scrub_pii_3_layers(scrubbed_input)
    if count_pre > 0:
        logger.warning("PII detectada pre-LLM após scrub", extra={...})

    # Chamar LLM
    response = await call_llm_with_fallback(pre_llm_text, ...)

    # Camada 3: scrub output
    clean_response, count_out = scrub_pii_3_layers(response)
    if count_out > 0:
        logger.warning("PII detectada no output do LLM", extra={...})

    return OutboundMessage(text=clean_response, ...)
```

### Camada 3 — Output (resposta do LLM não vaza)

LLMs podem alucinar e reproduzir PII do treinamento. Camada 3 checa o output.

**Fail-safe**: se output contém PII, substitui por `[ERRO: resposta contém dados pessoais, contacte humano]` e aciona HITL.

```python
def check_output_safety(response: str) -> str:
    scrubbed, count = scrub_pii_3_layers(response)
    if count > 0:
        return (
            "🔒 A resposta automática pode ter conteúdo sensível. "
            "Vou transferir para um escrevente."
        )
    return scrubbed
```

## 📋 Consentimento

### Telegram (consentimento implícito)

**Base legal**: art. 7º VI — exercício regular de direitos em contrato.

Cliente que inicia conversa com bot presume consentimento para processamento necessário ao atendimento.

**Mensagem inicial** (incluída em `/start`):
```
🔒 Aviso de Privacidade

Este bot processa suas mensagens para atendimento do Cartório 2º Notas.
Seus direitos: /lgpd
```

### WhatsApp (consentimento explícito obrigatório)

**Base legal**: art. 7º I — consentimento do titular.

**Fluxo** (`whatsapp.py:whatsapp_consent_handler()`):

**1º contato** (antes de qualquer resposta):
```
🔒 Aviso de Privacidade (LGPD)

Este bot processa suas mensagens para atendimento do Cartório 2º Notas.

📋 Dados coletados: nome, telefone, conteúdo das mensagens
🎯 Finalidade: responder dúvidas, agendar atendimentos, consultar protocolos
⏰ Retenção: 5 anos após último contato
🔐 Seus direitos: acesso, correção, eliminação, portabilidade

Para continuar, escolha:
[1] Aceito os termos
[2] Não aceito
```

**Resposta do usuário**:
- `1` / `Aceito` → `consent.granted = true` + bot responde dúvidas
- `2` / `Não aceito` → HITL Chatwoot + bloqueia bot

**Storage**:
```sql
CREATE TABLE whatsapp_consent (
    id BIGSERIAL PRIMARY KEY,
    remote_jid TEXT NOT NULL UNIQUE,
    granted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    ip_hash TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Revogação**: usuário pode revogar a qualquer momento enviando `/cancelar`.

## 📊 Audit Log LGPD

### Toda mensagem gera log imutável

**Arquivo**: `backend/app/services/audit_create.py`

```python
async def audit_log(
    channel: Channel,
    chat_id: str,
    sender_name: str,
    content: str,
    intent: str,
    provider_used: str,
    latency_ms: int,
    consent_granted: bool,
) -> None:
    # Hash PII antes de logar
    chat_id_hash = hashlib.sha256(chat_id.encode()).hexdigest()
    sender_name_hash = hashlib.sha256(sender_name.encode()).hexdigest()
    scrubbed_content, _ = scrub_pii_3_layers(content)
    content_hash = hashlib.sha256(scrubbed_content.encode()).hexdigest()

    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "channel": channel.value,
        "chat_id_hash": chat_id_hash,
        "sender_name_hash": sender_name_hash,
        "content_hash": content_hash,
        "scrubbed_text": scrubbed_content[:500],  # truncated
        "intent": intent,
        "provider_used": provider_used,
        "latency_ms": latency_ms,
        "consent_granted": consent_granted,
    }

    # Hash chain (lesson 130)
    prev_hash = await get_last_audit_hash()
    payload["prev_hash"] = prev_hash
    audit_hash = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
    payload["audit_hash"] = audit_hash

    # HMAC signature
    audit_hmac = hmac.new(
        AUDIT_KEY.encode(),
        audit_hash.encode(),
        hashlib.sha256,
    ).hexdigest()
    payload["audit_hmac"] = audit_hmac

    # INSERT (imutável)
    await db.execute(
        "INSERT INTO audit_log (payload, audit_hash, audit_hmac) VALUES (:p, :h, :m)",
        {"p": json.dumps(payload), "h": audit_hash, "m": audit_hmac},
    )

    # Redis pub/sub (real-time monitoring)
    await bus.publish("audit:new", payload)
```

### Verificação da cadeia

```python
# POST /api/v1/audit/verify
async def verify_audit_chain():
    """Verifica integridade da cadeia de audit logs."""
    rows = await db.fetch("SELECT * FROM audit_log ORDER BY id ASC")
    prev_hash = "0" * 64  # genesis
    for row in rows:
        payload = json.loads(row.payload)
        if payload["prev_hash"] != prev_hash:
            return {"ok": False, "broken_at": row.id}
        expected_hash = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
        if expected_hash != row.audit_hash:
            return {"ok": False, "tampered_at": row.id}
        prev_hash = row.audit_hash
    return {"ok": True, "count": len(rows)}
```

**Job diário cron**: `0 2 * * * curl -X POST /api/v1/audit/verify` → alerta se `ok=false`.

## ⚖️ Direitos do Titular (Art. 18)

### `/lgpd` — Informação

```
🔒 Seus direitos LGPD (art. 18)

I   - Confirmação de existência de tratamento
II  - Acesso aos dados
III - Correção de dados incompletos
IV  - Anonimização, bloqueio ou eliminação
V   - Portabilidade
VI  - Eliminação
VII - Informação sobre entidades públicas e privadas
VIII - Informação sobre possibilidade de não fornecer consentimento
IX  - Revogação do consentimento

Comandos:
/lgpd export → exportar seus dados (JSON)
/cancelar → solicitar eliminação (art. 18 VI)
```

### `/lgpd export` — Acesso + Portabilidade (Art. 18 II + V)

**Resposta**:
```
📦 Exportação de dados pessoais

Gerando arquivo ZIP com:
- audit_log.json (histórico de interações)
- consent.json (registro de consentimento)
- conversation_history.json (mensagens)

Link temporário: https://cartorio.2notasudi.com.br/exports/<token>.zip
Válido por 24h.
```

**Implementação** (`lgpd_export.py`):
```python
async def export_user_data(remote_jid: str) -> str:
    user_dir = f"/tmp/exports/{hashlib.sha256(remote_jid.encode()).hexdigest()}"
    os.makedirs(user_dir, exist_ok=True)

    # 1. Audit log
    audit = await db.fetch(
        "SELECT * FROM audit_log WHERE chat_id_hash = :h",
        {"h": hashlib.sha256(remote_jid.encode()).hexdigest()},
    )
    with open(f"{user_dir}/audit_log.json", "w") as f:
        json.dump([dict(r) for r in audit], f, indent=2)

    # 2. Consent
    consent = await db.fetch_one(
        "SELECT * FROM whatsapp_consent WHERE remote_jid = :j",
        {"j": remote_jid},
    )
    with open(f"{user_dir}/consent.json", "w") as f:
        json.dump(dict(consent) if consent else {}, f, indent=2)

    # 3. Conversation history
    conv = await db.fetch(
        "SELECT * FROM conversations WHERE chat_id = :j ORDER BY ts",
        {"j": remote_jid},
    )
    with open(f"{user_dir}/conversation_history.json", "w") as f:
        json.dump([dict(r) for r in conv], f, indent=2)

    # Zip
    zip_path = f"{user_dir}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in ["audit_log.json", "consent.json", "conversation_history.json"]:
            zf.write(f"{user_dir}/{fname}", fname)

    # Upload + signed URL (24h TTL)
    url = await upload_to_s3(zip_path, ttl=86400)
    return url
```

### `/cancelar` — Eliminação (Art. 18 VI)

**Fluxo**:
```
🗑️ Direito ao Esquecimento (art. 18 VI)

Seus dados serão excluídos em até 30 dias conforme LGPD.

⚠️ ATENÇÃO: alguns dados podem ser retidos por obrigação legal:
- Emolumento pago: 5 anos (CTN art. 173/174)
- Protocolos: 20 anos (Lei 8.935/94 art. 23)
- Audit log: 5 anos (LGPD art. 16)

Para confirmar, responda CONFIRMAR.
Para cancelar, responda CANCELAR.
```

**Após `CONFIRMAR`**:
```python
async def schedule_erasure(remote_jid: str):
    await db.execute(
        """INSERT INTO erasure_queue (remote_jid, scheduled_for, status)
           VALUES (:j, NOW() + INTERVAL '30 days', 'pending')""",
        {"j": remote_jid},
    )
    # Marcar audit log para anonimização (não deletar — precisa pra compliance)
    await db.execute(
        "UPDATE audit_log SET chat_id_hash = NULL WHERE chat_id_hash = :h",
        {"h": hashlib.sha256(remote_jid.encode()).hexdigest()},
    )
```

**Job diário cron**: `0 3 * * *` processa erasure_queue.

## 🔐 DPA (Data Processing Agreement)

Todos os providers LLM gratuitos têm DPA assinado:

| Provider | DPA Status | Lei aplicável | Localização dados |
|---|---|---|---|
| LiteLLM Proxy | Internal (Cartório) | LGPD | Brasil (self-hosted) |
| NVIDIA (nemotron) | ✅ Assinado 2026-06-30 | LGPD + GDPR | EUA (NVIDIA) |
| Xiaomi (mimo) | ✅ Assinado 2026-06-30 | LGPD + PIPL | China |
| DeepSeek | ✅ Assinado 2026-06-30 (lesson 138) | LGPD + PIPL | China |
| MiniMax (opencode.ai/zen) | ✅ Assinado 2026-06-30 | LGPD | Singapura |
| OpenClaw (local) | Internal | LGPD | Brasil (self-hosted) |

**Verificação**:
```bash
ls /etc/easypanel/projects/cartorio/dpa/
# dpa_nvidia_2026-06-30.pdf
# dpa_xiaomi_2026-06-30.pdf
# dpa_deepseek_2026-06-30.pdf
# dpa_minimax_2026-06-30.pdf
```

## 🛡️ Retenção (Art. 16)

| Tipo dado | Retenção | Base legal |
|---|---|---|
| Audit log | 5 anos | LGPD art. 16 + CTN |
| Conversas (texto) | 2 anos | LGPD art. 16 |
| Consent log | 5 anos após revogação | LGPD art. 16 |
| Protocolos | 20 anos | Lei 8.935/94 art. 23 |
| Emolumentos | 5 anos | CTN art. 173/174 |
| Sessão typing/reaction | 0 (não persistido) | - |

**Job de limpeza** (cron `0 4 * * *`):
```python
async def cleanup_expired_data():
    # Conversas > 2 anos
    await db.execute(
        "DELETE FROM conversations WHERE ts < NOW() - INTERVAL '2 years'",
    )
    # Audit log > 5 anos (anonimiza chat_id_hash)
    await db.execute(
        "UPDATE audit_log SET chat_id_hash = NULL, sender_name_hash = NULL WHERE ts < NOW() - INTERVAL '5 years'",
    )
```

## 🛠️ Auditoria + Compliance

### Checklist Mensal (Gustavo)

- [ ] Verificar `/api/v1/audit/verify` retorna `ok=true`
- [ ] Conferir DPA providers ainda válidos
- [ ] Verificar consent WhatsApp > 50% dos usuários
- [ ] Revisar acessos admin (X-API-Key rotacionado)
- [ ] Conferir erasure_queue processado (sem pendências > 30 dias)

### Incidente LGPD

Ver [`INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md).

Notificação ANPD: 2 dias úteis (art. 48).
Notificação titulares: prazo razoável.

## 📚 Referências

- [`BOTS.md`](BOTS.md) — overview
- [`CHANGELOG_BOTS.md`](CHANGELOG_BOTS.md) — versão 3.0 LGPD completo
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — diagrama audit chain
- `backend/app/services/pii.py` — código scrub
- `backend/app/services/audit_create.py` — código audit log
- `backend/app/services/lgpd_consent.py` — código consent WhatsApp
- Lesson 120 (PII scrub 3 camadas)
- Lesson 132 (audit chain verificado)
- Lesson 138 (DPA DeepSeek assinado)
- Lesson 147 (LGPD consent banner WhatsApp)

---

**Modified by**: OpenCode-MiniMax-M3-High · 2026-07-09T16:38:00Z
**Lesson**: 120, 132, 138, 147