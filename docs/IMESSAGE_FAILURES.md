# IMESSAGE FAILURES — 2026-07-28

Toda falha encontrada na campanha, com root cause e status.

## F1 — Endpoint pietra sem system prompt (P0 persona) — RESOLVIDA
- Sintoma: "Eu sou o **MiniMax-M3**, modelo desenvolvido pela MiniMax" (reproduzido 03:51 UTC via endpoint público).
- Root cause: endpoint repassava mensagens sem system prompt; identidade dependia 100% do cliente.
- Fix: `PIETRA_SYSTEM_PROMPT` sempre prependido (commit 76bffdf3). Teste: `TestSystemPromptInjection`.

## F2 — Identity guard só cobria "Hermes" (P0) — RESOLVIDA
- Fix: patterns estendidos (MiniMax/Claude/GPT/Kimi/DeepSeek/Gemini/Grok/OpenAI/Anthropic etc.) + sanitize provider→Pietra + endpoint usa hard-stop (commit 76bffdf3).

## F3 — Think tags vazavam no canal API (P1) — RESOLVIDA
- `<think>...</think>` e fechamento órfão `</think>` (vazou em chunk SSE em prod).
- Fix: `_strip_think_tags` no endpoint + remoção de órfãs (commit 8f32264f).

## F4 — Sem PII scrub pre-LLM no endpoint (P0 LGPD) — RESOLVIDA
- Fix: `pii.scrub` em todas as mensagens role=user (commit 76bffdf3). Teste: `TestPiiScrubPreLlm`.

## F5 — Tabela de emolumentos placeholder ERRADA (P0 financeiro) — RESOLVIDA
- autenticação 28,90 (oficial 11,21), reconhecimento firma 32,10 (11,21), procuração 156,40 (68,94) — servido a clientes reais com selo TABELA_2026_MG.
- Fix: `EMOLUMENTOS_2026` corrigido + MCP tool delega para `emolumento_real_djalma` (HITL em compostos) + aliases de slugs (commits 8507b6f4, 8f32264f). Regression: `test_emolumento_oficial_2026.py`.

## F6 — Circuit breakers stale 5h (P1 disponibilidade) — RESOLVIDA (operacional)
- Blip transitório ~23:20 UTC abriu cb:open por 5h → endpoint servindo string fixa.
- Fix: keys deletadas 03:55 UTC. **Residual**: cooldown 5h sem half-open é agressivo (abrir ticket: reduzir `open_time_seconds` ou half-open probe).

## F7 — Tool loop infinito (P0 funcional) — RESOLVIDA
- Root cause: `ChatMessage(role, content)` dropava `tool_calls`/`tool_call_id`/`name` → MiniMax re-chamava a tool para sempre, sem sintetizar.
- Fix: campos preservados no schema + forwarding (commit 32f2306c). Regression: `TestToolResultPassthrough`.

## F8 — Modelo respondia R$ sem tool call (P0 funcional) — RESOLVIDA
- "emolumento de testamento" respondido com api_calls=1 (R$ 95,86 inventado em probe).
- Fix: system prompt com REGRA DE OURO de tool obrigatória (commit c7b4799e) + F7.

## F9 — OPENCODE_GO_BASE_URL=http://localhost:9999/v1 (P2) — ABERTA
- Nada escuta nesse endereço no container → LLM MONITOR reporta OFFLINE (mensagem de erro trocada: minimax reporta erro do opencode_go).
- Ação: corrigir env no Easypanel (apontar para endpoint real ou remover provider). Não impacta a chain principal (opencode_go não está na chain do endpoint).

## F10 — cartorio_api 0/0 (serviço zumbi) — ABERTA (limpeza)
- `No such image: easypanel/cartorio/api:latest`. Serviço morto no Swarm.
- Ação: `docker service rm cartorio_api` após confirmar com Easypanel (serviço legado duplicado do system-api).

## F11 — Saudação com horário errado (P3 qualidade) — ABERTA
- "Boa tarde" às 23:30 BRT. Modelo não recebe relógio BRT. Ticket (sessão paralela).

## F12 — PHOTON_ALLOW_ALL_USERS=true (P2 decisão humana) — ABERTA
- Linha pública aceita qualquer remetente (Gap G4 relatório paralelo). Necessária decisão do Gustavo: manter aberta (canal público do cartório) ou allowlist.

## F13 — Endpoint /api/v1/pietra/chat/completions sem auth (P2 exposição) — ABERTA
- Qualquer cliente pode usar como proxy LLM gratuito (rate limit global 60/min mitiga). HEAD já adiciona rate limiting dedicado. Decidir: exigir API key (quebra clientes atuais) ou manter público com rate limit.

## F14 — Endpoint agora exige rebuild manual para deploy (P3 processo) — ABERTA
- Easypanel não auto-builda no push; API trpc retorna 401 para mutations com a key atual. Deploys desta campanha: rsync + docker build na VPS + service update (mesma tag). Documentar ou corrigir webhook GitHub→Easypanel.
