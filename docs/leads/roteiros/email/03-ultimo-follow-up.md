# E-mail — Último Follow-up (encerramento de ciclo)

**Canal**: Mesmo e-mail institucional da primeira mensagem
**Quando enviar**: 7 dias úteis após o follow-up 02 (total: 14 dias úteis desde msg 1), **somente se não houve resposta aos 2 primeiros**
**Quem envia**: Gustavo Almeida — contato@2notasudi.com.br
**Base legal LGPD**: art. 7º I + art. 18 IX (última tentativa antes de encerrar)
**Compliance**: tom respeitoso, sem pressão; encerramento de ciclo, não insistência
**Data do roteiro**: 23/06/2026

---

## Filosofia do "último follow-up"

Esta é a **terceira e última** mensagem. O objetivo é:

1. **Fechar o ciclo** com dignidade — não insistência.
2. **Deixar a porta aberta** — o destinatário pode voltar quando quiser.
3. **Confirmar opt-out por inércia** — se não responder, registramos `sem_resposta` e paramos de mandar mensagens naquele canal.
4. **Não queimar a relação** — tabelião pode mudar de ideia em 3, 6, 12 meses. Tratar como "longo prazo", não "agora ou nunca".

> **Atenção LGPD**: nenhuma linguagem de urgência artificial. Sem "última chance", sem "só hoje", sem "vagas limitadas".

---

## Placeholders

| Campo | Descrição |
|-------|-----------|
| `{{NOME_CARTORIO}}` | Nome oficial completo |
| `{{CTA_HORARIO}}` | 2 opções concretas (1 semana à frente) |

---

## E-mail pronto pra envio

### Assunto

```
Re: Chatbot WhatsApp para cartórios — último contato
```

### Corpo

```
Oi, equipe do {{NOME_CARTORIO}}.

Esse é meu último e-mail sobre o chatbot. Não quero atrapalhar
a rotina de vocês — vou parar de mandar mensagem por aqui.

Fico à disposição se um dia fizer sentido conversar. A oferta
dos 30 dias grátis continua de pé enquanto estivermos operando.

Se quiser retomar o contato no futuro, é só responder este
e-mail ou mandar mensagem pra contato@2notasudi.com.br.

E se este contato não for bem-vindo, basta responder "SAIR"
que eu retiro seu endereço da lista imediatamente. Sem custo.

Obrigado pelo tempo.

Mensagem em conformidade com a LGPD (Lei 13.709/2018).

Gustavo Almeida
Fundador — 2 Notas Udi
contato@2notasudi.com.br
✉️ DPO: dpo@2notasudi.com.br
```

---

## Por que NÃO usar "última chance" / "só hoje"

| Linguagem proibida | Por que |
|--------------------|---------|
| "Última chance" | Pressão abusiva (LGPD art. 6º VI — não discriminação, art. 37 — boa-fé) |
| "Só hoje" / "Vagas limitadas" | Urgência artificial = prática comercial agressiva (CDC art. 36 + LGPD art. 6º) |
| "Não perca" | Idem |
| "Garanta já" | Idem |
| Qualquer gatilho de escassez falso | Idem |

**Tom usado aqui**: encerramento respeitoso, sem artifício. A oferta de 30 dias é mantida, mas como disponibilidade contínua, não como urgência.

---

## Checklist CEO (5 critérios)

- [x] **Sinal específico**: NÃO aplicável (último follow-up é institucional-genérico, não precisa de novo sinal)
- [x] **LGPD-safe**: opt-out "SAIR", tom respeitoso, sem pressão, base legal declarada
- [x] **CTA claro**: NÃO usa CTA de agendamento — é encerramento. Convite a voltar no futuro, sem urgência
- [x] **Tom PT-BR natural**: "esse é meu último e-mail", "fico à disposição", "obrigado pelo tempo"
- [x] **Piloto 30d**: reitera oferta de 30 dias grátis (disponibilidade contínua, sem prazo artificial)

## Bloqueios lexicais verificados

Nenhuma ocorrência de: Vossa Senhoria / venho por meio desta / solicito / informamos que / coloco-me à disposição / aguardo retorno / atenciosamente.

## Linguagem de urgência verificada

Nenhuma ocorrência de: última chance / só hoje / vagas limitadas / não perca / garanta já / escassez.

---

## Encerramento do ciclo (após este e-mail)

Marcar no CRM:

| Campo | Valor |
|-------|-------|
| `data_followup_2` | ISO 8601 |
| `status_final` | `sem_resposta` |
| `data_encerramento_ciclo` | ISO 8601 |
| `proxima_acao_permitida` | Apenas se houver **nova manifestação pública** do destinatário (post LinkedIn, entrevista, evento do setor). Sem nova prospecção ativa por 12 meses. |

---

**Modified by Gustavo Almeida**