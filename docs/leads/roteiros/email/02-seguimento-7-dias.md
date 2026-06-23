# E-mail — Follow-up 7 dias (sem resposta)

**Canal**: Mesmo e-mail institucional da primeira mensagem
**Quando enviar**: 7 dias úteis após o e-mail 01-institucional-tier-a.md, **somente se não houve resposta**
**Quem envia**: Gustavo Almeida — contato@2notasudi.com.br
**Base legal LGPD**: art. 7º I + art. 18 IX (opt-out facilitado)
**Compliance**: continuação do consentimento implícito da msg 1; sem novo dado coletado
**Data do roteiro**: 23/06/2026

---

## Placeholders (mesmos do e-mail 01)

| Campo | Descrição |
|-------|-----------|
| `{{NOME_CARTORIO}}` | Nome oficial completo |
| `{{SINAL_ESPECIFICO}}` | Mesmo sinal do e-mail 01 |
| `{{CTA_HORARIO}}` | 2 novas opções (pular 1 dia à frente) |

---

## E-mail pronto pra envio

### Assunto

```
Re: Chatbot WhatsApp para cartórios — 30 dias grátis
```

### Corpo

```
Oi, equipe do {{NOME_CARTORIO}}.

Mandei um e-mail na semana passada sobre chatbot de WhatsApp
pro {{NOME_CARTORIO}} e imagino que a caixa de entrada esteja
pesada — acontece.

Resumo rápido do que proponho: 30 dias grátis, sem custo, sem
compromisso. A gente implanta, vocês testam com seus clientes
reais, e no final decide se fica. Se não ficar, a gente
desinstala e fim.

Lembro o sinal que me chamou atenção: {{SINAL_ESPECIFICO}}.
Faz sentido que o próximo salto seja automatizar o atendimento
inicial sem perder o escrevente humano.

Posso mostrar em 15min {{CTA_HORARIO}}? Responde com o melhor
horário ou propõe outra opção.

Se este contato não for oportuno, basta responder "SAIR" e eu
paro de mandar mensagem. Sem custo.

Mensagem em conformidade com a LGPD (Lei 13.709/2018).

Gustavo Almeida
Fundador — 2 Notas Udi
contato@2notasudi.com.br
✉️ DPO: dpo@2notasudi.com.br
```

---

## Regras LGPD do follow-up

| Aspecto | Tratamento |
|---------|-----------|
| **Base legal** | Continuidade do consentimento implícito (LGPD art. 7º I) — o destinatário pode revogar a qualquer momento com "SAIR" |
| **Dado novo coletado** | Nenhum — apenas reitera msg anterior |
| **Opt-out** | Reforçado no rodapé com palavra-chave idêntica |
| **Registro** | Marcar `data_followup_1`, manter `opt_out` como null (ainda não decidido) |
| **Intervalo mínimo** | 7 dias úteis após msg 1 — não encurtar |

---

## Checklist CEO (5 critérios)

- [x] **Sinal específico**: placeholder `{{SINAL_ESPECIFICO}}` (mesmo do e-mail 01, repetido pra refrescar memória)
- [x] **LGPD-safe**: opt-out "SAIR" mantido, base legal declarada, sem dado PF novo
- [x] **CTA claro**: 15min + 2 opções concretas + dia útil + horário comercial
- [x] **Tom PT-BR natural**: "Oi", "acontece", "a gente" — sem juridiquês
- [x] **Piloto 30d**: parágrafo dedicado reforçando "sem custo, sem compromisso"

## Bloqueios lexicais verificados

Nenhuma ocorrência de: Vossa Senhoria / venho por meio desta / solicito / informamos que / coloco-me à disposição / aguardo retorno / atenciosamente.

---

## Próximo passo (se ainda sem resposta)

Após este follow-up, esperar mais 7 dias úteis. Se continuar sem resposta:

- Encerrar o ciclo naquele canal (e-mail).
- Tentar o **próximo canal** (LinkedIn do tabelião ou WhatsApp Business) usando os templates correspondentes nesta pasta.
- Marcar `status_final = sem_resposta` no CRM.

---

**Modified by Gustavo Almeida**