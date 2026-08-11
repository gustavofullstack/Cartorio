# Lesson 300 — WhatsApp mudo: root cause e liberacao autonoma (2026-08-11)

## Sintoma
Instancia `cartorio-agent` (`c18e80c2-4045-40ff-bd73-3924ef23c249`, JID `553491952444`) estava `OPEN`, webhook 200, mas o bot nao respondia clientes.

## Root causes (empilhados)
1. **Webhook canônico nao enviava**: `EVOLUTION_WEBHOOK_URL` apontava para `/api/v1/webhook/evolution`, que gera resposta JSON mas **nao chama** Evolution `sendText`. Path correto com `chat_pipeline` + envio: `/api/v1/whatsapp/webhook`.
2. **Host Evolution errado no system-api**: `EVOLUTION_BASE_URL=http://cartorio_evolution-api:8080` (servico `0/0`). Host real: `http://cartorio_whatsapp-api:8080`.
3. **API key errada no system-api**: chave local desatualizada → 401 interno → `whatsapp/health` degradado (`evolution_api=offline`).
4. **LLM chain quebrada**: `OPENCODE_GO_BASE_URL=http://localhost:9999/v1` + fallback `opencode_go,openclaw,cache`. MiniMax monitor falhava. Fix: `OPENCODE_GO_BASE_URL=https://api.minimax.io/v1` + chain `minimax,opencode_go,cache`.
5. **WhatsApp LID addressing**: inbound vem como `NNN@lid` com telefone em `remoteJidAlt`. Sem normalizar, `sendText` retorna 400 `exists:false`.

## Fixes aplicados (prod)
- Super backup: `/var/backups/cartorio/whatsapp/SUPER_BACKUP_WHATSAPP_CARTORIO_AGENT_20260811_014322.tar.gz` (sha256 `a4b4aa5829c39accda894e886fe219c953b3f76cb94e498d0723a237526306f1`).
- Webhook Evolution → `https://api.2notasudi.com.br/api/v1/whatsapp/webhook`.
- `cartorio_system-api` env: Evolution host/key, MiniMax via OPENCODE_GO, webhook URL.
- `parse_evolution_payload`: usa `remoteJidAlt` quando `@lid`; ignora `status@broadcast` e `fromMe`.
- Sem reacao emoji no WhatsApp (pedido Felipe / estilo Lark).

## Evidencia
- `GET /api/v1/whatsapp/health` → `status=ok`, `whatsapp_session=open`.
- Radar: `evolution=online`.
- Live test `LIVE_AUTONOMOUS_*`: `bot.llm_ok` + `bot.send ok` + mensagem entregue a `553492800250`.
- Hermes Lark: `cartorio_hermes 1/1`, model `MiniMax-M3`, feishu enabled.

## Regra permanente
Antes de culpar LLM/sessao: (1) confirmar qual path o webhook aponta; (2) confirmar host Docker do Evolution (`whatsapp-api` vs `evolution-api`); (3) confirmar apikey interna com `connectionState`; (4) normalizar LID→telefone.
