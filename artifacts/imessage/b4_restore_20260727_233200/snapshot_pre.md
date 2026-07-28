# B4 Restore — Snapshot Pré-Restart

**Quando:** 2026-07-28 02:35Z (23:35 BRT 27/07)
**Operador:** Pietra (ZCode sessão local, Mac Gustavo)

## Estado real divergente do que o doc IMESSAGE_IDENTITY_LEAK sugeria

| Item | Doc assumia | Real encontrado |
|---|---|---|
| Gateway PID | 74263 (state.json) | 74263 **MORTO**; wrapper LaunchAgent PID 78540 vivo; Node sidecar PID 78558 na 8793 |
| Porta 8793 | não-listening | **LISTENING Node 78558** |
| sessions/ count | variável | **251 arquivos** |
| .skills_prompt_snapshot.json | existe | **NÃO existe** (purgado antes) |
| gateway_state.json photon | disconnected | **connected** (updated_at 02:34:41Z = 23:34 BRT, há 1 min) |
| hermes CLI | (não verificado) | `~/.local/bin/hermes`, gateway status reporta PID 72747 detached fallback + outro perfil cartorio LaunchAgent PID 78540 |
| LaunchAgent | — | `ai.hermes.gateway-cartorio` PID 78540 loaded |
| Conflito de processos | não mencionado | **DOIS gateways competindo pelo mesmo perfil cartorio**: 72747 detached (PID do addendum 23:00) E 78540 LaunchAgent |

## Histórico iMessage Cartório Bot (chat_id 364, identifier +16282649335)

| BRT (UTC-3) | ID | Quem | Conteúdo |
|---|---|---|---|
| 23:47 27/07 | 3283 | Gustavo | "Oi Pietra! Testando fallback..." |
| 23:47-23:48 | 3284-3291 | Bot | 8 mensagens de ERRO (rate-limit + empty stream + provider failed) |
| 23:49 | 3292 | Gustavo | "Oi Pietra! Mais um teste..." |
| 23:49-23:50 | 3293-3294 | Bot | "Switched to fallback deepseek-v4-flash-free" → "Oi, Pietra! Teste confirmado..." ✅ |
| 23:50 | 3295 | Gustavo | "Excelente Pietra! Confirmado o switch..." |
| 23:50 | 3296-3297 | Bot | "Switched..." → "Confirmado, Pietra! A troca..." ✅ |
| **00:14 28/07** | **3299** | **Gustavo** | **"VAMOS REINICIAR DO ZERO E PRECISO QUE LEMBRE DE TODAS AS MENSAGENS DO INICIO AO FIM DESSE CHAT!!"** |
| 00:31-00:33 | 3300-3301 | Gustavo | "oi" / "Oi" |
| 00:31-01:42 | 3302-3308 | Gustavo | "oi/test/1/2/3/4/5/oi" (bateria de testes) |

**🚨 NENHUMA resposta do bot depois do "reset" (00:14 28/07).** Confirma 100% o sintoma reportado:
imensager não está respondendo.

## Causa direta observada

- Última resposta do bot (id 3297) às 23:50 BRT 27/07
- Photon `disconnected` desde 21:04 BRT 27/07 (vide doc IMESSAGE_IDENTITY_LEAK §D1)
- 11 mensagens enviadas pelo Gustavo entre 00:14-01:42 → todas caíram no vazio
- Photon RECONECTOU às 02:34:41Z (= 23:34 BRT 27/07) — há ~1 minuto, mas o histórico acima NÃO mostra novas respostas do bot, sugerindo que **as mensagens da fila podem estar perdidas** ou **não foram reprocessadas após reconnect**

## Decisão operacional

**B4 NÃO foi executado porque o estado mudou entre o doc (22:42) e o snapshot real (23:35).**
Photon acabou de reconnectar sozinho. Restart agora = arriscar mais derrubada + perder a janela de reprocessamento natural.

Próximos passos discutidos com o usuário separadamente.
