# Roadmap Cartorio Chatbot - 12 semanas

Premissa: cartorio medio brasileiro, ~200-300 atendimentos/dia, 1-3 tabelioes, equipe de 4-8 escreventes. Estado: MG (carga de tabela oficial).

## Fase 0 — Foundation (Semana 1-2) [STATUS: em andamento]

- [x] Stack implantada no Easypanel: OpenClaw + n8n + Evolution + Supabase
- [x] Repo backend skeleton (este repo)
- [x] 5 modelos de dados core + audit log hash chain
- [x] PII scrubbing + calculo emolumento
- [ ] Supabase schema completo (rodar migrations Alembic)
- [ ] DNS + HTTPS (cartorio.com.br → Caddy/Traefik)
- [ ] Backup automatizado Postgres (snapshot diario, retencao 30d)

## Fase 1 — MVP WhatsApp (Semana 3-8) — CORTE ESTRATEGICO CEO

> **Decisão D3.1 (ceo-assistant)**: Sprint 1 faz SÓ consulta de emolumento.
> Status protocolo Sprint 2. Criar protocolo só DEPOIS de 30 dias de shadow mode validado.
> Motivo: ship rapido + validar com escreventes reais antes de bot ganhar write access.

### Sprint 1 (sem 3-4) — SÓ CONSULTA EMOLUMENTO
- [ ] Workflow n8n #1: msg WhatsApp → Evolution → OpenClaw → API regras → resposta
- [ ] Endpoint `GET /api/v1/emolumento/calcular` (ja existe, polish + deploy)
- [ ] LLM via LiteLLM (Claude Opus 4.5 primary, GPT-5.5 fallback, Gemini/Llama como router de intencao barato)
- [ ] PII scrubbing regex-only (latencia <5ms) ANTES de chamar LLM
- [ ] Resposta template: "emolumento X custa R$ Y, prazo Z"
- [ ] **KPI Sprint 1**: 100 consultas/dia, 0 erro de valor, 0 handoff humano

### Sprint 2 (sem 5-6) — STATUS PROTOCOLO + SHADOW MODE
- [ ] Endpoint `GET /api/v1/protocolo/{numero}` consulta status
- [ ] **Shadow mode**: bot sugere resposta, escrevente envia, comparacao automatica
- [ ] HITL escalonado nivel 1 (read_only bot responde sozinho com confidence >= 0.85)
- [ ] Dashboard escrevente mostra: msg recebida, intencao detectada, resposta sugerida, quem enviou
- [ ] **KPI Sprint 2**: 95% das sugestoes aceitas sem edicao

### Sprint 3 (sem 7-8) — CRIAR PROTOCOLO (so pos 30d shadow)
- [ ] Endpoint `POST /api/v1/protocolo` cria via conversa (HITL nivel 2 - create_draft)
- [ ] Endpoint `POST /api/v1/cliente` (consentimento LGPD obrigatorio)
- [ ] Upload de documento (Supabase Storage) com hash SHA256
- [ ] Notificacao proativa: "seu protocolo #X avancou pra em_andamento"
- [ ] Dashboard basico pro escrevente (React admin)
- [ ] **KPI Sprint 3**: 50% dos protocolos novos criados via bot (restante via balcao)

## Fase 2 — Compliance + Hardening (Semana 7-8)

- [ ] RIPD (Relatorio de Impacto a Protecao de Dados Pessoais)
- [ ] DPO designado e contato publicado
- [ ] Politica de privacidade + termo de consentimento no chat
- [ ] Direito ao esquecimento (endpoint DELETE /cliente/{id} + cascade)
- [ ] Retencao automatica (job diario apaga conversas >365d)
- [ ] Logs de acesso (LGPD art. 37)
- [ ] Pen-test basico (Burp Suite + OWASP top 10)
- [ ] Rate limiting (60 req/min/IP)
- [ ] WAF Cloudflare

## Fase 3 — Multi-canal + Escala (Semana 9-10)

- [ ] Telegram bot (mesma API, gateway OpenClaw)
- [ ] Web widget no site do cartorio
- [ ] Email integration (Resend ou SES) — confirmacoes, PDFs assinados
- [ ] LiteLLM gateway em HA (2 replicas, fallback automatico)
- [ ] LLM local Llama 3.1 8B para PII scrubbing (zero dado vai pra API publica)
- [ ] Cache Redis para tabela de emolumentos (atualizacao diaria)

## Fase 4 — Premium + Assinatura Digital (Semana 11-12)

- [ ] Integracao gov.br/ICP-Brasil para assinatura digital
- [ ] Geracao de PDF final com carimbo de tempo
- [ ] Validacao humana obrigatoria antes de aplicar isencao
- [ ] Relatorio mensal de auditoria (gerado automaticamente)
- [ ] SLA dashboards (tempo medio, fila, gargalos)
- [ ] Documentacao de operacao para o cartorio (runbook)

## Pos-12 semanas — Roadmap futuro

- Q3 2026: integracao com sistema estadual (CARTIS MG, e-Cartorio SP, etc)
- Q3 2026: app mobile nativo (React Native) com biometria
- Q4 2026: multi-cartorio (white label, replicacao)
- Q1 2027: BI dashboard executivo (Looker/Metabase)
- Q2 2027: integracao com Juizado Especial Federal (procurações)

## Riscos identificados

| Risco | Mitigacao |
|-------|-----------|
| Hallucination LLM em valor juridico | Human-in-the-loop obrigatorio em toda decisao final |
| LGPD: vazamento de CPF | PII scrubbing em 3 camadas (input, log, LLM) |
| Disponibilidade WhatsApp | Multi-canal (Telegram, Web) como fallback |
| Ataque a audit log | HMAC + hash chain + verificacao automatica diaria |
| Cartorio pequeno: resistencia a mudança | Treinamento, runbook, dashboard simples |

Modified by Gustavo Almeida
