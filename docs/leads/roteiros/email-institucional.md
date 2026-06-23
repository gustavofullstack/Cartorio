# Roteiro E-mail Institucional — Cartórios (LGPD-safe)

**Versão:** 1.0
**Data:** 23/06/2026
**Canal:** E-mail institucional (contato@2notasudi.com.br)
**Quem envia:** Gustavo Almeida, contato@2notasudi.com.br
**Quem redigiu/revisou:** Rein `cartorio-lgpd`
**Base legal:** LGPD art. 7º I (consentimento) + art. 8º (especificidade)
**DPO:** dpo@2notasudi.com.br

> Mensagem formal, mais longa que o WhatsApp, com anexo leve (PDF opcional). Cabeçalho com identificação, opt-out no rodapé.

---

## Template — E-mail completo

### Assunto (subject)

```
[Cartórios] {SINAL_ESPECIFICO} — chatbot que reduz fila no balcão
```

> **Por que esse assunto:** menciona o sinal específico do destinatário (Jaguarao GPTW MG, Vampre R$90M/ano) + benefício tangível (fila no balcão). Aberto porque é direto. Sem clickbait.

### Corpo do e-mail

```
Assunto: [Cartórios] {SINAL_ESPECIFICO} — chatbot que reduz fila no balcão

Prezado(a) [PRIMEIRO_NOME] [SOBRENOME],

Meu nome é Gustavo Almeida, fundador da 2 Notas Udi — empresa que
desenvolve automação conversacional para cartórios de notas no Brasil.

Estou entrando em contato porque o [NOME_CARTORIO] se destaca
em [CIDADE_UF] por {SINAL_ESPECIFICO}. Esse tipo de reconhecimento
costuma vir acompanhado de pressão operacional crescente — fila no
balcão, equipe sobrecarregada, cidadãos esperando.

Por isso, gostaria de apresentar como cartórios que estão em
situação semelhante estão usando chatbot WhatsApp/Telegram/Web
para:

  • Responder 80% das dúvidas sobre emolumentos, prazos e
    documentação em até 30 segundos (24/7, em PT-BR simples).
  • Reduzir fila no balcão com triagem automática e agendamento
    online integrado.
  • Manter total conformidade LGPD — PII scrubbing em 3 camadas,
    audit log imutável com SHA-256 + HMAC, DPO designado, retenção
    configurável.

Demonstração gravada (3 min): https://2notasudi.com.br/demo
Política de Privacidade:    https://2notasudi.com.br/privacidade
RIPD (Relatório LGPD):      https://2notasudi.com.br/ripd

Se este contato for de seu interesse, posso agendar uma conversa
de 20 minutos nos próximos dias. Caso prefira não receber
nenhuma comunicação adicional, basta responder este e-mail
com o assunto "SAIR" e removo seu contato imediatamente da
nossa lista, sem burocracia.

Atenciosamente,

Gustavo Almeida
Fundador, 2 Notas Udi
contato@2notasudi.com.br

Encarregado de Dados (DPO): dpo@2notasudi.com.br
Política de Privacidade:    https://2notasudi.com.br/privacidade

— — — — — — — — — — — — — — — — — — — — — — — — — — —
Caso não deseje mais receber nossos e-mails, responda com
o assunto "SAIR" para remover seu endereço permanentemente.
Base legal: LGPD art. 7º I (consentimento) + art. 18 IX
(revogação). Não enviamos nenhum e-mail sem seu consentimento
prévio. Seus dados foram obtidos de fonte pública (site do
cartório, CNS ou ANOREG).
— — — — — — — — — — — — — — — — — — — — — — — — — — —
```

---

## Como preencher os placeholders

| Placeholder | Como obter | Fonte obrigatória |
|-------------|-----------|-------------------|
| `[PRIMEIRO_NOME]` + `[SOBRENOME]` | Nome completo do tabelião(a) | Site oficial / CNS / ANOREG |
| `[NOME_CARTORIO]` | Nome fantasia | Site oficial / CNS |
| `[CIDADE_UF]` | Cidade e unidade federativa | Endereço público do cartório |
| `{SINAL_ESPECIFICO}` | **1 sinal único por cartório** | Pesquisa do CEO-assistant |

### Exemplos reais

| Cartório | {SINAL_ESPECIFICO} |
|----------|--------------------|
| Cartório Jaguarao (MG) | ter conquistado o selo **GPTW MG 2025** |
| Cartório Vampre (SP) | ter atingido **mais de R$ 90 milhões/ano em atos lavrados** mantendo equipe enxuta |
| Cartório X | [Outro sinal público relevante] |

---

## Regras

1. **SINAL_ESPECIFICO vem SEMPRE da pesquisa do CEO-assistant** — 1 sinal único por destinatário, no máximo.
2. **Demonstração por link** — nunca anexar PDF pesado. Demo fica em HTML público.
3. **Opt-out no rodapé + no assunto alternativo** — cliente pode responder "SAIR" sem expor motivo.
4. **Identificação completa** — nome, cargo, empresa, e-mail, DPO, links de política.
5. **Sem HTML pesado** — texto puro ou HTML minimalista. Marketing agressivo = descadastramento + reputação.
6. **Assinatura curta** — apenas nome, cargo, empresa, e-mail, DPO. Sem logos ou banners.
7. **Fonte dos dados:** pública (site oficial, CNS, ANOREG). Nunca comprar lista.

---

## Resposta esperada e ação

| Resposta | Ação |
|----------|------|
| "Tenho interesse" | Responder com horários (Calendly) + pedir telefone para demo ao vivo |
| "Quem é você?" / "De onde tirou meu e-mail?" | Resposta padrão + link do site + opt-out |
| "Não tenho interesse" | Resposta breve + opt-out |
| "SAIR" no assunto | Remover do mailing + responder confirmando remoção em até 5 dias úteis |
| Sem resposta em 7 dias úteis | Encerrar ciclo. **Não enviar follow-up automático.** |

---

## Limites operacionais

| Item | Limite |
|------|--------|
| E-mails por dia (máquina contato@) | 30 (warm-up gradual) |
| Tamanho do e-mail | ≤ 8 KB |
| Follow-up automático | Proibido |
| Lista | Sem lista comprada. Apenas opt-in ou dado público explícito. |
| Retenção do registro de consentimento | 5 anos (LGPD art. 37) |

---

## Versão

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 23/06/2026 | Versão inicial | Rein `cartorio-lgpd` |

Modified by Gustavo Almeida