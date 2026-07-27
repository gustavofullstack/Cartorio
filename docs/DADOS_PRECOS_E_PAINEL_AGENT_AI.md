# Dados, preços e painel do Agent AI

## Fonte vigente de preços

O catálogo público do Agent AI usa somente itens de consulta direta da **Tabela 1 — Atos do Tabelião de Notas** da Portaria CGJ/TJMG nº 8.664/2025, com vigência a partir de **1º de janeiro de 2026**.

- Fonte primária: [PDF oficial do TJMG](https://www8.tjmg.jus.br/institucional/at/pdf/cpo86642025.pdf)
- Captura técnica: 2026-07-26
- SHA-256 do PDF capturado: `84781a023d6d51d9cf68a4d2ecd0c78b7fa3b0c04ba800be4d7e085aa7173417`
- Revisão operacional: pendente de validação do escrevente responsável antes de publicar qualquer novo item ou cálculo composto.

| Item publicado pelo agente | Referência TJMG | Emolumentos | TFJ | Valor final ao usuário |
| --- | --- | ---: | ---: | ---: |
| Reconhecimento de firma por assinatura | Tabela 1, item 5.a | R$ 8,55 | R$ 2,66 | R$ 11,21 |
| Autenticação de cópia por folha | Tabela 1, item 3 | R$ 8,55 | R$ 2,66 | R$ 11,21 |
| Procuração genérica por outorgante | Tabela 1, item 4.f.1 | R$ 52,43 | R$ 16,51 | R$ 68,94 |
| Testamento | Tabela 1, item 4.h.1 | R$ 332,64 | R$ 104,60 | R$ 437,24 |
| Ata notarial até duas folhas | Tabela 1, item 2.1 | R$ 166,18 | R$ 52,24 | R$ 218,42 |

## Regras de segurança do dado

O painel e a IA não podem apresentar como preço final os seguintes casos: escritura com conteúdo financeiro, inventário, divórcio com partilha, procuração em causa própria, usucapião, gratuidade, urgência, diligências, arquivamentos e atos acessórios. Eles dependem da composição concreta do ato e ficam em `HITL_REQUIRED` até a conferência do escrevente.

Dados pessoais nunca entram no painel. A coleta registra apenas: origem, URL, hash, vigência, instante de captura, estado da revisão, identificador do ato, componentes monetários e decisão de publicação. O texto do cliente é sanitizado antes de qualquer extração por IA e não é incluído nos eventos analíticos.

## Painel operacional proposto

O painel deve consumir uma visão agregada, sem PII, com quatro blocos:

1. **Qualidade da fonte**: fonte primária, hash, vigência, idade da captura e aprovação humana.
2. **Catálogo publicado**: ato, item da portaria, emolumentos, TFJ, valor final e escopo.
3. **Extração por IA**: volume por tipo de ato, confiança, taxa de encaminhamento ao escrevente e falhas de extração — sem texto, CPF, telefone, documento ou identificador de conversa.
4. **Operação**: consultas de preço, respostas com catálogo, handoffs e SLA do escrevente.

Estados permitidos: `CAPTURED`, `EXTRACTED`, `HUMAN_REVIEWED`, `PUBLISHED`, `SUPERSEDED`, `REJECTED`. O agente só lê registros `PUBLISHED` cuja vigência contenha a data da consulta; ausência ou expiração resulta em encaminhamento humano, nunca em preço inventado.

## Próxima coleta

Na publicação de nova tabela pelo TJMG, execute:

```bash
python3 scripts/collect_tjmg_emolumentos.py \
  --output /tmp/tjmg-emolumentos-manifest.json
```

O coletor baixa o PDF em diretório temporário, calcula SHA-256, confirma a identificação da portaria e grava apenas um manifesto `CAPTURED`. Depois, comparar com a versão anterior, revisar os itens e somente então promover os itens aprovados para `PUBLISHED`. A versão anterior permanece auditável e não é sobrescrita.
