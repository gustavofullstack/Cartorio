# Hooks - OpenClaw Agent (CartórioBot)

Hooks sao eventos passiveis de observacao que disparam callbacks em
plugins registrados. Diferente de skills (que o agente USA ativamente),
hooks rodam em background sempre que o evento correspondente ocorre.

## Convecao de nomenclatura

- Hook ID: `<categoria>:<evento>` (kebab-case)
- Categoria: `session`, `message`, `skill`, `handoff`, `lgpd`, `audit`
- Callback: funcao async em plugin registrado

## Hooks implementados

| Hook ID | Quando dispara | Bloqueavel | Payload |
|---------|----------------|------------|---------|
| `session:start` | Nova sessao iniciada | Nao | `{session_id, sender, canal}` |
| `session:end` | Sessao encerrada (timeout/disconnect) | Nao | `{session_id, duracao_segundos, mensagens_count}` |
| `message:received` | Mensagem recebida do cliente (pre-skill) | Sim | `{message, scrubbed, pii_findings}` |
| `message:sent` | Resposta enviada pelo bot (post-LLM) | Nao | `{response, llm_tokens_in, llm_tokens_out}` |
| `skill:invoked` | Skill ativada | Nao | `{skill_name, args, resultado}` |
| `handoff:triggered` | Handoff humano acionado | Nao | `{reason, cliente_id, agente_id}` |
| `pii:detected` | PII scrub detectou dado sensivel | Sim | `{findings, redacted_count}` |
| `lgpd:blocked` | LGPD gate bloqueou acao | Sim | `{motivo, base_legal, cliente_id_hash}` |
| `audit:logged` | Entrada gravada no audit log | Nao | `{audit_id, action, actor_id}` |

## Hook execution order

Para cada hook bloqueavel, plugins sao executados em ordem de prioridade
(menor numero = maior prioridade). Se qualquer plugin retornar `block=True`,
o evento eh interrompido e handoff humano eh acionado.

```
message:received (bloqueavel)
  1. pii-scrubber-plugin (priority=10, always first)
  2. consent-gate-plugin (priority=20, LGPD gate)
  3. rate-limit-plugin (priority=30, anti-spam)
  4. analytics-plugin (priority=100, observability)
```

## Como registrar um hook em plugin

```yaml
# plugin.yaml
hooks:
  - id: message:received
    priority: 50
    blocking: true
    timeout_ms: 5000
```

```python
# main.py
async def on_message_received(self, payload: dict) -> dict:
    # Modifica ou bloqueia
    if self.should_block(payload):
        return {"block": True, "reason": "rate_limit_exceeded"}
    return payload  # passa adiante
```

## LGPD compliance

Hooks que escutam `pii:detected` ou `lgpd:blocked` DEVEM:
- NUNCA logar PII cru (apenas hash + scrubbed)
- Documentar base legal em manifest
- Registrar leitura do hook no audit log (LGPD art. 37)

## Metric exposure

Cada hook emite metricas Prometheus:
- `openclaw_hook_total{hook_id, plugin, result}` — contador
- `openclaw_hook_duration_seconds{hook_id, plugin}` — histograma latencia

Modified by Gustavo Almeida