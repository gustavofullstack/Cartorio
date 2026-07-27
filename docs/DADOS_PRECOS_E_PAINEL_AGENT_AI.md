# Dados, preços e painel do Agent AI

## Fonte vigente de preços

O catálogo público do Agent AI usa somente itens de consulta direta da **Tabela 1 — Atos do Tabelião de Notas** da Portaria CGJ/TJMG nº 8.664/2025, com vigência a partir de **1º de janeiro de 2026**.

- Fonte primária: [PDF oficial do TJMG](https://www8.tjmg.jus.br/institucional/at/pdf/cpo86642025.pdf)
- Captura técnica: 2026-07-26
- Integridade revalidada: 2026-07-27, por download direto do PDF oficial.
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

## Painel operacional (implementado — Fase 4)

O painel consome uma visão agregada, sem PII, com quatro blocos servidos por endpoints reais sob `/api/v1/painel`:

1. **Qualidade da fonte** — `GET /api/v1/painel/fonte`: fonte primária, hash SHA-256, vigência, idade da captura (`idade_dias`, calculada no servidor) e aprovação humana (`revisado_por`/`revisado_em` da captura `PUBLISHED` mais recente; sem banco, fallback para as constantes versionadas da Portaria 8.664/2025).
2. **Catálogo publicado** — `GET /api/v1/painel/catalogo`: ato, item da portaria, emolumentos, TFJ, valor final e escopo, dos itens `PUBLISHED` vigentes no banco (fallback para o catálogo público versionado quando o banco está vazio/indisponível).
3. **Extração por IA** — `GET /api/v1/painel/extracao`: extrações por `outcome`, handoffs por `reason` e fallbacks de LLM por `reason` (contadores em memória do processo) — sem texto, CPF, telefone, documento ou identificador de conversa.
4. **Operação** — `GET /api/v1/painel/operacao`: consultas ao `POST /api/v1/emolumentos/real/calcular` por `outcome` (contador `cartorio_agent_ai_consultas_total`), handoffs e taxa de handoff (divisão por zero tratada).

Complementar: `GET /api/v1/painel/ia-usage?dias=30` (≤ 365) expõe a telemetria agregada do LiteLLM (Fase 3). Interfaces: `/painel/agent-ai` (mesa de evidências) e `/dashboard`, ambas com refresh periódico leve (60s) e estado "indisponível" por bloco quando um endpoint falha.

Em 2026-07-27, as quatro rotas públicas dos blocos (`fonte`, `catalogo`,
`extracao` e `operacao`) responderam HTTP 200 via HTTPS. Isso confirma a
disponibilidade das rotas; a prova anti-PII continua sendo o contrato
automatizado, não a mera resposta HTTP.

Estados permitidos: `CAPTURED`, `EXTRACTED`, `HUMAN_REVIEWED`, `PUBLISHED`, `SUPERSEDED`, `REJECTED`. O agente só lê registros `PUBLISHED` cuja vigência contenha a data da consulta; ausência ou expiração resulta em encaminhamento humano, nunca em preço inventado.

## Próxima coleta

Na publicação de nova tabela pelo TJMG, execute:

```bash
python3 scripts/coletar_tabela_tjmg.py --salvar-evidencia
```

O coletor baixa o PDF em diretório temporário, calcula SHA-256, confirma a identificação da portaria e, com `--salvar-evidencia`, grava um manifesto `CAPTURED`. Depois, comparar com a versão anterior, revisar os itens e somente então promover os itens aprovados para `PUBLISHED`. A versão anterior permanece auditável e não é sobrescrita. Para o inventário completo e as regras de coleta externa, consulte `docs/MAPA_DADOS_E_COLETA_EXTERNA.md`.
