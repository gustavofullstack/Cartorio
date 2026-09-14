# Monitoramento Evolution — G8.22.T2

## Objetivo

O workflow `WF-TEMPLATE Monitoramento Evolution` consulta a conexão da instância Evolution a cada cinco minutos. Quando o estado deixa de ser `open`, coleta o status, alerta o escrevente no Telegram e registra `evolution_disconnect_alert` no audit log conforme o Art. 37 da LGPD.

O template é importado inativo. Revise as variáveis, vincule a credencial do Telegram e execute o teste manual antes de ativar.

## Schedule

- Trigger: `scheduleTrigger`.
- Intervalo: cinco minutos.
- Timeout: cada chamada HTTP é limitada a 30 segundos.
- Estado saudável: `instance.state == open`; encerra em `NoOp (online)`.
- Estado desconectado: consulta `/instance/status`, alerta e audita.

## Variáveis de ambiente

| Variável | Uso |
|---|---|
| `EVOLUTION_API_URL` | URL base da Evolution API, sem barra final |
| `EVOLUTION_API_KEY` | Chave global usada apenas nos endpoints `/instance/*` |
| `EVOLUTION_INSTANCE` | Nome técnico da instância monitorada |
| `ESCREVENTE_TELEGRAM_CHAT_ID` | Chat interno que recebe o alerta |

Não grave valores reais no JSON. O token do bot deve permanecer em uma credencial Telegram do N8N, selecionada após a importação.

## LGPD

O alerta contém zero PII: somente o nome técnico da instância e o status retornado pela Evolution. Não inclua telefone, nome de cliente, mensagem, CPF, RG, protocolo ou payload de execução. O registro de auditoria usa apenas valores estáticos operacionais.

## Ativação e validação

1. Importe `infra/n8n-workflows/template-monitoramento-evolution.json` no N8N.
2. Configure as quatro variáveis e associe a credencial Telegram.
3. Confirme que a instância online segue para `NoOp (online)` sem alerta.
4. Use `workflow_dispatch` para forçar o ramo de alerta com status sintético em sandbox; não desconecte nem consulte a instância real para este teste.
5. Confirme a entrega no chat interno e a entrada `evolution_disconnect_alert` no audit log.
6. Remova os dados sintéticos fixados e ative o schedule somente após revisão HITL.

## Resposta ao alerta

1. Acesse `whatsapp.2notasudi.com.br/manager`.
2. Verifique o estado da instância e gere novo QR code quando necessário.
3. Solicite reconexão pelo responsável autorizado.
4. Aguarde a próxima execução ou rode manualmente; o estado esperado é `open`.
5. Registre a intervenção operacional sem inserir PII.

## Rollback

Desative o workflow no N8N. Isso interrompe novas consultas e alertas sem alterar a instância Evolution nem apagar registros de auditoria.

Modified by Gustavo Almeida + cartorio-n8n — G8.22.T2.
