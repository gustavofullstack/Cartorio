# Lesson 264 — G8.22.T2 monitoramento da conexão Evolution (2026-07-18)

## Contexto

A conexão WhatsApp da instância Evolution podia cair sem um alerta operacional específico. A task exigia um artefato importável e validável offline, sem consultar ou alterar a Evolution real.

## Decisão

O template `template-monitoramento-evolution.json` executa a cada cinco minutos, consulta `connectionState` e encerra sem efeito quando `instance.state` está `open`. Qualquer outro estado segue para consulta de status, alerta Telegram do escrevente e registro no endpoint de auditoria.

O template permanece inativo no repositório. URL, chave, instância e chat são referências a variáveis do ambiente N8N; nenhum segredo é persistido no export.

## LGPD

O alerta usa somente nome técnico da instância e status. Não consulta nem transmite mensagens, telefones, clientes, documentos ou protocolos. A auditoria recebe valores operacionais estáticos e não carrega PII.

## Otimização

O cron de cinco minutos equilibra tempo de detecção e carga. Cada HTTP request tem timeout máximo de 30 segundos, e o caminho saudável termina imediatamente em um NoOp.

## Operação

O ramo de alerta deve ser validado com status sintético por execução manual em sandbox. Desconectar a instância real para testar monitoramento cria indisponibilidade evitável e não é necessário para validar o workflow.

## Validação

- inventário básico: 41 workflows, zero JSON inválido;
- inventário estrito: 41 workflows válidos;
- teste dedicado: 11 passed;
- Ruff do arquivo novo: zero erros e formato válido;
- mypy: zero erros em 197 arquivos;
- suíte completa: 4379 passed, 23 skipped e 2 falhas fora do escopo;
- `test_scrub_response_nao_altera_audit_metadata` continua falhando isoladamente por esperar IP bruto, regressão prévia já registrada na Lesson 260;
- `test_openapi_security_scheme_defined` passa isoladamente e continua com falha dependente da ordem do cache OpenAPI, também registrada na Lesson 260;
- Ruff global continua bloqueado pelo F841 pré-existente em `tests/test_alert_to_telegram_g8.py:266`.

Modified by Gustavo Almeida + cartorio-n8n — G8.22.T2.
