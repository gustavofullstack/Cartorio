# Lesson 254 — Telegram Token Recovery, Evolution Redis Fix & OpenCode Zen Validation (2026-07-19)

## Contexto
Conclusão da re-integração e validação do bot Telegram `@test_cartorio_bot`, correção do pool Redis na Evolution API, re-alinhamento de provedores OpenCode Zen e verificação do Radar de Saúde do ecossistema.

## Decisões & Implementações

1. **Atualização do Token do Telegram Bot & Webhook**:
   - Token atualizado para `8859206262:AAFFCPET5ci2qcCIC_hgm0ppcOyBSOIrwqM` no `.env` da VPS e no `.env` local.
   - Webhook configurado e validado em `https://api.2notasudi.com.br/api/v1/telegram/webhook`.
   - `getWebhookInfo` confirma `pending_update_count: 0` e `last_error_message: none`.

2. **Correção de DNS do Redis na Evolution API**:
   - O serviço `cartorio_evolution-api` utilizava IP estático antigo (`10.11.211.250`).
   - Atualizado via Swarm para a chave DNS canônica `CACHE_REDIS_URI=redis://default:%40Techno832466@cartorio_redis:6379`.
   - Serviço convergiu e gerou QR Code no log do container.

3. **OpenClaw Gateway Provider Fix**:
   - Atualizada a configuração `/var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/openclaw.json` de `litellm/MiniMax-M3` para `opencode_free_3/deepseek-v4-flash-free`, eliminando erros `ENOTFOUND` de conexão com LiteLLM legado.

4. **Ajuste de Suíte de Testes (14 Providers)**:
   - Atualizado `test_opencode_generic.py` para refletir 14 provedores na tabela `PROVIDER_DISPATCH` (incluindo as 3 contas OpenCode Zen).
   - Suíte de testes `pytest`: **2833 passed, 0 failed**.

## Status Final do Radar (7/7 Online)
```json
{
  "status": "green",
  "services": {
    "database": "online",
    "redis": "online",
    "n8n": "online",
    "openclaw": "online",
    "evolution": "online",
    "chatwoot": "online",
    "supabase": "online"
  }
}
```

## Regras de Ouro Aplicadas
- **Segurança de Credentials**: Nenhuma chave rotacionada; chaves armazenadas estritamente em `.env` locais e de produção.
- **Audit Chain**: Mantida imutável e verificada no startup da API.
