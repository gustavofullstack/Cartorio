# Mapa de dados e coleta externa — Agent AI Cartório

**Escopo:** 2º Serviço Notarial de Uberlândia (Djalma).  
**Atualizado em:** 2026-07-26.  
**Método de inventário:** modelos SQLAlchemy, migrations Alembic, `infra/supabase/schema.sql`, integrações versionadas e verificação somente-leitura da VPS. Este documento descreve a estrutura e os fluxos; não consulta nem reproduz dados de clientes.

## 1. Estado operacional verificado

Na VPS `Cartorio`, a verificação em 2026-07-26 encontrou saudáveis e em execução: API do Cartório, Supabase/Postgres, Redis, n8n, Evolution API, Chatwoot e `cartorio_openclaw-gateway`.

**Não foi encontrado serviço, container ou processo `Hermes` na VPS.** Portanto, não é correto afirmar que o Agent Hermes Cartório esteja rodando nela. A VPS tem o **OpenClaw** como gateway de IA visível. A confirmação de Hermes exige uma nova evidência do runtime específico (processo/serviço e uma resposta real pelo canal), pois disponibilidade de infraestrutura não prova operação fim a fim.

## 2. Mapa da base de dados

O Postgres/Supabase é o banco durável. Redis é infraestrutura efêmera para cache, idempotência, rate limit, locks e filas. Os dados se dividem assim:

| Domínio | Tabelas/modelos principais | Conteúdo | Tratamento para análise |
| --- | --- | --- | --- |
| Cadastro e LGPD | `clientes`, `lgpd_consent_log`, `lgpd_consents`, `opt_out_log` | identidade, contato, consentimento e preferências | PII/sensível; análise só agregada ou pseudonimizada, com base legal e controle de acesso |
| Conversas e atendimento | `conversas`, `atendimentos`, `mensagens`, `sessoes_chat`, `chatwoot_conversation_meta`, `telegram_chat_meta` | canal, intenção, handoff, atendimento humano e metadados de mensagens | texto não entra em dashboard; usar métricas agregadas por canal, intenção e período |
| Atos e operação notarial | `protocolos`, `documentos`, `agendamentos`, `emolumentos`, `mv_protocolo_stats`, `mv_protocolo_aging`, `mv_emolumento_stats` | protocolo, documentos, agenda, composição de preço e visão operacional | jurídico/documental: acesso por função; agente somente propõe e sempre respeita HITL |
| Integração e entrega | `webhook_events`, `webhook_event_dlq`, `outbox_messages`, `n8n_run_log`, `evolution_instance`, `atendimento_link` | idempotência, eventos recebidos, fila de saída e execução de automações | não usar payload bruto como dataset analítico; reter hashes, status, duração e erro categorizado |
| Governança | `audit_log`, `cnj_export_requests`, `lgpd_audit_anpd` | trilha imutável, exportações regulatórias e prestação de contas | append-only; não editar nem usar como fonte de enriquecimento de perfil |
| Plataformas de agentes/n8n | famílias `agent_*`, `agents_*`, `instance_ai_*`, `workflow_*`, `execution_*`, `credentials_*` | estado técnico de agentes, workflows, execuções e credenciais | inventário técnico; segredos e logs brutos ficam fora de extrações e painéis |

Há também tabelas de infraestrutura e autenticação no dump do Supabase. Elas não são fonte de negócio e devem ficar fora de relatórios do cartório. A separação acima é obrigatória para evitar que dados de operação de ferramentas ou credenciais sejam confundidos com dados notariais.

### Fluxo de dados atual

```text
WhatsApp / Telegram / Web
          -> Evolution / Telegram webhook / Chatwoot
          -> API FastAPI (scrub PII, idempotência, rate limit)
          -> Postgres/Supabase + Redis + audit log
          -> n8n / OpenClaw / atendimento humano
          -> painel agregado sem PII
```

Todo ato jurídico nasce como `DRAFT`; preço composto, urgência, gratuidade e validação documental exigem revisão humana. A auditoria é encadeada com hash/HMAC e não pode ser alterada retroativamente.

## 3. Fontes externas: ordem de prioridade

| Prioridade | Fonte | Método recomendado | Uso permitido | Regra de publicação |
| --- | --- | --- | --- | --- |
| P0 | [Portarias e tabelas do TJMG](https://www8.tjmg.jus.br/institucional/at/pdf/cpo86642025.pdf) | download direto de PDF oficial (`web fetch`) | preços, vigência e itens normativos | hash + parser + comparação + revisão do escrevente |
| P0 | [Justiça Aberta/CNJ](https://www.cnj.jus.br/justica-aberta/) | exportação CSV/XLSX ou consulta pública suportada | dados estatísticos e cadastrais públicos de serventias | salvar URL, data, versão e licença/termos; não inferir dados pessoais |
| P1 | [Atos normativos do CNJ](https://atos.cnj.jus.br/) | busca e download de atos oficiais | mudanças regulatórias e alertas de revisão | extração textual versionada, com fonte e revisão jurídica |
| P1 | DJe/TJMG | coleta de edição/PDF público, somente de assuntos pré-definidos | portarias, comunicados e prazos | lista controlada de termos, deduplicação por URL/hash e revisão humana |
| P2 | Portais públicos municipais/estaduais | API pública primeiro; `web fetch` apenas em páginas estáveis | agenda pública, endereço e informação institucional | análise de termos, responsável e periodicidade antes de ativar |

O CNJ informa que o Justiça Aberta reúne dados de serventias e que seu painel permite relatórios CSV/XLSX; esses formatos são preferíveis a scraping de páginas. Fontes autenticadas, restritas, com CAPTCHA, dados de terceiros, processos individuais, redes sociais ou cadastros contendo PII **não entram** em crawler.

## 4. Padrão técnico para web fetch, scraping e crawling

1. **Registrar a fonte:** órgão, finalidade, base legal/termos, URL canônica, dono interno, frequência e classificação LGPD.
2. **Preferir API/exportação:** API oficial, CSV/XLSX/RSS ou PDF assinado antes de HTML scraping.
3. **Checar permissão:** `robots.txt`, termos de uso, autenticação, limite de requisições e eventual restrição de redistribuição. Sem permissão clara, o conector fica em `PROPOSED`.
4. **Coletar de modo gentil:** identificador de cliente, timeout, rate limit baixo, retry com backoff, cache por ETag/Last-Modified e sem contornar CAPTCHA/bloqueio.
5. **Preservar evidência:** URL, timestamp, HTTP status, hash do arquivo, versão do parser, tipo de conteúdo e licença/termos conhecidos.
6. **Extrair em ambiente isolado:** PDF/HTML para dados estruturados; PII deve ser descartada ou sanitizada antes de LLM, log ou analytics.
7. **Validar:** schema, faixa de valores, vigência, duplicidade e divergência contra a versão anterior.
8. **Revisar e publicar:** estados `CAPTURED -> EXTRACTED -> HUMAN_REVIEWED -> PUBLISHED`; erro ou dúvida vira `REJECTED`/`SUPERSEDED`. O agente só consome `PUBLISHED` vigente.

Nenhum crawler pode executar ação externa, preencher formulário, iniciar solicitação, aceitar termos ou tomar decisão jurídica. A coleta é leitura; a decisão continua com o escrevente.

## 5. Painel de dados do Agent AI

O painel deve usar uma visão analítica separada, sem CPF, telefone, e-mail, mensagem, documento, identificador de conversa ou payload de webhook. Métricas iniciais:

- **Fontes:** idade da captura, hash, vigência, status de revisão e divergências.
- **Preços:** consultas por ato, itens publicados, encaminhamentos HITL e catálogo vencido.
- **Atendimento:** volume por canal/intenção, taxa de handoff, SLA e erros por categoria.
- **Confiabilidade:** eventos deduplicados, DLQ, latência e cobertura de dados.

A visão deve aplicar mínimo de grupo para evitar reidentificação e obedecer às políticas RLS. Logs, payloads e documentos ficam no domínio operacional, não no painel.

## 6. Backlog priorizado

| Ordem | Entrega | Critério de aceite |
| --- | --- | --- |
| 1 | Criar `external_sources` e `source_captures` versionadas | URL, hash, vigência, parser, status e responsável; sem conteúdo pessoal |
| 2 | Consolidar coleta TJMG já existente | execução agendada, diff de versão e bloqueio de publicação sem revisão humana |
| 3 | Conector Justiça Aberta por exportação | somente dados públicos, fonte/termos registrados e carga idempotente |
| 4 | Monitor DJe/TJMG de temas controlados | baixa frequência, hash/deduplicação, fila de revisão e sem scraping amplo |
| 5 | Criar visão agregada do painel | RLS testada, nenhum campo PII e testes contra vazamento |
| 6 | Validar o runtime Hermes, se ele for necessário | evidência de processo/serviço, rota de canal e resposta real fim a fim |

## 7. Referências operacionais internas

- `backend/app/models/` — contratos do núcleo FastAPI.
- `backend/alembic/` e `infra/supabase/schema.sql` — evolução e inventário físico do Postgres.
- `backend/app/services/emolumento_fonte_tjmg.py` e `scripts/coletar_tabela_tjmg.py` — padrão atual de coleta oficial de preços.
- `docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md` — catálogo de preços e regras do painel.

