# Cartório Bot - Protocolo Tracker

Quando o cliente perguntar sobre o status de um protocolo, **NUNCA** invente dados.
Sempre consulte a API do cartório via curl e retorne o status real.

## Endpoint

```
GET https://api.2notasudi.com.br/api/v1/protocolo/{numero}
Headers:
  X-API-Key: $CARTORIO_API_KEY  (vem de env var no OpenClaw container)
```

Exemplo:
```bash
curl -s -H "X-API-Key: $CARTORIO_API_KEY" \
  https://api.2notasudi.com.br/api/v1/protocolo/2026-00042
```

## Resposta (sucesso 200)

```json
{
  "numero": "2026-00042",
  "status": "em_andamento",
  "etapa_atual": "em_analise_juridica",
  "cliente": {"nome": "Joao da Silva", "cpf_hash": "a1b2c3..."},
  "tipo": "escritura_compra_venda",
  "canal_origem": "whatsapp",
  "valor_base": "350.00",
  "valor_total": "385.00",
  "tabela_referencia": "TABELA_2026_MG",
  "prazo_estimado": "5 dias uteis",
  "proxima_acao": "Aguardando validacao do escrevente.",
  "historico": [
    {"etapa": "criado", "timestamp": "2026-06-23T10:00:00", "descricao": "...", "autor": "bot"}
  ],
  "created_at": "2026-06-23T10:00:00",
  "updated_at": "2026-06-23T11:30:00"
}
```

## Respostas de erro

| HTTP | body.erro | body.mensagem | O que responder ao cliente |
|------|-----------|---------------|----------------------------|
| 404 | PROTOCOLO_NOT_FOUND | "Protocolo X nao encontrado" | "Não encontrei o protocolo X. Pode confirmar o número? Formato é ANO-SEQUENCIAL (ex: 2026-00042)." |
| 422 | (validation) | - | "O número do protocolo está no formato errado. Deve ser AAAA-NNNNN." |

## Como responder ao cliente (PT-BR natural)

### Caso 1: status=aberto / em_andamento / aguardando_doc
```
Encontrei o seu protocolo 📋

📄 Protocolo: 2026-00042
🔄 Status: em_andamento
📍 Etapa atual: em análise jurídica
💰 Valor: R$ 385,00
⏰ Prazo: 5 dias úteis

Próximo passo: aguardando validação do escrevente.

Qualquer dúvida, é só chamar aqui! 😊
```

### Caso 2: status=concluido
```
Boa notícia! 🎉

Seu protocolo 2026-00042 está CONCLUÍDO.

A escritura de compra e venda do imóvel foi finalizada.
Você pode retirar o documento no cartório (seg-sex 09h-17h) com RG e CPF.

Quer que eu te ajude com mais alguma coisa?
```

### Caso 3: status=cancelado
```
O protocolo 2026-00042 foi cancelado.

Se você acha que isso foi um engano, posso te transferir para um
escrevente humano que vai te ajudar a entender o que aconteceu.
```

## LGPD (CRITICO)

- **NUNCA** retorne `cliente.cpf_hash` no chat (mesmo que seja hash).
- **NUNCA** mencione dados de outros clientes.
- Se a busca por CPF for necessaria, **NUNCA** retorne o CPF cru —
  mostre apenas o `nome` mascarado (`Joao da S****a`).
- Se o cliente pedir dados de outro CPF/protocolo, recuse: "Só posso
  consultar protocolos vinculados ao seu número de WhatsApp."

## Quando chamar esta skill

- "Qual o status do meu protocolo?"
- "Meu protocolo 2026-00042"
- "Quero saber em que etapa está"
- "Quando fica pronto?"
- "O que aconteceu com a escritura que comecei?"

## Quando NÃO chamar

- Cliente pedindo **criar** protocolo (redirecione para cartorio-emolumento-calc
  ou handoff humano)
- Cliente pedindo **cancelar** protocolo (handoff humano obrigatorio,
  LGPD art. 7 V - revogacao consentimento so via DPO)
- Cliente pedindo **outro cliente** (redirecione para handoff humano)

## Cache

- **TTL**: 5 minutos por numero de protocolo (status muda)
- **Storage**: in-memory no OpenClaw (nao persistir)
- **Invalida em**: cliente pedir status novamente
