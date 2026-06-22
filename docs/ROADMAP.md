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

## Fase 1 — MVP WhatsApp (Semana 3-6)

### Sprint 1 (sem 3-4)
- [ ] Workflow n8n #1: msg WhatsApp → Evolution → OpenClaw → API regras → resposta
- [ ] Endpoint `POST /api/v1/webhook/evolution` recebe e responde
- [ ] Endpoint `GET /api/v1/protocolo/{numero}` consulta status
- [ ] Endpoint `GET /api/v1/emolumento/calcular` (ja existe, falta polish)
- [ ] LLM via LiteLLM (Claude Opus 4.5 primary, GPT-5.5 fallback)
- [ ] PII scrubbing antes de chamar LLM
- [ ] **Shadow mode**: bot sugere, humano faz, 30 dias de comparacao

### Sprint 2 (sem 5-6)
- [ ] Endpoint `POST /api/v1/protocolo` cria protocolo a partir de conversa
- [ ] Endpoint `POST /api/v1/cliente` (consentimento LGPD obrigatorio)
- [ ] Upload de documento (Supabase Storage) com hash SHA256
- [ ] Notificacao proativa: "seu protocolo #X avancou pra em_andamento"
- [ ] Dashboard basico pro escrevente (React admin)

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
