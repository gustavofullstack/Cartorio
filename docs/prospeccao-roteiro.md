# Roteiro de Prospecção LGPD-safe — Cartórios via WhatsApp

**Versão:** 1.0
**Data:** 23 de junho de 2026
**Quem envia:** Gustavo Almeida (WhatsApp pessoal)
**Quem redigiu/revisou:** Rein `cartorio-lgpd`
**Base legal:** LGPD Lei 13.709/2018, art. 7º I (consentimento) + art. 8º (especificidade) + art. 9º (informação clara)
**DPO:** dpo@2notasudi.com.br

> Este roteiro define como abordar cartórios prospect via WhatsApp **de forma LGPD-safe**. **Não é envio em massa.** É abordagem manual, individualizada, com fontes públicas e opt-out claro na primeira mensagem.

---

## 1. Princípios inegociáveis (LGPD art. 6º)

1. **Finalidade específica e declarada** — falar sobre o chatbot, oferecer demo, agendar conversa. Nada além disso.
2. **Necessidade e adequação** — usar apenas dados **públicos**: nome do tabelião, nome do cartório, telefone institucional já publicado em site/ANOREG.
3. **Transparência** — a primeira mensagem diz claramente quem está falando, por que está contatando, e como sair da lista.
4. **Consentimento específico** — só continuamos a conversa após o destinatário responder afirmativamente.
5. **Livre acesso / revogação** — opt-out em qualquer momento, sem burocracia.
6. **Não discriminação** — sem pressão, sem urgência artificial, sem ofertas agressivas.

> **Regra de ouro:** se a primeira mensagem do destinatário for "não tenho interesse", **encerramos imediatamente** e marcamos o número como opt-out permanente (LGPD art. 18 IX).

---

## 2. Fonte dos dados (apenas dados públicos)

Antes de enviar, valide que cada item veio de **fonte pública**:

- **Nome do tabelião(a):** site oficial do cartório, ANOREG Brasil, Diário Oficial, Google Maps.
- **Nome do cartório:** site oficial, ANOREG, Cadastro Nacional de Serventias (CNS) do CNJ.
- **Telefone:** site do cartório, página "Fale conosco" ou Google Meu Negócio.
- **Cidade/UF:** endereço público no CNS.

**Proibido usar:** listas compradas, dados de Facebook Leads, scraping não autorizado, dados pessoais sem consentimento anterior do titular para prospecção.

---

## 3. Limites operacionais

| Item | Limite |
|------|--------|
| Mensagens por dia (WhatsApp pessoal Gustavo) | **máx. 20** (não configurar auto-disparo) |
| Mensagens por cartório antes de opt-out | **1** (abordagem única, sem insistência) |
| Horário de envio | 09h–18h BRT (seg-sex) — nunca sábado, domingo ou feriado |
| Tempo de espera por resposta | 5 dias úteis → encerrar |
| Tentativas de follow-up após opt-out | **0** |

> **Atenção:** WhatsApp bane contas com mais de ~50 mensagens/dia para contatos que não te têm nos contatos. Abordagem manual preserva o canal e a relação.

---

## 4. Mensagem 1 — Apresentação (cold outreach, tom profissional)

> **Enviar exatamente como está abaixo, sem personalizar de forma agressiva.** Adapte apenas o nome do cartório/tabelião.

---

```
Olá, [Nome do Tabelião]. Tudo bem?

Meu nome é Gustavo Almeida, sou fundador da 2 Notas Udi — empresa
que desenvolve tecnologia para cartórios de notas. Estou entrando
em contato porque o [Nome do Cartório] figura entre os principais
cartórios de [Cidade/UF] e gostaria de saber se o(a) senhor(a)
tem 10 minutos para uma conversa rápida sobre como outros cartórios
estão usando automação para reduzir tempo de atendimento e fila
no balcão.

Posso explicar em uma mensagem o que oferecemos:

• Chatbot de WhatsApp que responde dúvidas sobre emolumentos,
  status de protocolo e agendamento 24/7, em PT-BR simples.
• Triagem automática com handoff para escrevente humano em
  qualquer ato jurídico (isenção, escritura, certidão).
• Compliance LGPD desde o desenho — PII scrubbing, audit log
  imutável, DPO designado, retenção configurável.

Se tiver interesse, posso enviar uma demo gravada de 3 minutos
e nossa Política de Privacidade:

📄 Política de Privacidade: https://2notasudi.com.br/privacidade
🎥 Demo: https://2notasudi.com.br/demo

Se este contato não for oportuno, **basta responder "SAIR"** que
retiro seu número da lista imediatamente e não envio mais nenhuma
mensagem. Sem burocracia, sem custo.

Atenciosamente,
Gustavo Almeida
Fundador, 2 Notas Udi
✉️ contato@2notasudi.com.br
✉️ DPO: dpo@2notasudi.com.br
```

---

### Por que essa estrutura cumpre LGPD art. 7º + 8º + 9º:

| Requisito LGPD | Como atendemos |
|----------------|----------------|
| **Consentimento específico** (art. 7º I, 8º) | Só continuamos se o destinatário responder afirmativamente à pergunta. |
| **Informação clara** (art. 9º) | Identificamos quem somos, o que oferecemos, com link da política. |
| **Finalidade explícita** (art. 9º II) | Conversa sobre chatbot para cartórios, agendamento de demo. |
| **Opt-out facilitado** (art. 18 IX) | Palavra-chave única ("SAIR") sem custo. |
| **Dado público** | Nome/tabelionato tirados de fonte pública. |
| **Sem dado sensível** | Não pedimos nem mencionamos CPF, RG, valor, endereço. |

---

## 5. Respostas típicas — como reagir

### 5.1. "Tenho interesse / Pode mandar a demo"

```
Ótimo! Vou enviar agora:

🎥 Demo em vídeo (3 min): https://2notasudi.com.br/demo
📄 Política de Privacidade: https://2notasudi.com.br/privacidade
📄 RIPD (Relatório de Impacto LGPD): https://2notasudi.com.br/ripd

Posso agendar uma conversa de 20 min para entender seu fluxo
atual e ver se faz sentido? Tenho disponibilidade:

• [data 1] - [horário]
• [data 2] - [horário]
• [data 3] - [horário]

Responda com o horário preferido ou "SAIR" para não receber mais.
```

> Marcar no CRM: `consentimento_prospeccao = true`, `data`, `canal=whatsapp_pessoal`.

### 5.2. "Quem é você? De onde tirou meu número?"

```
Justo. Meu nome é Gustavo Almeida, fundador da 2 Notas Udi
(empresa: https://2notasudi.com.br). Seu número é o contato
institucional do cartório publicado no site do [Nome do Cartório]
e/ou no Cadastro Nacional de Serventias do CNJ.

Se preferir não receber mais mensagens, responda "SAIR" e eu
retiro seu número imediatamente. Sem custo.

Atenciosamente,
Gustavo Almeida
```

### 5.3. "Não tenho interesse" / "SAIR" / "Para de mandar mensagem"

```
Entendido. Vou retirar seu número da lista agora.

Você não receberá mais nenhuma mensagem deste número.
Obrigado pelo retorno.

Gustavo Almeida — 2 Notas Udi
✉️ dpo@2notasudi.com.br (caso queira contatar o DPO diretamente)
```

> Marcar no CRM: `opt_out = true`, `data`, `canal=whatsapp_pessoal`. **Não enviar mais nada por nenhum canal.**

### 5.4. "Isso é golpe / spam"

```
Entendo a preocupação. Pode confirmar nossa empresa no site
https://2notasudi.com.br e nosso DPO em dpo@2notasudi.com.br.

Se preferir não receber mais nada, basta responder "SAIR" e eu
retiro imediatamente. Não envio mais nada.

Atenciosamente,
Gustavo Almeida
```

### 5.5. "Manda para meu sócio / outro tabelião"

```
Perfeito. Qual o nome e contato dele(a)? Vou enviar a mesma
mensagem padrão (com opt-out claro) só uma vez. Se ele(a) não
responder em 5 dias úteis, paro de tentar.

E para o seu número: se quiser também sair, responda "SAIR".
```

### 5.6. Mensagem silenciosa (sem resposta após 5 dias úteis)

> **NÃO enviar follow-up.** Encerrar o ciclo. Marcar `sem_resposta = true`. Tentar de novo apenas se houver **nova manifestação pública** do destinatário (post LinkedIn, entrevista, evento).

---

## 6. Registro de consentimento e opt-out

Cada interação deve ser registrada em planilha/CRM com:

| Campo | Descrição |
|-------|-----------|
| `data_envio_msg1` | ISO 8601 |
| `nome_tabeliao` | Público, do CNS/site |
| `nome_cartorio` | Público |
| `telefone` | Público, site do cartório |
| `fonte` | URL do site ou CNS |
| `consentimento` | true / false |
| `data_consentimento` | ISO 8601 (se true) |
| `opt_out` | true / false |
| `data_opt_out` | ISO 8601 (se true) |
| `status_final` | convertido / opt_out / sem_resposta / em_conversa |

> Retenção desse registro: 5 anos (LGPD art. 37 — log de operação comercial).

---

## 7. Checklist antes de enviar (rodar mentalmente em cada abordagem)

```
[ ] O nome do tabelião está em fonte PÚBLICA? (site, CNS, ANOREG)
[ ] O telefone é o institucional público, não pessoal?
[ ] A mensagem inclui identificação (nome, empresa)?
[ ] A mensagem declara a finalidade?
[ ] A mensagem tem link da Política de Privacidade?
[ ] A mensagem tem mecanismo de opt-out simples ("SAIR")?
[ ] O horário está entre 09h–18h BRT, dia útil?
[ ] Hoje ainda não enviei mais de 20 mensagens?
[ ] Este número NÃO está marcado como opt_out no CRM?
[ ] A mensagem NÃO inclui dado sensível (CPF, RG, valor, endereço)?
```

Se qualquer resposta for **NÃO**, **não envie**.

---

## 8. O que é proibido

- ❌ Mensagens automáticas em massa (Meta bane + ANPD multa).
- ❌ Usar WhatsApp pessoal para envio > 20/dia (risco de ban).
- ❌ Anexar PDF, link de checkout, áudio não solicitado na primeira mensagem.
- ❌ Pedir CPF, RG, CNPJ, dados pessoais na abordagem.
- ❌ Prometer resultado específico ("vai aumentar 30% do seu faturamento").
- ❌ Usar linguagem de urgência artificial ("última vaga", "só hoje").
- ❌ Insistir após opt-out ou "não tenho interesse" (LGPD art. 18 IX).
- ❌ Comprar listas de leads (LGPD art. 6º VIII — prevenção).
- ❌ Compartilhar a base de opt-out com terceiros.

---

## 9. Plano de resposta a reclamação

Se o destinatário reclamar formalmente (ANPD, Procon, jurídico):

1. **Confirmar recebimento** em até 24h.
2. **Remover contato** da base imediatamente (já é padrão, mas documentar).
3. **Investigar** o que causou a reclamação (origem do dado? opt-out ignorado?).
4. **Responder formalmente** em até 15 dias úteis (LGPD art. 18 §5º).
5. **Documentar** em `.harness/memory/MEMORY.md` como lição.

---

## 10. Versionamento

| Versão | Data | Mudança | Aprovado por |
|--------|------|---------|--------------|
| 1.0 | 23/06/2026 | Versão inicial do roteiro | DPO + cartorio-lgpd |

Modified by Gustavo Almeida