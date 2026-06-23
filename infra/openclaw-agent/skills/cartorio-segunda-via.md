# Cartório Bot - Segunda Via de Documento

Quando o cliente pedir uma copia adicional de um documento ja emitido (escritura,
certidao, procuracao registrada), use esta skill.

## Endpoint

```
GET https://api.2notasudi.com.br/api/v1/documento/segunda-via?protocolo_id=42&formato=pdf
Headers:
  X-API-Key: $CARTORIO_API_KEY
```

Response 200:
```json
{
  "protocolo_id": 42,
  "numero": "2026-00001",
  "tipo": "escritura_compra_venda",
  "url_pdf": "https://supbase.2notasudi.com.br/storage/v1/object/sign/documentos/2026-00001/escritura.pdf?token=...",
  "expira_em": "2026-06-25T23:59:59Z",
  "custo_emolumento": "R$ 25,00",
  "observacoes": "Taxa de segunda via conforme TABELA_2026_MG."
}
```

## Como responder ao cliente (PT-BR natural)

### Caso 1: documento existe, segunda via disponivel
```
Achei o seu documento! 📄

📋 Protocolo: 2026-00001
📄 Tipo: escritura_compra_venda
💰 Custo segunda via: R$ 25,00

📎 Link para download: [link_pdf]
⏰ Link expira em 24h.

Voce pode:
1. Baixar agora pelo link acima
2. Pedir para retirar copia fisica no cartorio (seg-sex 09h-17h)

Como prefere?
```

### Caso 2: protocolo nao encontrado
```
Hmm, nao encontrei o protocolo [numero] no nosso sistema.

Voce pode:
1. Confirmar o numero (formato AAAA-NNNNN)
2. Pedir para um escrevente verificar via [handoff-trigger]
```

### Caso 3: documento nao concluido ainda
```
O protocolo 2026-00001 ainda esta em [status]. 

Documentos so ficam disponiveis para segunda via APOS a conclusao do ato.

Quer que eu te avise quando ficar pronto?
```

## LGPD

- Link do PDF eh assinado (token JWT) e expira em 24h
- **NAO** exibir link em chat publico - usar link assinado com expiracao
- Logar toda requisicao de segunda via (LGPD art. 37 - direito de acesso)
- Limite: maximo 3 segundas vias por protocolo por mes (anti-fraude)

## Quando NAO gerar segunda via (handoff)

- Cliente eh terceiro (nao titular) - exige autorizacao formal
- Documento com mais de 5 anos (Provimento CNJ 74/2018 - retencao minima)
- Cliente sem CPF no sistema - handoff para identificacao
- Suspeita de fraude - alertar DPO

## Edge cases

- PDF indisponivel (storage offline): "Tivemos uma instabilidade no storage. Tente em 5 minutos."
- Token expirado: cliente clica e recebe 403; oferecer novo link
- URL muito longa (>2000 chars): encurtar com bit.ly (cuidado: link externo)
