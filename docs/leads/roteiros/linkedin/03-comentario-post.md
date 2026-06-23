# LinkedIn — Comentário em Post (estratégia conteúdo-first)

**Canal**: LinkedIn — comentários em posts do tabelião
**Quando usar**: tabelião publicou post recente (últimas 2 semanas) sobre tema relevante (cartório, atendimento, digitalização, ANOREG, etc.)
**Quem comenta**: Gustavo Almeida (perfil pessoal)
**Base legal LGPD**: art. 7º I (consentimento tácito por post público) + art. 9º
**Compliance**: post é público, comentário é público, sem coleta de dado pessoal
**Data do roteiro**: 23/06/2026

---

## Filosofia do "comentário em post"

Diferente das outras duas abordagens (nota de conexão e DM), o **comentário em post** é:

- **Não-solicitado comercialmente** — você comenta o conteúdo, não o tabelião PF.
- **Construção de presença** — antes de pitch, demonstrar que você entende o setor.
- **Discreto** — sem link na primeira intervenção; oferecer DM só se o tabelião responder.
- **Público** — outros seguidores veem, viraliza expertise, posiciona a marca.

> **Regra de ouro**: o primeiro comentário NUNCA vende nada. Comenta o post, adiciona 1 ideia útil, oferece-se pra continuar a conversa em DM **se** o tabelião responder.

---

## Placeholders

| Campo | Descrição |
|-------|-----------|
| `{{AUTOR_POST}}` | Primeiro nome do autor do post |
| `{{TEMA_POST}}` | Tema do post (resumo em 5 palavras) |
| `{{IDEIA_UTIL}}` | 1 insight prático que adiciona ao post (genérico, sem pitch) |
| `{{CTA_DM}}` | (Opcional) Pergunta se quer trocar ideia em DM |

---

## Comentário template (1ª intervenção — sem pitch)

```
{{AUTOR_POST}}, {{IDEIA_UTIL}}.

A gente tá vendo isso de perto com cartórios que já operam chatbot no
atendimento inicial: o ganho real não é substituir o escrevente, é
liberar ele pro que importa (ato jurídico complexo). {{CTA_DM}}
```

**Variação mais curta** (para posts mais curtos):

```
{{AUTOR_POST}}, {{IDEIA_UTIL}}. Faz sentido?
```

**Variação com pergunta aberta** (gera conversa):

```
{{AUTOR_POST}}, {{IDEIA_UTIL}}. {{CTA_DM}}
```

---

## Exemplos de {{IDEIA_UTIL}} por tema

| Tema do post | Ideia útil (sugestão) |
|--------------|----------------------|
| "Atendimento rápido no cartório" | "O gargalo real é triagem — 70% das mensagens são dúvidas simples (emolumento, prazo, doc) que um bot resolve em 2min" |
| "Digitalização do cartório" | "A primeira onda de digitalização foi do papel. A próxima é do atendimento — WhatsApp virou balcão" |
| "ANOREG ranking 2025" | "Cartórios no top 10 tem algo em comum: WhatsApp Business ativo. Sinal de abertura pra próxima onda (IA conversacional)" |
| "Contratação de escrevente" | "Bot não substitui escrevente — tira dele 60% do atendimento repetitivo pra ele focar em escritura/procuração" |
| "Segurança da informação" | "LGPD compliance vira diferencial competitivo: cliente confia mais em cartório que mostra política de privacidade clara" |
| "PIX no cartório" | "PIX resolveu o pagamento. Falta resolver o atendimento — que continua no balcão ou telefone" |

---

## Por que essa estrutura cumpre LGPD

| Requisito | Atendimento |
|-----------|-------------|
| **Consentimento** (art. 7º I) | Post público = espaço público; comentário é contribuição |
| **Finalidade** (art. 9º) | Discussão técnica sobre o setor, não prospecção PF |
| **Sem dado pessoal** | Nenhum dado é coletado do autor |
| **Opt-out natural** | Tabelião pode ocultar / bloquear / deletar comentário |

---

## Limites operacionais

| Item | Limite |
|------|--------|
| Comentários por dia | máx. 5 (qualidade > quantidade) |
| Comentários por post do mesmo autor | 1 (não monopolize a thread) |
| Tempo de espera por resposta | 7 dias úteis → encerrar |
| Pitch de venda | **NUNCA no 1º comentário**. Só depois de 2+ interações se o autor puxar assunto |

---

## Checklist CEO (5 critérios)

- [x] **Sinal específico**: o post do tabelião É o sinal específico (tema dele, não template)
- [x] **LGPD-safe**: zero dado PF, opt-out por ignore/bloqueio, base legal declarada
- [x] **CTA claro**: NÃO usa CTA de venda no 1º comentário — usa pergunta aberta ou "faz sentido?"
- [x] **Tom PT-BR natural**: "a gente", "tá", "pra" — zero juridiquês
- [x] **Piloto 30d**: NÃO mencionado (canal não é de venda; é de conteúdo)

## Bloqueios lexicais verificados

Nenhuma ocorrência de: Vossa Senhoria / venho por meio desta / solicito / informamos que / coloco-me à disposição / aguardo retorno / atenciosamente.

---

## Próximo passo (após resposta do tabelião)

| Resposta | Ação |
|----------|------|
| **Tabelião responde com curiosidade** | Mandar DM com `02-mensagem-pos-aceite.md` (adapta o pitch pra conversa pós-comentário) |
| **Tabelião responde com indiferença** | Não insistir. Agradecer e seguir. |
| **Tabelião pede pra parar** | Marcar opt-out. Não enviar mais nada por nenhum canal. |
| **Outros profissionais comentam** | Responder também (vira thread de discussão setorial) |

---

**Modified by Gustavo Almeida**