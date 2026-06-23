---
description: 15 cláusulas obrigatórias para DPA (Data Processing Agreement) com sub-processors LGPD + 3 templates (DeepSeek/OpenCode-Go/Evolution) já criados em docs/lgpd/ + adaptações cross-project (US/EU/BR/CN). Carrega quando revisar assinatura DPA, draft contrato com operador, ou configurar novo sub-processor.
---

# DPA templates — 15 cláusulas obrigatórias

## Contexto

Sprint 3 (2026-06-23): cartorio-lgpd criou 3 templates DPA em `docs/lgpd/dpa_*_template.md` cobrindo os 3 sub-processors ativos do Cartorio. Pendente: assinatura jurídica externa (esforço total 1-2 meses do kickoff à assinatura).

## As 15 cláusulas obrigatórias

Modelo: ANPD + Resolução CD/ANPD nº 4/2023 + IAPP.

1. **Identificação das partes** — controlador + operador + DPOs
2. **Objeto e finalidade** — VEDAÇÃO EXPRESSA a treinamento, compartilhamento não autorizado, finalidade própria
3. **Base legal (LGPD art. 7)** + **transferência internacional (LGPD art. 33)** — incisos específicos + mecanismo: SCC art. 33 II + consentimento específico art. 33 I
4. **Tipos de dados tratados** — PII scrubbed, dados sensíveis art. 5 II, vedações
5. **Duração e retenção** — específica por categoria + eliminação ≤30d pós-revogação
6. **8 obrigações do operador (LGPD art. 39)** — instruções documentadas, sem sub-contratação sem aprovação, segurança art. 46, **vedação treinamento**, DPO próprio, registro de operações, eliminação/devolução, observação dos princípios art. 6
7. **Confidencialidade e sigilo** — indefinido ou 5y
8. **Notificação de incidentes** — ≤24h (**MAIS restritivo que art. 48**)
9. **Sub-processadores** — lista atual, autorização prévia, responsabilidade solidária
10. **Direitos do titular (LGPD art. 18)** — operador auxilia controlador
11. **Auditoria** — anual + on-demand + certificações ISO 27001/SOC 2
12. **Devolução ou eliminação** — ≤30d + certificado + logs mantidos 5y
13. **Responsabilidade** — solidária art. 42 + limite R$ 5M seguro RC + sem limite em dolo
14. **Lei aplicável BR + foro Uberlândia + renúncia**
15. **Disposições finais** — vigência, alterações, nulidade, integração com contrato principal

## Estrutura padrão de cada template

- Cabeçalho com versão + status (**SEMPRE STAGING ONLY até assinatura**) + Bloqueio LGPD correspondente
- Seção "Cross-References" no final (linka RIPD Tratamento + consent Item + privacy Seção + AUDITORIA_BLOCKERS)
- Assinaturas com testemunhas + reconhecimento de firmas + Apostila de Haia (se跨境)
- Histórico de versões (Conventional Commits style)

## Os 3 templates criados (2026-06-23)

| Provedor | Arquivo | Tipo | Mecanismo跨境 |
|----------|---------|------|--------------|
| DeepSeek (China) | `dpa_deepseek_template.md` (11.5KB) | Completo, 15 cláusulas | art. 33 II (SCC) + I (consent) — duplo |
| OpenCode-Go (gateway) | `dpa_opencode_go_template.md` (8.5KB) | Simplificado, sem armazenamento PII | Sem跨境 própria — complementar ao sub-processor primário |
| Evolution API (BR) | `dpa_evolution_api_template.md` (9.5KB) | Médio, sem跨境, base legal art. 7 II (obrig. legal) | N/A |

### Diferenciação por tipo de sub-processor

- **跨境 (China):** DPA completo + SCC + consentimento específico + auditoria presencial + seguro R$ 5M
- **Gateway:** DPA simplificado (sem armazenamento, sem treinamento, sem跨境 própria) — complementar ao sub-processor primário
- **BR:** DPA médio — sem跨境, sem SCC, base legal pode ser art. 7 II (obrigação legal) em vez de consentimento

## Cross-project: adaptação para outros tipos de sub-processor

| Tipo | Mecanismo art. 33 | Adaptações |
|------|-------------------|------------|
| SaaS EUA | art. 33 II (SCC) + I (consent) se sem Privacy Shield equivalente | Mesma estrutura, jurisdição NY/DE |
| BR | Sem跨境 | Base legal varia (art. 7 I, II, V, VI) |
| UE | art. 33 I (adequacy) — DPA mais simples | Remover SCC, adequacy decision automática |

## Estimativa de esforço jurídico externo (Doneda/Patricia Peck)

- Parecer inicial: 8-16h
- Adaptação por provedor: 2-4h cada
- Negociação: 2-6 semanas por provedor
- **Total kickoff → assinatura: 1-2 meses**

## REGRA DE FERRO

**NUNCA começar a enviar dado real para sub-processor sem DPA assinado E armazenado em `docs/lgpd/dpa_<provider>.pdf`.** Template é ponto de partida, NAO contrato.

Aplica a QUALQUER projeto B2B SaaS com sub-processors de PII.
