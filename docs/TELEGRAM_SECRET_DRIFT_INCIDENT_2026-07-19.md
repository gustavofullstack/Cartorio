# Incidente Telegram — divergência de segredo local/produção

**Data:** 2026-07-19  
**Escopo:** `@test_cartorio_bot`, webhook `https://api.2notasudi.com.br/api/v1/telegram/webhook`  
**Impacto:** mensagens privadas e de grupo chegam sem resposta.

## Evidência sanitizada

| Verificação | Ambiente | Resultado |
|---|---|---|
| Bot API `getMe` | `.env` local | HTTP 200; bot identificado como `test_cartorio_bot` |
| `getWebhookInfo` | `.env` local | HTTP 200; URL canônica, zero pendências e sem erro recente |
| `GET /api/v1/telegram/webhook/info` | produção | HTTP 401 `Unauthorized` |
| `GET /api/v1/telegram/health` | produção | `configured=true` (não valida autenticação no Bot API) |

Conclusão: há divergência entre o segredo usado localmente e o segredo
provisionado em produção (ou o segredo de produção foi revogado). O endpoint
webhook pode continuar acessível, mas toda chamada de saída (`sendMessage`,
`sendChatAction`, `getWebhookInfo`) falha com 401. Não é um problema de
permissão do grupo nem de modelo LLM.

## Validação segura (sem imprimir segredos)

Execute em sessão protegida, com o token injetado pelo gerenciador de segredos
(não cole o valor em arquivos ou comandos versionados):

```bash
set +x
curl -fsS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" \
  | jq '{ok, result: {id: .result.id, is_bot: .result.is_bot, username: .result.username}}'

curl -fsS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" \
  | jq '{ok, result: {url: .result.url, pending_update_count: .result.pending_update_count, last_error_date: .result.last_error_date, last_error_message: .result.last_error_message}}'
```

O primeiro comando deve retornar `ok: true`; o segundo deve mostrar a URL
canônica, `pending_update_count: 0` e ausência de `last_error_message`.
Respostas 401/403 indicam token inválido ou revogado.

## Remediação controlada

1. No BotFather, confirme que o token atualmente autorizado pertence ao
   `@test_cartorio_bot`. Se estiver revogado, um operador autorizado deve
   emitir um token novo.
2. Atualize **somente** o segredo `TELEGRAM_BOT_TOKEN` no secret manager do
   serviço de produção e mantenha `TELEGRAM_WEBHOOK_SECRET` igual ao valor
   usado no registro do webhook. Nunca grave em Git, imagem Docker ou log.
3. Reinicie/reimplante o serviço da API para carregar os segredos. Não altere
   código nem banco para esta correção.
4. Registre o webhook usando o helper existente, que não imprime o token:

   ```bash
   python3 scripts/telegram_set_webhook.py --apply
   ```

5. Repita as validações acima e, então, faça um smoke test humano: `/start` no
   PV e `@test_cartorio_bot /start` no grupo. Mensagens livres de grupo sem
   menção são ignoradas de propósito (anti-spam/privacy).

## Rollback

Se a validação pós-restart falhar, restaure o último par de segredos conhecido
como válido no secret manager, reinicie o serviço e execute novamente
`setWebhook`. Não faça rollback para valores presentes no Git, nem remova o
webhook como tentativa de diagnóstico. Se não houver segredo válido conhecido,
pare no estado degradado e escale ao operador do BotFather; não tente adivinhar
ou rotacionar credenciais.

**Modified by Gustavo Almeida**
