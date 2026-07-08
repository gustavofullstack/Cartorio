---
name: MiniMax-M3
description: |
  Skill para usar o provider MiniMax-M3 XMax Thinking (MiniMax Coding Plan) via LiteLLM proxy.
  Modelo de IA com reasoning avancado (XMax Thinking automatico). Acessivel via:
  - LiteLLM VPS interno: http://coding-vps_apenas_para_auxilio_litellm-app:4000 (master key)
  - Direct MiniMax API: https://api.minimaxi.com/v1 (sk-cp-* key)
  Use quando precisar: gerar codigo, analisar codebase, planejar tasks complexas, raciocinio passo-a-passo.
  Provider: MiniMax.io Coding Plan | Model: MiniMax-M3 XMax Thinking | Versao: 2026-07-08
---

# MiniMax-M3 XMax Thinking — Skill de IA Provider

## Acesso (DUAL)

| Item | Valor |
|------|-------|
| **Provider** | MiniMax.io Coding Plan |
| **Model** | `MiniMax-M3` |
| **Thinking** | XMax Thinking (automatico) |
| **API Key direta** | `sk-cp-kRIbiqKy9F-0aN0rrWUAHSAvNc_e0e00Gr1U4QlYWi_CIgguvXKr7gNLBo6DaEVU7JpY0GnJFinOFMOhBMNFD6Sp8pMuN9UEXyNR4mMi4V4hqm9eUr_7j5s` |
| **Base URL direta** | `https://api.minimaxi.com/v1` |
| **LiteLLM proxy (VPS)** | `http://coding-vps_apenas_para_auxilio_litellm-app:4000` |
| **LiteLLM master key** | `e39dss0k1baohuqkprjv` |
| **Custo** | MiniMax Coding Plan (plano Gustavo) |

## Uso via LiteLLM Proxy (RECOMENDADO - bypass CORS/firewall)

```bash
# Health check
curl -sk http://coding-vps_apenas_para_auxilio_litellm-app:4000/health/liveliness
# "I'm alive!"

# List models
curl -sk -H "Authorization: Bearer e39dss0k1baohuqkprjv" \
  http://coding-vps_apenas_para_auxilio_litellm-app:4000/v1/models
# {"data":[{"id":"MiniMax-M3","object":"model","owned_by":"openai"}],"object":"list"}

# Chat completion (XMax Thinking automatico)
curl -sk -H "Authorization: Bearer e39dss0k1baohuqkprjv" \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-M3","messages":[{"role":"user","content":"Diga OK"}]}' \
  http://coding-vps_apenas_para_auxilio_litellm-app:4000/v1/chat/completions
```

## Uso via MiniMax API direta

```bash
# ATENCAO: sk-cp-* key direto retorna 401 via curl externo (lesson 2026-07-08).
# SEMPRE usar via LiteLLM proxy. Se precisar da key direta:
curl -sk -H "Authorization: Bearer sk-cp-kRIbiqKy9F-0aN0rrWUAHSAvNc_e0e00Gr1U4QlYWi_CIgguvXKr7gNLBo6DaEVU7JpY0GnJFinOFMOhBMNFD6Sp8pMuN9UEXyNR4mMi4V4hqm9eUr_7j5s" \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-M3","messages":[{"role":"user","content":"OK"}]}' \
  https://api.minimaxi.com/v1/chat/completions
```

## Codigo Python (OpenAI-compatible)

```python
import urllib.request
import json

payload = json.dumps({
    "model": "MiniMax-M3",
    "messages": [{"role": "user", "content": "Seu prompt aqui"}],
    "max_tokens": 500,
}).encode()

req = urllib.request.Request(
    "http://coding-vps_apenas_para_auxilio_litellm-app:4000/v1/chat/completions",
    data=payload,
    headers={
        "Authorization": "Bearer e39dss0k1baohuqkprjv",
        "Content-Type": "application/json",
    },
)

with urllib.request.urlopen(req, timeout=30) as r:
    body = json.loads(r.read().decode())
    reply = body["choices"][0]["message"]["content"]
    usage = body.get("usage", {})
    print(f"REPLY: {reply}")
    print(f"USAGE: {usage}")
    # XMax Thinking:
    # - reasoning_tokens: tokens de raciocinio interno
    # - completion_tokens: tokens da resposta final
```

## Caracteristicas XMax Thinking

| Aspecto | Detalhe |
|---------|---------|
| **Reasoning** | Automatico (chain-of-thought interno) |
| **Reasoning tokens** | 10-100 tokens (visivel em `usage.completion_tokens_details.reasoning_tokens`) |
| **Latencia media** | 1.5-2.5s para respostas curtas, 5-15s para tarefas complexas |
| **Context window** | 1M tokens (effective) |
| **Code quality** | Senior-level (Python, JS, TS, Go, Rust, SQL) |
| **LGPD compliance** | NAO enviar PII (CPF/RG/telefone/email) - usar PII sanitizer antes |
| **Idiomas** | PT-BR (excelente), EN, ES |

## Regras de Uso

1. **SEMPRE via LiteLLM proxy** (key direta nao funciona externamente - Lesson 2026-07-08)
2. **PII SCRUB ANTES** - usar `app/services/pii.py` antes de enviar qualquer texto com dados pessoais
3. **Max tokens** - default 500 para conciso, 2000+ para code generation
4. **Streaming** - SSE suportado via `stream=True`
5. **Tool calling** - suportado (OpenAI function calling format)
6. **Vision** - suportado (imagens em base64 ou URL)

## MCP Server

Localizado em `backend/mcp_server.py` (cartorio-mcp-cabuloso) - expone tools que usam MiniMax M3 internamente.

Adicionar tool MiniMax no MCP server (proxima task):
```python
@mcp.tool()
async def ask_minimax(prompt: str, max_tokens: int = 500) -> str:
    """Ask MiniMax-M3 XMax Thinking a question. Returns response text."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "http://coding-vps_apenas_para_auxilio_litellm-app:4000/v1/chat/completions",
            headers={"Authorization": "Bearer e39dss0k1baohuqkprjv"},
            json={"model": "MiniMax-M3", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=30.0,
        )
        return r.json()["choices"][0]["message"]["content"]
```

## Configuracao LiteLLM (ja aplicada)

```yaml
# /etc/easypanel/projects/coding-vps_apenas_para_auxilio/litellm-app/
# Configuracao no DB (LiteLLM_ModelTable) - ja existe:
- model_name: MiniMax-M3
  litellm_params:
    model: openai/MiniMax-M3
    api_base: https://api.minimaxi.com/v1
    api_key: sk-cp-kRIbiqKy9F-...
```

## Validacao (testado 2026-07-08)

```bash
# Resultado real:
HTTP=200 TIME=1.91s
REPLY: OK
USAGE: {
  'completion_tokens': 26,
  'prompt_tokens': 182,
  'total_tokens': 208,
  'completion_tokens_details': {'reasoning_tokens': 22},
  'prompt_tokens_details': {'cached_tokens': 128}
}
```

## Lições Aprendidas

- **2026-07-08**: Sk-cp-* key direto em api.minimaxi.com retorna 401 - usar SEMPRE via LiteLLM proxy
- **2026-07-08**: XMax Thinking = automatico, NAO precisa ativar parametro thinking=true
- **2026-07-08**: `reasoning_tokens` aparece em `usage.completion_tokens_details.reasoning_tokens`
- **2026-07-08**: LiteLLM internamente tem o modelo registrado como "openai/MiniMax-M3" (compat layer)