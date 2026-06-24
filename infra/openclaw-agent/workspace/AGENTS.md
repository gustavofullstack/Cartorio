# AGENTS.md - Regras do Agent AI Cartorio (OpenClaw)

> **Configuracao operacional do OpenClaw gateway.**
> Modelo LLM: `deepseek-v4-flash` (OpenCode-Go)
> Contexto: **1M tokens** (NAO 131k - isso era cache de sessoes antigas, contexto real do modelo e' 1M)
> Thinkings: **ADAPTATIVO** (ver secao Thinkings abaixo)

## Contexto 1M - LICAO IMPORTANTE

OpenClaw reporta "131.1k tokens usados" mas o **modelo real (deepseek-v4-flash) suporta 1M de contexto**. O que aconteceu:

- OpenClaw UI mostra **tokens consumidos na sessao atual** (ate agora)
- NAO mostra o **contexto maximo** do modelo
- Janela real disponivel: 1.000.000 tokens
- A "limitacao 131k" era de um modelo ANTIGO (deepseek-v2) que NAO usamos mais

**Acao**: configurar OpenClaw para usar TODO o contexto de 1M, nao truncar em 131k.

```bash
# Verificar config atual
openclaw config get max_context_tokens
# Esperado: 1000000 (1M)

# Se estiver errado:
openclaw config set max_context_tokens 1000000
openclaw config set max_output_tokens 8192
```

## Thinkings ADAPTATIVO

Por padrao, thinkings (raciocinio explicito antes de responder) esta **DESLIGADO** para economizar tokens. Mas para tarefas complexas (codigo, debug, LGPD), o Gustavo pediu para **LIGAR adaptativamente**.

**Regra de decisao**:

| Tarefa | Thinkings |
|---|---|
| Saudacao simples / FAQ | OFF |
| Consultar protocolo / emolumento | OFF |
| Analise de codigo / debug | **ON** (max thinking) |
| Calculo emolumento + validacao LGPD | **ON** (max thinking) |
| Resposta juridica com cita | **ON** (max thinking) |
| Handoff para humano (decisao critica) | **ON** (max thinking) |

**Implementacao no OpenClaw**:

```yaml
# infra/openclaw-agent/openclaw.json
{
  "agent": {
    "thinking": {
      "enabled": "adaptive",  # NAO boolean fixo
      "max_thinking_tokens": 8000,
      "triggers": {
        "keywords": ["calcular", "validar", "analisar", "debug", "LGPD", "PII", "erro", "exception"],
        "complexity_threshold": 0.7  # score de complexidade do prompt
      }
    },
    "max_context_tokens": 1000000,
    "max_output_tokens": 8192
  }
}
```

**Em codigo Python** (call Opencode-Go):

```python
from app.integrations.opencode_go import chat

response = await chat(
    messages=[{"role": "user", "content": pergunta}],
    thinking="auto",  # OpenCode-Go decide
    model="deepseek-v4-flash",
    max_thinking_tokens=8000,  # quando ativado
    max_tokens=2000,
)
```

## Modelo: deepseek-v4-flash (OpenCode-Go)

- **Provider**: OpenCode-Go (`https://opencode.ai/zen/go/v1`)
- **Modelo**: `deepseek-v4-flash` (low cost, fast)
- **Custo**: ~10x menor que Claude Opus 4.5 / GPT-5.5
- **Latencia**: ~500ms-1s para respostas tipicas
- **Contexto**: 1M tokens
- **DPA**: assinado (LGPD art. 33 - transferencia internacional OK)

**Por que deepseek-v4-flash**:
- Custo beneficio imbatível para cartorio
- Suporta 1M contexto (vs 131k de modelos antigos)
- PT-Brasil: compreende bem formalidades juridicas
- DPA assinado: legalmente seguro

## Fallback: OpenClaw gateway

Se OpenCode-Go falhar, fallback para **OpenClaw gateway** (secundario):
- Configurado em `backend/app/config.py::openclaw_*`
- Modelos alternativos: Claude, OpenAI, local LLM
- Triggered automaticamente em timeout/5xx

## Skills do OpenClaw

Lista de skills (auto-load em wake):
- `pesquisa-satisfacao` - NPS pos-atendimento
- `protocolo-tracker` - status de protocolo via cliente
- `agendamento` - slots livres
- `emolumento-calc` - calculo de custas
- `pessoa-fisica-validacao` - valida CPF/CNS/CNH
- `lgpd-explicacao` - explica termos LGPD
- `handoff-humano` - transfere para escrevente

## Hooks

- `pre-response`: PII scrub (defense in depth)
- `post-response`: audit log (LGPD art. 37)
- `on-handoff`: notifica escrevente via Chatwoot
- `on-error`: log + retry + escalation

## Comandos do agent (slash commands no chat)

- `/emolumento` - calculo rapido
- `/protocolo [numero]` - consultar status
- `/agendar` - ver slots
- `/humano` - handoff imediato para escrevente
- `/cancelar` - cancela conversa atual

## Boas praticas

1. **PII scrubbing em 3 camadas** (input, pre-LLM, output) - nao confie no caller
2. **HITL obrigatorio** em qualquer acao juridica (isencao, urgencia, validacao)
3. **Audit log** em TODA chamada ao LLM (LGPD art. 37)
4. **Consent gate** - bloqueia se `consent_granted=False` (LGPD art. 7 I)
5. **Rate limit** - 30/min padrao, 60/min DPO, 600/min N8N

## Limitacoes conhecidas

- NAO modificar `.env` (sensitive) - so ler
- NAO conectar WhatsApp Business API diretamente (sempre via N8N + Evolution)
- NAO acessar DB prod sem ir via API autenticada
- NAO rotacionar chaves (Gustavo + ZCode sao unicos com acesso)

## Referencias

- OpenClaw: https://github.com/openclaw-ai/openclaw (docs internas)
- DeepSeek V4: https://api-docs.deepseek.com/
- OpenCode-Go: https://opencode.ai/docs/
- LGPD art. 7 I (consentimento): https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- SOUL/IDENTITY/TOOLS/USER: arquivos companheiros em `workspace/`
