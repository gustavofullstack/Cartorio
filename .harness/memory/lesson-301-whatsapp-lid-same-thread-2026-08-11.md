# Lesson 301 — WhatsApp LID: resposta no thread errado (2026-08-11)

## Sintoma
Sessao OPEN, webhook 200, LLM ok, sendText 200, mas o Gustavo nao via resposta no chat onde digitou.

## Causa
WhatsApp LID cria dois JIDs para o mesmo contato:
- inbound: `162023748985056@lid` (thread visivel no app)
- alt: `553492800250@s.whatsapp.net`

O remap `remoteJidAlt` fazia o bot responder no chat do telefone. O cliente continua olhando o chat `@lid` e acha o bot mudo.

Segundo bug: Evolution envia `event=MESSAGES_UPSERT`. `parse_evolution_payload` exigia exatamente `messages.upsert` (ponto) e devolvia `ignored`. Deploy com `docker build` cacheado deixou o container antigo no ar.

## Fix
- Responder no mesmo `remoteJid` (`@lid` incluso). `sendText` aceita `1620...@lid`.
- `is_messages_upsert_event()` aceita ponto, underscore e casing.
- Ignorar `status@broadcast` e `*@broadcast`.
- Rebuild producao com `--no-cache` quando o COPY do `backend/app` nao invalidar.

## Evidencia
- Replies manuais no LID: DELIVERY_ACK.
- Live `LID_LIVE_*` + `MESSAGES_UPSERT`: `bot.llm_ok` + `bot.send ok` no thread `@lid` ("Autenticacao de copia sai por R$ 11,21 por folha.").
- Backup: `/var/backups/cartorio/whatsapp/SUPER_BACKUP_WHATSAPP_CARTORIO_AGENT_20260811_110455.tar.gz`
