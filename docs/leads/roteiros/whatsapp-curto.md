# Roteiro WhatsApp Curto — Cartórios (LGPD-safe)

**Versão:** 1.0
**Data:** 23/06/2026
**Canal:** WhatsApp pessoal do Gustavo
**Quem dispara:** Gustavo Almeida
**Quem redigiu/revisou:** Rein `cartorio-lgpd`
**Base legal:** LGPD art. 7º I (consentimento) + art. 8º (especificidade)
**DPO:** dpo@2notasudi.com.br

> Mensagem curta (≤ 500 caracteres), tom direto, opt-out na primeira linha. Máximo 1 envio por cartório.

---

## Template

```
Olá, [PRIMEIRO_NOME] do [NOME_CARTORIO] — {SINAL_ESPECIFICO}.

Sou Gustavo Almeida, fundador da 2 Notas Udi (cartórios).
Quero te mostrar como [BENEFICIO_ESPECIFICO_RELACIONADO_AO_SINAL] em outros cartórios.

Demo 3 min: https://2notasudi.com.br/demo
Política de privacidade: https://2notasudi.com.br/privacidade

Não é spam. Resposta "SAIR" remove seu número da lista sem custo.

— Gustavo
✉️ dpo@2notasudi.com.br (DPO)
```

---

## Como preencher os placeholders

| Placeholder | Como obter | Fonte obrigatória |
|-------------|-----------|-------------------|
| `[PRIMEIRO_NOME]` | Nome do tabelião(a) | Site oficial do cartório / CNS / ANOREG |
| `[NOME_CARTORIO]` | Nome fantasia do cartório | Site oficial / CNS |
| `{SINAL_ESPECIFICO}` | **1 sinal único por cartório** | Pesquisa do CEO-assistant |
| `[BENEFICIO_ESPECIFICO_RELACIONADO_AO_SINAL]` | Benefício direto do sinal | Inferido do sinal |

### Exemplos reais de sinais (do CEO-assistant)

| Cartório | {SINAL_ESPECIFICO} | [BENEFICIO_ESPECIFICO_RELACIONADO_AO_SINAL] |
|----------|--------------------|----------------------------------------------|
| Cartório Jaguarao (MG) | Reconhecido como GPTW MG 2025 | Conquistou selo GPTW automatizando 80% das dúvidas de emolumento |
| Cartório Vampre (SP) | Mais de R$ 90M/ano em atos lavrados | Mantém SLA em dia mesmo com time enxuto usando triagem automática |
| Cartório X (geral) | [Outro sinal relevante] | [Benefício correspondente] |

---

## Regras

1. **SINAL_ESPECIFICO vem SEMPRE da pesquisa do CEO-assistant** (Jaguarao=GPTW MG, Vampre=>R$90M/ano, etc.).
2. **Nunca usar 2 sinais** na mesma mensagem — perde foco.
3. **Demonstração por link** — nunca enviar PDF ou áudio não solicitado na primeira mensagem.
4. **Opt-out sempre na mesma tela** — "SAIR" como palavra única, sem custo.
5. **Horário:** 09h–18h BRT, segunda a sexta.
6. **Limite:** 20 mensagens/dia, 1 por cartório, sem insistência.
7. **Fonte dos dados:** pública (site, CNS, ANOREG). Nada comprado, nada de scraping.

---

## Resposta esperada e ação

| Resposta | Ação |
|----------|------|
| "Interessado" / "manda demo" | Responder com horários de reunião (ver `email-institucional.md`) |
| "SAIR" / "não tenho interesse" | Resposta padrão de opt-out + marcar no CRM |
| "Quem é você?" | Resposta com identificação + link do site |
| Sem resposta em 5 dias úteis | Encerrar ciclo, marcar `sem_resposta=true` |

---

## Versão

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 23/06/2026 | Versão inicial | Rein `cartorio-lgpd` |

Modified by Gustavo Almeida