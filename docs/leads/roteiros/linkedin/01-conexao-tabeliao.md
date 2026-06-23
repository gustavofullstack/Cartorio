# LinkedIn — Solicitação de Conexão (Tabelião)

**Canal**: LinkedIn — aba "Conexões" do tabelião
**Tier alvo**: A — Líderes Nacionais (perfil com LinkedIn pessoal/institucional ativo)
**Quem envia**: Gustavo Almeida (perfil pessoal — não use perfil institucional nesta fase)
**Base legal LGPD**: art. 7º I (consentimento) + art. 9º (informação clara) + art. 18 IX (opt-out)
**Compliance**: o tabelião pode recusar/ignorar a conexão sem custo. Não é mensagem em massa.
**Data do roteiro**: 23/06/2026

---

## Placeholders

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `{{NOME_TABELIAO}}` | Nome do tabelião (público, do site/LinkedIn) | "Dra. Maria" ou "Dr. João" |
| `{{NOME_CARTORIO}}` | Nome do cartório (público) | "5º Ofício de Notas de BH (Cartório Amaral)" |
| `{{SINAL_ESPECIFICO}}` | 1 sinal concreto do perfil (post recente, prêmio, expansão) | "Vi seu post sobre IA em cartórios" |

---

## Copy pronta pra envio (nota de conexão — limite 300 chars do LinkedIn)

```
{{NOME_TABELIAO}}, tudo bem? Sou Gustavo Almeida, fundador da 2 Notas Udi
(chatbot pra cartórios de notas). {{SINAL_ESPECIFICO}}. Adoraria trocar
uma ideia sobre como IA conversacional pode escalar atendimento sem
perder o toque humano do escrevente. Posso mandar 1 case de 15min?
```

**Limite de caracteres**: 300 (LinkedIn não permite mais na nota de conexão).
**Contagem atual**: ~270 caracteres (deixa folga para personalização).

---

## Por que essa estrutura cumpre LGPD

| Requisito | Atendimento |
|-----------|-------------|
| **Consentimento** (art. 7º I) | Conexão voluntária — tabelião aceita se quiser |
| **Informação clara** (art. 9º) | Identificação (nome, empresa) + finalidade (case de 15min) |
| **Opt-out** (art. 18 IX) | Basta recusar/ignorar a conexão — sem mensagem adicional |
| **Dado público** | Nome do tabelião vem de site/LinkedIn institucional |
| **Sem dado sensível** | Não menciona CPF, valor, ato específico |

---

## Regras operacionais LinkedIn

| Item | Limite |
|------|--------|
| Solicitações de conexão por dia | máx. 20 (LinkedIn restringe convites não respondidos) |
| Follow-up após aceite | 1 mensagem única (ver `02-mensagem-pos-aceite.md`) |
| Tempo de espera por aceite | 14 dias úteis → encerrar |
| Mensagens de vendas diretas (InMail) | proibidas (só após conexão aceita) |

---

## Checklist CEO (5 critérios)

- [x] **Sinal específico**: placeholder `{{SINAL_ESPECIFICO}}` (preencher com post/prêmio recente do tabelião)
- [x] **LGPD-safe**: zero dado PF, opt-out por recusa de conexão, base legal declarada
- [x] **CTA claro**: "1 case de 15min" — leve, não "reunião de demo"
- [x] **Tom PT-BR natural**: "tudo bem?", "adoraria trocar uma ideia", "posso mandar" — zero juridiquês
- [x] **Piloto 30d**: NÃO mencionado na nota de conexão (limite de 300 chars). Será mencionado na mensagem pós-aceite (próximo arquivo).

## Bloqueios lexicais verificados

Nenhuma ocorrência de: Vossa Senhoria / venho por meio desta / solicito / informamos que / coloco-me à disposição / aguardo retorno / atenciosamente.

## Limites LinkedIn verificados

- ≤ 300 caracteres ✓
- Sem link (LinkedIn filtra nota com URL)
- Sem emoji em excesso (1-2 máx)
- Sem menção a "vagas" ou "promoção"

---

## Próximo passo

Após o tabelião aceitar a conexão:

- Enviar `02-mensagem-pos-aceite.md` em até 48h.
- Se não aceitar em 14 dias: remover do pipeline ativo. Tentar de novo só se houver nova manifestação pública (post, entrevista, evento).

---

**Modified by Gustavo Almeida**