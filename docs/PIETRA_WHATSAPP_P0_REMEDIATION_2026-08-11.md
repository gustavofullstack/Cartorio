# Pietra WhatsApp — P0 remediation (2026-08-11)

## Resultado

O defeito da captura era reproduzível em código: o adapter Evolution fazia
`text[:800]`, descartando o restante e podendo cortar uma palavra. A camada de
consentimento também concedia LGPD automaticamente no primeiro contato e a
reserva de idempotência rejeitava o payload root-level antes do parser dual.

Correções locais nesta branch:

- `split_whatsapp_text()` fragmenta por parágrafo/espaço e envia todos os
  blocos, preservando UTF-8 e botões somente no último bloco.
- `evolution_ingest` aceita payload nested e root-level antes da idempotência.
- WhatsApp exige `SIM` explícito; `PARAR` continua revogando consentimento.
- Logs de consentimento e do webhook legado usam hash do remetente, nunca o
  telefone bruto.
- Memória persistente aplica scrub de conteúdo e metadados textuais antes de
  Postgres/Redis.
- Saída final corrige um vocabulário fechado de erros de acentuação PT-BR;
  não tenta “corrigir” nomes, números ou texto do cliente.
- Workflows N8N 12/EVO-IN tiveram conexões corrigidas para nomes de nós,
  parser moderno preservado e segredo literal removido; WF14 também usa a
  credencial `cartorio-api-key` em vez de valor no JSON.

## Evidência de validação

- Testes focados Pietra/WhatsApp: **31 passed**.
- Testes de regressão de saída/memória: **5 passed**.
- Ruff nos arquivos tocados: **0 erros**.
- Mypy nos arquivos tocados: **0 erros**.
- JSON N8N 12, 14 e EVO-IN: válido.
- Scanner `backend/scripts/check_no_literal_keys.py`: zero violações.

## Piloto WhatsApp (2026-08-11 tarde)

Somente estes números passam da ACL (HMAC + E.164 canônico):

| Pessoa | Número |
| :--- | :--- |
| Felipe Pizarro | +55 34 99880-7228 |
| Gustavo Almeida | +55 34 99280-0250 |

`PIETRA_WHATSAPP_RESTRICT_INBOUND=true` + hashes vazios usa esse piloto.
`APP_ENV` **não** governa a ACL (produção estava com `APP_ENV=test`).

## Tabela oficial (Felipe / dossier Djalma Pizarro / TJMG 2026)

| Ato | Valor final |
| :--- | :--- |
| Abertura de firma / autenticação cópia / reconhecimento | R$ 11,21 |
| Autenticação documento eletrônico | R$ 12,99 |
| Procuração genérica | R$ 68,94 |
| Procuração previdenciária | R$ 36,61 |
| Ata notarial até 2 folhas | R$ 218,42 |
| Testamento público (item básico) | R$ 437,24 |
| Horário de balcão | seg–sex 09h–17h (sem sábado regular) |
| Endereço | Rua Cel. Antônio Alves Pereira, 850, Centro |
| Titular | Djalma Pizarro (substitutos: Felipe Pizarro, Alexandra José Beicker) |
| Telefones | (34) 3216-0252 / (34) 3215-7048 / WA (34) 99195-2444 |

ITBI Uberlândia: 2%. Testamento: 2 testemunhas. PDF eletrônico ≠ cópia física.

## Estado operacional observado (SSH 2026-08-11 16:27 UTC)

- `cartorio_system-api` 1/1 atende a API pública. `cartorio_api` 0/1.
- Redis efetivo: `cartorio_memory-cache`. Evolution: `cartorio_whatsapp-api`.
- Sessão WhatsApp `cartorio-agent`: open.
- Radar: amarelo (OpenClaw e Chatwoot offline).
- Container ainda **não** tinha `whatsapp_access` até o deploy desta branch.

## Ações obrigatórias antes do deploy

1. Revogar e emitir nova chave do provedor cujo token aparece exposto na
   captura (não copiar o valor para issues, logs ou commits). Atualizar o
   secret manager e conferir `MINIMAX_MODEL=MiniMax-M3`/proxy LiteLLM.
2. Disponibilizar a chave SSH operacional ou acesso EasyPanel autorizado para
   validar/recuperar OpenClaw e Chatwoot.
3. Reexportar N8N após importar os JSONs corrigidos, validar as credenciais e
   ativar os workflows pelo painel; não usar PATCH na API N8N 2.x.
4. Executar `make qa` com Python/uv disponíveis, obter revisão `cartorio-lgpd`
   para mudanças de PII/outbound e fazer smoke round-trip com Felipe.

## Limites

A normalização ortográfica é deliberadamente pequena e determinística. Atos
jurídicos, isenção, urgência, validade, emissão e protocolo permanecem HITL;
esta correção não autoriza o bot a decidir esses casos.

