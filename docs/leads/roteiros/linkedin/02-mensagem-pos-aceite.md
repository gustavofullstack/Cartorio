# LinkedIn — Mensagem Pós-Aceite (após conexão aceita)

**Canal**: LinkedIn Direct Message (DM)
**Quando enviar**: até 48h após o tabelião aceitar a conexão
**Quem envia**: Gustavo Almeida
**Base legal LGPD**: art. 7º I (consentimento implícito pela aceitação da conexão) + art. 9º + art. 18 IX
**Compliance**: DM é canal 1:1, opt-out por bloqueio/recusa
**Data do roteiro**: 23/06/2026

---

## Placeholders

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `{{NOME_TABELIAO}}` | Primeiro nome do tabelião | "Dra. Maria" |
| `{{NOME_CARTORIO}}` | Nome do cartório | "5º Ofício de Notas de BH" |
| `{{SINAL_ESPECIFICO}}` | 1 sinal concreto (post, prêmio, feature nova) | "Vi o post sobre expansão do horário" |
| `{{CTA_HORARIO}}` | 2 opções concretas (dia útil + horário) | "terça 30/06 às 10h ou quinta 02/07 às 14h" |

---

## Mensagem pronta pra envio (DM LinkedIn)

```
Oi, {{NOME_TABELIAO}}! Obrigado por aceitar a conexão.

{{SINAL_ESPECIFICO}}.

A gente automatiza 60% do atendimento inicial via WhatsApp Business + IA
conversacional, com handoff pro escrevente humano em qualquer ato
jurídico. Chatbot em PT-BR simples, integrado com e-Notariado e PIX.

A oferta: 30 dias grátis em troca de depoimento + logomarca no case.
Sem custo, sem compromisso. Implantação em 1 semana.

Posso mostrar 15min {{CTA_HORARIO}}? Responde com o melhor horário ou
propõe outro.

Se este contato não for bem-vindo, basta me avisar que paro de mandar
mensagem. Em conformidade com LGPD.

Gustavo Almeida
Fundador — 2 Notas Udi
contato@2notasudi.com.br
```

---

## Por que essa estrutura cumpre LGPD

| Requisito | Atendimento |
|-----------|-------------|
| **Consentimento renovado** (art. 7º I) | Conexão aceita = consentimento pra DM |
| **Finalidade explícita** (art. 9º II) | Demo 15min + oferta 30 dias |
| **Opt-out** (art. 18 IX) | "basta me avisar que paro" — sem custo |
| **Dado público** | Sinal do tabelião é público (post LinkedIn) |
| **Sem dado sensível** | Nada de CPF, valor, ato específico |

---

## Limites operacionais

| Item | Limite |
|------|--------|
| DMs por dia (não-conexão) | máx. 5 (LinkedIn restringe) |
| Follow-up após esta DM | máx. 1 (após 7 dias úteis) |
| Horário de envio | 09h–18h BRT (seg-sex) |
| Tempo de espera por resposta | 7 dias úteis → encerrar |

---

## Checklist CEO (5 critérios)

- [x] **Sinal específico**: placeholder `{{SINAL_ESPECIFICO}}` (mesmo da nota de conexão, reforçado)
- [x] **LGPD-safe**: opt-out claro, base legal declarada, sem dado PF
- [x] **CTA claro**: 15min + 2 opções concretas + dia útil + horário comercial
- [x] **Tom PT-BR natural**: "Oi", "a gente", "pra" — zero juridiquês
- [x] **Piloto 30d**: parágrafo dedicado com proposta concreta (30 dias + depoimento + logomarca + 1 semana implantação)

## Bloqueios lexicais verificados

Nenhuma ocorrência de: Vossa Senhoria / venho por meio desta / solicito / informamos que / coloco-me à disposição / aguardo retorno / atenciosamente.

## Se o tabelião recusar / não responder

- **Não responder em 7 dias úteis**: encerrar o ciclo naquele canal. Tentar via e-mail ou WhatsApp Business (com cuidado LGPD).
- **Recusar explicitamente** ("não tenho interesse", "SAIR"): marcar opt-out no CRM. Não enviar mais nada por nenhum canal (LGPD art. 18 IX).
- **Bloquear no LinkedIn**: registrar bloqueio e nunca mais abordar.

---

**Modified by Gustavo Almeida**