# Plugins - OpenClaw Agent (CartórioBot)

Plugins sao modulos passiveis de hook no ciclo de vida do OpenClaw Agent
que adicionam funcionalidades SEM modificar o core. Diferente de skills
(que sao declarativas - arquivos .md), plugins sao codigo executavel
que pode interceptar eventos, transformar mensagens, ou integrar com
sistemas externos.

## Convecao de nomenclatura

- Diretorio: `infra/openclaw-agent/plugins/<nome-do-plugin>/`
- Manifesto: `plugin.yaml` (metadados)
- Entry point: `main.py` (codigo do plugin)
- Hooks declarados: `hooks.yaml` (eventos que escuta)

## Plugins registrados

| Plugin | Tipo | Hooks | Status | Versao |
|--------|------|-------|--------|--------|
| (placeholder) | - | - | - | - |

## Como adicionar um novo plugin

1. Criar diretorio `plugins/<nome>/`
2. Implementar `plugin.yaml` com metadados:
   ```yaml
   name: meu-plugin
   version: 1.0.0
   description: O que faz
   author: Gustavo Almeida
   hooks:
     - on_message_received
     - on_message_sent
     - on_skill_invoked
     - on_session_start
     - on_session_end
   config:
     # configuracoes especificas do plugin
     some_key: some_value
   ```
3. Implementar `main.py` com classe `Plugin`:
   ```python
   from openclaw_plugin_sdk import PluginBase

   class MeuPlugin(PluginBase):
       name = "meu-plugin"
       version = "1.0.0"

       async def on_message_received(self, message: dict) -> dict:
           # Pode modificar ou bloquear mensagem
           return message
   ```
4. Adicionar entrada na tabela acima
5. Documentar em `docs/platforms/OPENCLAW.md` (se existir)
6. Adicionar tests em `backend/tests/test_plugin_<nome>.py`

## Hooks disponiveis

| Hook | Quando dispara | Pode bloquear? |
|------|----------------|----------------|
| `on_session_start` | Inicio de nova sessao | Nao |
| `on_session_end` | Fim de sessao (timeout/disconnect) | Nao |
| `on_message_received` | Cliente envia mensagem (pre-skill) | Sim (handoff) |
| `on_message_sent` | Bot envia resposta (post-LLM) | Nao |
| `on_skill_invoked` | Skill eh acionada | Nao |
| `on_handoff_trigger` | Handoff humano eh acionado | Nao |
| `on_pii_detected` | PII scrub detecta dado sensivel | Sim (ja bloqueia) |
| `on_lgpd_block` | LGPD gate bloqueia acao | Sim (ja bloqueia) |

## LGPD compliance

Todo plugin DEVE:
- NUNCA logar PII em texto puro (usar hash + scrubbed)
- Respeitar `motivo_encerramento` do cliente (LGPD art. 18 VI)
- Registrar acao no audit log via `AuditService.log()`
- Documentar base legal (LGPD art. 7o) em `plugin.yaml`

## Seguranca

- Plugins rodam em subprocesso isolado (sandbox)
- Permissoes declaradas em `plugin.yaml` sao enforced
- Timeout obrigatorio: 5s por hook (fail-fast)
- Network access: whitelist apenas dominios configurados

Modified by Gustavo Almeida