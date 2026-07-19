# Catálogo de Free Models e Free Providers

> Atualizado em 2026-07-19 | Projeto Cartório 2º Notas Uberlândia
> Integração completa de 3 contas OpenCode Zen + fallback chain multi-provider

## OpenCode Zen Free Models (3 Contas)

| Slot | Model | Contexto | Secret no `.env` |
|------|-------|----------|-------------------|
| 1 | deepseek-v4-flash-free | 1M tokens | `OPENCODE_ZEN_ACCOUNT_1_API_KEY` |
| 2 | mimo-v2.5-free | 1M tokens | `OPENCODE_ZEN_ACCOUNT_2_API_KEY` |
| 3 | nemotron-3-ultra-free | 1M tokens | `OPENCODE_ZEN_ACCOUNT_3_API_KEY` |

## Chain de Fallback Completa

```
opencode_zen_account_1 (deepseek-v4-flash-free, 1M ctx)
  → opencode_zen_account_2 (mimo-v2.5-free, 1M ctx)
    → opencode_zen_account_3 (nemotron-3-ultra-free, 1M ctx)
      → opencode_free_1 (nemotron-3-ultra-free, 1M ctx)
        → opencode_free_2 (mimo-v2.5-free, 1M ctx)
          → opencode_free_3 (deepseek-v4-flash-free, 1M ctx)
            → opencode_go (MiniMax-M3 XMax Thinking)
              → openrouter (multi-model aggregator)
                → groq (mixtral-8x7b, llama-3.3-70b)
                  → mistral (devstral-small, 256K ctx)
                    → google_ai_studio (gemini-3.5-flash, 1M ctx)
                        → openclaw (gpt-5.5 / claude-sonnet)
                          → jules (Gemini async)
                            → antigravity (Gemini OAuth)
```

## Provedores Gratuitos Mapeados

| Provider | Modelos Free | Conexão | Status |
|----------|-------------|---------|--------|
| **OpenCode Zen** | deepseek-v4-flash-free, mimo-v2.5-free, nemotron-3-ultra-free | OpenAI-compat | ✅ Ativo |
| **OpenCode Go** | MiniMax-M3 XMax Thinking | OpenAI-compat | ✅ Ativo |
| **OpenRouter** | deepseek-r1, qwen-2.5, llama-3.3, phi-4 | OpenAI-compat | ✅ Ativo |
| **Groq** | mixtral-8x7b, llama-3.3-70b, gemma-3-12b | OpenAI-compat | ✅ Ativo |
| **Google AI Studio** | gemini-3.5-flash, gemini-3.1-pro | OpenAI-compat | ✅ Ativo |
| **Mistral** | devstral-small (256K ctx) | OpenAI-compat | ✅ Ativo |
| **OpenClaw** | gpt-5.5, claude-sonnet | OpenAI-compat | ✅ Ativo |
| **Circuit Breaker** | Redis-based (5min cooldown) | Interno | ✅ Ativo |

## Configuração

Todas as chaves estão no `.env` local (gitignorado):

```env
# Provider default
LLM_DEFAULT_PROVIDER=opencode_zen_account_1

# Chain completa
LLM_FALLBACK_CHAIN=opencode_zen_account_1,opencode_zen_account_2,opencode_zen_account_3,opencode_free_3,opencode_free_1,opencode_free_2,opencode_go,openrouter,groq,mistral,google_ai_studio,openclaw,jules,antigravity

# Conta 1
OPENCODE_ZEN_ACCOUNT_1_API_KEY=<secret-manager-value>
OPENCODE_ZEN_ACCOUNT_1_MODEL=deepseek-v4-flash-free
OPENCODE_ZEN_ACCOUNT_1_BASE_URL=https://opencode.ai/zen/v1

# Conta 2
OPENCODE_ZEN_ACCOUNT_2_API_KEY=<secret-manager-value>
OPENCODE_ZEN_ACCOUNT_2_MODEL=mimo-v2.5-free
OPENCODE_ZEN_ACCOUNT_2_BASE_URL=https://opencode.ai/zen/v1

# Conta 3
OPENCODE_ZEN_ACCOUNT_3_API_KEY=<secret-manager-value>
OPENCODE_ZEN_ACCOUNT_3_MODEL=nemotron-3-ultra-free
OPENCODE_ZEN_ACCOUNT_3_BASE_URL=https://opencode.ai/zen/v1
```

## Segurança

- **Nunca commitar chaves**: `.env` está no `.gitignore`
- **Nunca rotacionar sem autorização**: Chaves são gerenciadas manualmente
- **PII scrubbing em 3 camadas**: input / pre-LLM / output (via `pii.py`)
- **Circuit breaker Redis**: Cada provider tem circuito independente
- **Audit log**: Toda chamada LLM é auditada com provider, modelo, latência
