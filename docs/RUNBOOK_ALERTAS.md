# RUNBOOK DE ALERTAS — Cartório AI (G9.S2.T10 / E3.07)

> Resposta operacional para os 9 alertas de `prometheus/alerts.yml`.
> LGPD: este runbook nunca instrui inspecionar PII — labels são enums canônicos.

## LLMCircuitOpen
**Sinal:** gauge `cartorio_llm_circuit_open{provider} == 1` por 2min.
**Significado:** provider LLM com 3+ falhas consecutivas; fallback ativo (TTL 300s).
**Ação:** 1) Verificar saúde do provider (MiniMax/litellm/zen) no painel; 2) checar `cartorio_llm_calls_total{status="error"}` por model; 3) se upstream 5xx/429, aguardar TTL do circuito; 4) se persistir > 15min, escalar para dono do provider. **Não** reiniciar API em cascata.

## LLMAllProvidersDegraded
**Sinal:** `rate(cartorio_llm_degraded_total[5m]) * 300 > 10`.
**Significado:** usuários recebendo degraded reply em volume — cadeia de fallback degradada.
**Ação:** 1) Confirmar LLMCircuitOpen correlato; 2) validar chaves/saldos dos providers; 3) se todos down, comunicar indisponibilidade parcial no canal interno; respostas degradadas são esperadas e scrubadas.

## DLQGrowing
**Sinal:** `dlq_depth > 5` por 5min.
**Significado:** mensagens mortas acumulando (integrador fora: Evolution/n8n/Chatwoot).
**Ação:** 1) `SELECT queue, count(*) FROM outbox_message WHERE status='dead' GROUP BY 1`; 2) checar saúde do integrador da fila top; 3) após recuperação, worker reprocessa no backoff (1m/5m/15m) — não reenfileirar manualmente sem runbook DLQ.

## WebhookAuthFailures
**Sinal:** `rate(cartorio_webhook_auth_failures_total[1m]) * 60 > 10` (canal em `{{ $labels.channel }}`).
**Significado:** pico de 401 — scan/brute-force de secret OU integrador desconfigurado.
**Ação:** 1) Confirmar se deploy recente mudou secret no integrador; 2) se origem externa desconhecida, avaliar bloqueio na borda (Traefik/fail2ban); 3) rotação de secret SOMENTE com ordem do dono.

## WhatsAppSessionDisconnected
**Sinal:** `cartorio_whatsapp_evolution_service_up == 1 and cartorio_whatsapp_session_connected == 0` por 2min.
**Significado:** Evolution API UP mas sessão WhatsApp fechada (QR expirado/logout).
**Ação:** acionar o dono para QR Connect no Manager (B2). Nunca declarar sessão aberta por `service_up` apenas.

## DeadMansSwitch
**Sinal:** `time() - cartorio_audit_dead_mans_switch_heartbeat > 900` por 2min (severity=page).
**Significado:** scheduler de verificação do audit log parou > 15min (inclui cold-start).
**Ação:** 1) Verificar processo/uvicorn vivo; 2) checar logs do job `dead_mans_switch`; 3) rodar verificação manual `POST /api/v1/audit/verify`; 4) se heartbeat não voltar após restart controlado, tratar como incidente de integridade (cartorio-lgpd).

## TelegramWebhookAuthSpike
**Sinal:** `rate(telegram_webhook_total{result="401"}[5m]) * 60 > 5`.
**Significado:** brute-force do `X-Telegram-Bot-Api-Secret-Token`.
**Ação:** 1) Confirmar em `getWebhookInfo` que secret bate com o configurado; 2) se ataque, bloquear origem na borda; 3) rotação do webhook secret só com ordem do dono + re-sync (runbook webhook).

## TelegramResponseSentZero
**Sinal:** webhooks 200 chegando, `increase(telegram_response_sent_total[10m]) == 0`.
**Significado:** envio para a API do Telegram quebrado (token inválido, rede, pool HTTP).
**Ação:** 1) `getMe` com o token do serviço; 2) checar egress/rede do container; 3) inspecionar erros em `cartorio_telegram_erros_total`; 4) se token revogado, escalar ao dono (rotação = ação humana).

## TelegramLLMFallbackExhausted
**Sinal:** zero `cartorio_llm_calls_total{status="success"}` em 10min com 5+ falhas.
**Significado:** cadeia inteira de providers falhando; só degraded reply servida.
**Ação:** 1) Mesmo protocolo de LLMAllProvidersDegraded; 2) prioridade alta se coincidir com TelegramResponseSentZero (usuário sem resposta útil).

_Modified by Gustavo Almeida — E3.07/G9.S2.T10, 2026-07-25._
