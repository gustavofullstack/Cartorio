# GOALS.md - Objetivos do OpenClaw Agent (CartórioBot)

Objetivos mensuraveis e prazo claro. Diferente de SOUL.md (identidade/
comportamento) e IDENTITY.md (persona/tecnico), GOALS.md define as METAS
que orientam decisoes de produto.

## Visao de 6 meses (Ja documentada em SOUL.md)

> Ser o principal ponto de entrada do cartorio 24/7: cliente manda
> mensagem as 22h, eu qualifico, calculo, agendo, e quando o Gustavo
> abre o escritorio as 09h, a agenda ja esta pronta e os clientes sabem
> o que trazer.

## Metas quantificaveis

### Meta 1 - Adocao (Cobertura de atendimento)

- **Target**: 80% das conversas inbound via WhatsApp resolvidas pelo bot sem handoff humano
- **Baseline hoje**: ~40% (handoff em quase toda duvida juridica)
- **Prazo**: Sprint 6 (90 dias)
- **Metrica de medicao**: `conversas_total - handoff_count` / `conversas_total`
- **Query Prometheus**: `rate(conversas_resolvidas_bot_total[30d]) / rate(conversas_total[30d])`

### Meta 2 - Tempo de resposta

- **Target**: P95 < 3s para resposta do bot (sem LLM call)
- **Target**: P95 < 8s para resposta do bot (com LLM call)
- **Baseline hoje**: varia muito (depende do OpenCode-Go)
- **Prazo**: Sprint 4 (60 dias)
- **Metrica**: latencia webhook Evolution → bot_response
- **Query Prometheus**: `histogram_quantile(0.95, rate(bot_response_latency_seconds_bucket[5m]))`

### Meta 3 - LGPD compliance

- **Target**: 100% das mensagens com PII detectado ANTES de ir ao LLM
- **Target**: 0 violacoes LGPD reportadas (DPO/auditoria)
- **Baseline hoje**: 100% ja atendido (PII scrubbing 3 camadas)
- **Prazo**: continuo (NUNCA regride)
- **Metrica**: `pii_blocked_count / pii_detected_count` deve ser >= 1.0

### Meta 4 - Emolumentos corretos

- **Target**: 100% dos calculos de emolumento conferem com tabela oficial MG 2026
- **Baseline hoje**: ~95% (alguns casos de borda ainda pendentes)
- **Prazo**: Sprint 5 (75 dias)
- **Metrica**: comparacao automatica entre API e planilha oficial semanal
- **Test coverage**: tabela de emolumento >= 95% coberta por pytest

### Meta 5 - Reduzir handoff

- **Target**: handoff humano < 30% das conversas
- **Baseline hoje**: ~60% (handoff em duvida juridica, reclamacao, valor > R$ 5k)
- **Prazo**: Sprint 6 (90 dias)
- **Metrica**: `handoff_count / conversas_total`
- **Acoes**: treinar LLM em duvidas juridicas comuns, expandir base de conhecimento

### Meta 6 - Confiabilidade

- **Target**: uptime >= 99.5% (4h downtime/mes aceitavel)
- **Baseline hoje**: ~98% (algumas quedas de OpenCode-Go + Redis)
- **Prazo**: Sprint 4 (60 dias)
- **Metrica**: health radar 7 servicos (DB, Redis, LLM, N8N, Evolution, Chatwoot, OpenClaw)
- **Alerta**: webhook Prometheus + alerta Gustavo via Telegram se uptime < 99%

## North Star Metric

**NSM = `conversas_resolvidas_sem_human_total`** — conversas onde o bot
resolveu sozinho sem precisar de escrevente. Esta eh a metrica que mais
importa para o cartorio: cada conversa resolvida pelo bot eh tempo que
o Gustavo/escrevente NAO gastou.

## Decisoes alinhadas aos goals

- Toda feature nova: perguntar "isso move alguma Meta?"
- Toda correcao: priorizar items que afetam Meta 1 (adocao) ou Meta 3 (LGPD)
- Refactor: aceitar se melhora Meta 2 (latencia) ou Meta 6 (uptime)
- LGPD nunca eh trade-off (Meta 3 eh absoluto)

## Review trimestral

A cada 90 dias, revisar:
- Status de cada meta (vermelha/amarela/verde)
- Razoes de desvio
- Ajustes de target se necessario
- Atualizar GOALS.md com proximo trimestre

Modified by Gustavo Almeida