# Migração segura do cálculo de emolumentos

## Decisão

Os endpoints históricos `/api/v1/emolumento/calcular` e `/api/v1/emolumentos/calcular-api` usam a tabela `EMOLUMENTOS_2026` marcada no código como *placeholder*. Eles não devem ser fonte de preço do Agent AI.

O contrato novo e verificável é:

| Objetivo | Endpoint | Resultado |
| --- | --- | --- |
| Catálogo e proveniência | `GET /api/v1/emolumentos/real/djalma` | Itens `PUBLISHED`, hash, fonte e vigência |
| Consulta de item/triagem | `POST /api/v1/emolumentos/real/calcular` | `PUBLISHED` com valor final ou `HITL_REQUIRED` sem total |
| Extração sanitizada | `POST /api/v1/emolumentos/real/extrair-ai` | Sinais sanitizados, decisão e auditoria persistida pela rota |
| Dados do painel | `GET /api/v1/inteligencia-dados/agent-ai` | Catálogo + uso agregado em memória, sem PII |
| Interface do painel | `GET /api/v1/painel/agent-ai` | HTML que consome o contrato acima |

## Consumidores migrados no repositório

- `infra/n8n-workflows/01-consulta-emolumento.json` — chama o contrato seguro e responde handoff em `HITL_REQUIRED`.
- `infra/n8n-workflows/38-emolumento-calculator.json` — chama o contrato seguro e não apresenta breakdown inventado.
- `infra/openclaw-agent/agent-tools-registry.json` — tool `2.0.0` aponta ao endpoint seguro.
- `infra/openclaw-agent/skills/cartorio-emolumento-calc.md` — catálogo e respostas atualizados.
- `infra/openclaw-agent/workspace/SOUL.md` — instrução de comportamento atualizada.

As definições locais foram migradas; ativação em produção depende da importação controlada dos workflows no n8n e de uma rodada de aceitação do canal. Não é seguro trocar somente a URL: os identificadores e o contrato de resposta são diferentes.

## Sequência de corte

1. Implantar o backend que contém os endpoints novos. Não importar workflow antes disso: em 2026-07-26 a API pública ainda respondia `404` para o contrato novo.
2. Fazer smoke sem PII contra produção:

   ```bash
   curl -fsS https://api.2notasudi.com.br/api/v1/emolumentos/real/djalma
   curl -fsS -X POST \
     'https://api.2notasudi.com.br/api/v1/emolumentos/real/calcular?tipo_ato=procuracao_geral'
   ```

   O primeiro deve retornar fonte/hash/vigência; o segundo deve retornar `PUBLISHED` e `68.94`.
3. Exportar backup do workflow n8n ativo, importar os dois workflows em staging e testar `PUBLISHED` para autenticação, firma e procuração geral; testar `HITL_REQUIRED` para escritura, urgência, folhas extras e isenção.
4. Atualizar o workflow remoto ativo somente após os smokes e observar em Prometheus `cartorio_agent_ai_extracoes_total` e `cartorio_agent_ai_handoffs_total` durante uma janela controlada.
5. Marcar os endpoints legados como descontinuados na OpenAPI e remover sua exposição dos agentes.
6. Após uma janela de compatibilidade aprovada, retirar a tabela placeholder e seus testes de valor fixo.

## Estado remoto observado

- `flow.2notasudi.com.br/healthz`: `200` em 2026-07-26.
- O workflow remoto ativo “01 - Consulta Emolumento WhatsApp (v3)” tem ID distinto do export local e ainda aponta ao contrato legado.
- A API pública ainda não expõe o catálogo seguro; por isso nenhuma atualização de workflow foi enviada.

Nenhuma etapa autoriza publicar novos preços sem manifesto `CAPTURED`, revisão humana e promoção explícita para `PUBLISHED`.
