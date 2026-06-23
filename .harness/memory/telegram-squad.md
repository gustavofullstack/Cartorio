# Telegram Squad — Contexto Operacional

> Status vivo do squad de bots Telegram da Pietra (Mavis).
> Atualizado quando muda o setup. Cada entrada: data + situacao + acao tomada.

---

## 2026-06-23 18:42 BRT — @udiapods_bot SEM token operacional (pre-existente)

**Sintoma:** Gustavo respondendo no DM @udiapods_bot nao eh capturado pelo Mavis ha SEMANAS.

**Causa raiz:** `~/.mavis/credentials/mavis/telegram.json` so contem botToken de **@pietra_ceo_bot** (8921906164:AAEgpyeDx9svIv_wIB5IG5MYJWmyYbmHZVc). @udiapods_bot nunca foi exportado na env (TELEGRAM_BOT_TOKEN=INVALID).

**Confirmado em:** `~/.mavis/memory/archive/2026-06-23/telegram-squad.md` — "Bot token @udiapods_bot nao exportado na env (TELEGRAM_BOT_TOKEN=INVALID)".

**Recovery 17:43 BRT NAO foi causa:** trocou apenas o token quebrado de @pietra_ceo_bot por outro funcional. Nao tocou em @udiapods_bot.

**Impacto atual:** GRUPO Pietra Squad (chat_id=-5006771024) eh a UNICA via captura. DM @udiapods_bot eh silencio total.

**Workaround em uso:** cross-post DM 6682284055 via @pietra_ceo_bot (best effort — so funciona se Gustavo fez /start nesse bot).

**Acao humana necessaria (fora do escopo do Mavis):** Gustavo precisa recuperar o token do @udiapods_bot via BotFather e exportar pra env (TELEGRAM_BOT_TOKEN). Sem isso, DM do bot @udiapods_bot fica mudo.

**Refs:**
- memory archive: ~/.mavis/memory/archive/2026-06-23/telegram-squad.md
- creds file: ~/.mavis/credentials/mavis/telegram.json
- recovery context: comunicacao mvs_9b3c9043 18:41 BRT
- GRUPO reinforcement enviada: reply_to_message_id=4 em -5006771024 (Pietra Squad)

---

## Bots Ativos

| Bot | Token | Chat DM Gustavo | Status |
|-----|-------|-----------------|--------|
| @pietra_ceo_bot | 8921906164:AAEgpyeDx9svIv_wIB5IG5MYJWmyYbmHZVc | 6682284055 | FUNCIONAL (cross-post best effort) |
| @udiapods_bot | INVALID | 6682284055 (esperado) | OFFLINE — Gustavo precisa recuperar via BotFather |
| @pietra_udia_pods | (squad bot) | (squad bot) | OK |
| @udiapods_bot | INVALID | n/a | OFFLINE |

---

## GRUPO Pietra Squad

- chat_id: -5006771024
- bots membros: @pietra_ceo_bot, @pietra_udia_pods (e variantes)
- captura inbound: rota `mavis im route` (ver `mavis im route list`)
- outbound: via bot @pietra_ceo_bot (curl + sendMessage)
- regra operacional 22/06 Gustavo: comunicacao proativa obrigatoria Mavis ↔ Antigravity, GRUPO eh canal unico de coordenacao cross-session
