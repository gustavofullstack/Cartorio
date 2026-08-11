# Pietra WhatsApp — ativação segura da allowlist

Status: piloto Felipe + Gustavo. Runtime público atual = `cartorio_system-api`.

## Pré-requisitos de produção

- Publicar a imagem no serviço que realmente atende `api.2notasudi.com.br`
  (`cartorio_system-api` 1/1). `cartorio_api` 0/1 não é a borda viva.
- `PIETRA_WHATSAPP_RESTRICT_INBOUND=true` (default). `APP_ENV` **não** governa
  a ACL — produção já rodou com `APP_ENV=test` e isso abria o bot.
- Hashes extras são opcionais. Lista vazia + restrict=true usa o piloto
  embutido: Felipe `+5534998807228` e Gustavo `+5534992800250`.
- Chave HMAC: `PIETRA_WHATSAPP_ALLOWLIST_HMAC_KEY` (32+) ou fallback
  `AUDIT_HMAC_KEY`. Nunca logar telefone/JID bruto.

Cada hash extra é HMAC-SHA256 do E.164 normalizado (incluindo `+`):

```text
HMAC-SHA256(ALLOWLIST_OR_AUDIT_KEY, "+55DDDNXXXXXXXX")
```

## Comportamento esperado

| Situação | Resultado |
| --- | --- |
| Felipe ou Gustavo (piloto) | Pode seguir para idempotência, consentimento e pipeline. |
| Remetente fora da lista | HTTP 200 `sender_not_authorized`; sem banco, Redis, consentimento, LLM ou resposta. |
| Grupo, broadcast ou LID sem `remoteJidAlt` | Bloqueado. |
| LID com `remoteJidAlt` autorizado | Permitido; a resposta mantém o LID original. |
| `restrict_inbound=false` | Aberto — somente suíte local / conftest. |

## Validação pós-publicação

1. Confirme `cartorio_api 1/1` e `GET /health` com resposta do serviço recém-publicado.
2. Envie um texto neutro de cada contato autorizado e confirme uma única resposta.
3. Envie um texto neutro de um contato não autorizado e confirme ausência de resposta e aumento da métrica `cartorio_whatsapp_acesso_bloqueado_total`.
4. Confirme no log somente `reason`, nunca telefone/JID bruto.
5. Não ative/importa o EVO-IN n8n antes de reconciliar o runtime e corrigir sua idempotência; o backend é a fronteira obrigatória de autorização.
