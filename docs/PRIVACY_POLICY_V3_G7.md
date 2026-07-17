# Política de Privacidade v3 — 2º Serviço Notarial de Uberlândia

**Versão:** 3.0 (G7)  
**Status:** **RASCUNHO PUBLICÁVEL** — aguarda publicação no site (HOLD-GUSTAVO)  
**Data do rascunho:** 17 de julho de 2026  
**Controlador:** 2º Serviço Notarial de Uberlândia — Cartório 2º Ofício de Notas  
**Encarregado de Dados (DPO):** `[NOME_DO_DPO]` · **dpo@2notasudi.com.br** · `[TELEFONE_DO_DPO]`  
**URL de publicação prevista:** https://2notasudi.com.br/privacidade  
**Fonte legada:** `docs/privacy-policy.md` (v1.1) · `docs/lgpd/policy/D23-site-privacy-policy-v3.md`  

> Documento em **português**, linguagem clara (LGPD art. 9º), alinhado à
> **Lei nº 13.709/2018 (LGPD)** e ao **Provimento CNJ nº 74/2018**.  
> **Não substitui** a versão publicada no site até o checklist de publicação
> (`docs/PRIVACY_POLICY_V3_PUBLISH_CHECKLIST_G7.md`) ser executado.

---

## 1. Quem somos (controlador)

O **2º Serviço Notarial de Uberlândia** (Cartório 2º Ofício de Notas de Uberlândia)
atua como **controlador** dos dados pessoais tratados no atendimento digital e nos
sistemas internos, nos termos do art. 5º, VI, da LGPD.

| Campo | Informação |
|-------|------------|
| Nome | 2º Serviço Notarial de Uberlândia / Cartório 2º Ofício de Notas |
| CNPJ | `[PREENCHER CNPJ OFICIAL]` |
| Sede | Uberlândia/MG — `[ENDEREÇO COMPLETO]` |
| Site | https://2notasudi.com.br |
| E-mail geral | contato@2notasudi.com.br |
| DPO (Encarregado) | `[NOME_DO_DPO]` |
| E-mail DPO | **dpo@2notasudi.com.br** |
| Telefone DPO | `[TELEFONE_DO_DPO]` |
| Canal DPO web | https://2notasudi.com.br/dpo |
| Prazo de resposta | até **15 dias úteis** (LGPD art. 18 §5º) |

---

## 2. Escopo desta política

Esta política cobre o tratamento de dados pessoais no:

1. **Bot multi-canal** — WhatsApp (Evolution API), Telegram e Web (widget / LobeChat);
2. **API e sistemas internos** — FastAPI, n8n, OpenClaw, LiteLLM, Chatwoot (handoff humano);
3. **Armazenamento e segurança** — Postgres (Supabase self-hosted), Redis, audit log;
4. **Infraestrutura** — Hostinger (VPS), Cloudflare (CDN/WAF/DNS), quando aplicável.

Não cobre sites de terceiros linkados ocasionalmente (ex.: gov.br/anpd).

---

## 3. Quais dados coletamos

Coletamos apenas o **necessário** (princípios da necessidade e minimização — LGPD art. 6º):

| Categoria | Exemplos | Finalidade principal |
|-----------|----------|----------------------|
| Identificação | Nome, CPF, RG, CNH, CNPJ (quando ato exigir) | Identificar partes do ato notarial |
| Contato | Telefone (WhatsApp/Telegram), e-mail | Atendimento e notificações |
| Conteúdo da conversa | Texto, áudio transcrito, descrição de imagem | Executar o atendimento solicitado |
| Dados do ato | Tipo de ato, valor, partes, documentos | Cumprir obrigação notarial (Provimento 74/2018) |
| Metadados técnicos | IP (preferencialmente truncado), user-agent, sessão | Segurança, auditoria (art. 37), anti-fraude |
| Consentimento | Timestamp, versão da política/termo, canal, opt-in/out | Prova de consentimento e revogação |
| Conteúdo processado por IA | Pergunta/resposta **após** mascaramento de PII | Assistente virtual (somente com base legal válida) |

**Dado sensível (LGPD art. 5º, II):** o CNS (Cartão Nacional de Saúde), quando
aparecer, é tratado com cuidado reforçado e **mascarado** antes de qualquer envio
a provedores de IA.

### 3.1 O que **não** enviamos “cru” a modelos de IA

Antes de qualquer chamada a LLM externo (MiniMax, DeepSeek, OpenAI, Anthropic etc.),
aplicamos **PII scrubbing em 3 camadas** (entrada do usuário → pré-LLM → saída do
modelo). Em especial:

- **CPF, RG, CNPJ, telefone, e-mail, cartão, CNS, CNH** e números de **protocolo/escritura**
  são mascarados ou substituídos por tokens;
- **Nunca** ecoamos CPF raw de volta ao usuário em canais de bot;
- Decisões jurídicas finais **sempre** passam por **humano (HITL)** — o bot não
  emite certidão/escritura sozinho.

---

## 4. Bases legais (LGPD art. 7º e art. 11)

| Base | Quando usamos |
|------|----------------|
| **art. 7º, I — Consentimento** | Bot, comunicações opcionais, uso de IA assistida, pesquisas |
| **art. 7º, II — Obrigação legal** | Guarda de protocolos, livros, audit log, obrigações fiscais/corregedoria |
| **art. 7º, V — Execução de contrato / procedimento preliminar** | Atendimento ao serviço que você solicitou |
| **art. 7º, VI — Exercício regular de direitos** | Resposta a intimação, MP, Judiciário, corregedoria |
| **art. 7º, IX — Legítimo interesse** | Segurança, prevenção a fraude, rate limit (com teste de balanceamento) |
| **art. 11** | Dados sensíveis somente nas hipóteses legais aplicáveis |

Quando a base for **consentimento**, você pode **revogar a qualquer momento**
(art. 8º §5º), sem prejuízo da licitude do tratamento anterior nem das obrigações
legais já iniciadas (ex.: protocolo aberto).

---

## 5. Finalidades do bot multi-canal

Seus dados no WhatsApp, Telegram e Web são usados **exclusivamente** para:

1. **Atendimento** — dúvidas sobre emolumentos, andamento, agendamento e serviços notariais;
2. **Execução do serviço** — coleta de informações para o escrevente processar o ato (sempre com validação humana);
3. **Cumprimento legal** — retenção exigida pelo Provimento CNJ 74/2018 e legislação tributária;
4. **Segurança e auditoria** — registro de operações (art. 37), integridade do audit log, anti-abuso;
5. **Comunicação operacional** — confirmações, retornos e handoff para atendimento humano (Chatwoot).

**Não usamos** seus dados para: vender a terceiros; marketing agressivo sem opt-in;
treinar modelos de IA de terceiros com o seu conteúdo bruto; decisões automatizadas
com efeitos jurídicos sem revisão humana (art. 20).

---

## 6. Canais: WhatsApp, Telegram e Web

| Canal | Como tratamos | Observações |
|-------|----------------|-------------|
| **WhatsApp** | Via Evolution API (infra própria/controlada) | Dual parse de webhook; consentimento na primeira interação |
| **Telegram** | Bot oficial do cartório | `parse_mode` seguro; opt-out por comando/palavra-chave |
| **Web** | Widget / LobeChat / portal | Preferência a cookies estritamente necessários; banner de privacidade |

Em todos os canais:

- consentimento **afirmativo** (não pré-marcado) quando exigido;
- possibilidade de **“PARAR” / “SAIR” / “revogar consentimento”**;
- handoff para **escrevente humano** quando o caso exigir (HITL).

---

## 7. Compartilhamento e operadores

Compartilhamos dados **somente** quando necessário:

### 7.1 Órgãos e obrigações legais

Corregedoria de Justiça (MG), Poder Judiciário, Ministério Público, Receita Federal /
SEFAZ, ANPD — nas hipóteses legais.

### 7.2 Operadores e infraestrutura

| Destinatário | Papel | Localização típica | Observação |
|--------------|-------|--------------------|------------|
| Hostinger | VPS / hospedagem | BR (datacenter) | DPA / contrato master |
| Cloudflare | DNS, CDN, WAF | Global | Metadados de borda; DPA |
| Supabase (self-hosted) | Banco Postgres + storage | VPS do cartório | Controlado pelo cartório |
| Redis (self-hosted) | Cache, rate limit, idempotência | VPS do cartório | Sem PII desnecessário |
| Evolution API | Gateway WhatsApp | Self-hosted | DPA template BR |
| n8n | Orquestração de workflows | Self-hosted | Ferramenta do controlador |
| Chatwoot | CRM / handoff humano | Self-hosted | Atendimento humano |
| OpenClaw / LiteLLM | Roteamento de LLMs | Preferência VPS BR | Prompts **scrubbed** |
| **Provedores LLM** (abaixo) | Inferência de linguagem | Conforme DPA de cada um | **Sem CPF raw** |

### 7.3 Provedores de inteligência artificial (transferência com scrubbing)

| Provider | Uso | Status DPA (à data do rascunho) | O que recebe |
|----------|-----|----------------------------------|--------------|
| MiniMax (M2.7 / M3) | Inferência bot / ops | **READY_TO_SIGN** (pacote G7) | Apenas texto **scrubbed** |
| OpenCode-Go / DeepSeek | Inferência low-cost | Conforme matriz DPA | Scrubbed |
| OpenAI / Anthropic (via proxy) | Fallback de qualidade | Conforme matriz / DPA público | Scrubbed |
| Llama 3.1 8B local | Fallback offline / PII-sensitive | Local (sem tráfego externo) | Preferido para dados sensíveis |
| mimo / mistral-free / openrouter / gemini free | Fallback secundário | Pendente ou bloqueado se sem DPA | Nunca PII bruta |

Detalhes e status atualizados: `docs/LLM_DPA_MATRIX.md` e `docs/DPA_MINIMAX_READY_TO_SIGN_G7.md`.

**Importante:** envio a LLM em país sem adequação ANPD só ocorre com salvaguardas do
**art. 33** (cláusulas contratuais e, quando exigido, consentimento específico) **e**
sempre com mascaramento prévio.

---

## 8. Retenção

| Tipo de dado | Prazo | Após o prazo |
|--------------|-------|--------------|
| Conversa do chatbot (texto) | **365 dias** | Eliminação ou anonimização |
| Logs de interação com LLM | **90 dias** (metadados/scrubbed) | Eliminação |
| Áudio/imagem da conversa | **365 dias** | Eliminação |
| Protocolo notarial | **5 anos** após o ato | Anonimização residual |
| Documento notarial (escritura etc.) | **20+ anos** (obrigação legal) | Guarda legal |
| Audit log (sem PII desnecessário) | **5 anos** | Manutenção da cadeia |
| Registro de consentimento / revogação | Relação + **5 anos** | Prova de conformidade |
| Backups criptografados | conforme política de backup (tipicamente ≤ 30–90 dias rotativos + retenção legal se contiver ato) | Destruição segura |

Passado o prazo, aplicamos **eliminação** ou **anonimização** (art. 12 e art. 16).

---

## 9. Direitos do titular (LGPD art. 18)

Você pode, a qualquer momento:

1. **Confirmação** de que tratamos seus dados;  
2. **Acesso** aos dados;  
3. **Correção** de dados incompletos, inexatos ou desatualizados;  
4. **Anonimização, bloqueio ou eliminação** de dados desnecessários ou excessivos;  
5. **Portabilidade** em formato estruturado;  
6. **Eliminação** dos dados tratados com base no consentimento;  
7. **Informação** sobre compartilhamentos;  
8. **Informação** sobre a possibilidade de não consentir e consequências;  
9. **Revogação** do consentimento;  
10. **Oposição** a tratamento irregular;  
11. **Revisão de decisões** tomadas unicamente com base em tratamento automatizado (art. 20) — no cartório, atos jurídicos finais **sempre** têm revisão humana.

### 9.1 Oposição parcial à IA (novidade v3)

Você pode se opor **somente** ao tratamento por IA (envio de mensagens a LLMs),
mantendo o atendimento jurídico-cartorário tradicional. Peça por e-mail ao DPO ou
pelo comando/fluxo LGPD do canal (`/lgpd` quando disponível).

### 9.2 Como exercer

- E-mail: **dpo@2notasudi.com.br**  
- Web: https://2notasudi.com.br/dpo  
- Chatbot: mensagem “quero exercer meus direitos LGPD” ou fluxo `/lgpd`  
- Presencial: balcão do cartório, mediante agendamento  

**Prazo de resposta:** até **15 dias úteis**.

---

## 10. Segurança da informação (LGPD art. 46)

- Criptografia em trânsito (TLS 1.3) e em repouso no banco;  
- PII scrubbing em 3 camadas antes de LLM;  
- Audit log **append-only** com cadeia SHA-256 + HMAC;  
- Hash de identificadores quando aplicável (lookup sem texto claro indevido);  
- Rate limit e proteção contra abuso;  
- Backups criptografados;  
- Princípio do menor privilégio;  
- Human-in-the-loop em atos jurídicos.

**Incidente com risco relevante:** comunicação à **ANPD em até 72 horas** e aos
titulares **sem demora indevida** (art. 48).

---

## 11. Cookies e tecnologias similares

No site e no widget web usamos, em regra:

- **Cookies estritamente necessários** (sessão, segurança, preferência de consentimento);
- **Não** usamos cookies de publicidade, redes de anúncio ou pixels de marketing
  sem consentimento específico.

O widget LobeChat, quando ativo, é **opt-in** (clique para iniciar) e prioriza
funcionamento sem fingerprinting invasivo.

---

## 12. Crianças e adolescentes

O bot **não se destina** a crianças menores de 12 anos (art. 14). Para adolescentes
(12–18), o tratamento depende de consentimento do responsável legal quando exigido.

---

## 13. Transferência internacional (resumo)

Dados pessoais só são transferidos ao exterior com salvaguardas do **art. 33**
(adequação, cláusulas contratuais específicas, consentimento específico, etc.).
Conteúdo enviado a LLMs no exterior é **sempre scrubbed**. Matriz viva:
`docs/LLM_DPA_MATRIX.md`.

---

## 14. Encarregado de Dados (DPO)

| | |
|--|--|
| Nome | `[NOME_DO_DPO]` *(preencher antes da publicação definitiva)* |
| E-mail | dpo@2notasudi.com.br |
| Telefone | `[TELEFONE_DO_DPO]` |
| Web | https://2notasudi.com.br/dpo |

Atribuições: art. 41 §2º (reclamações de titulares, interlocução com ANPD, orientação
interna, coordenação de resposta a incidentes).

---

## 15. Como reclamar à ANPD

- Site: https://www.gov.br/anpd  
- E-mail: atendimento@anpd.gov.br  
- Telefone: 0800 979 4040  

---

## 16. Alterações desta política

Mudanças materiais serão comunicadas com antecedência razoável (banner no site,
chatbot e/ou e-mail quando formos contato). Versão vigente é a **publicada** em
https://2notasudi.com.br/privacidade.

| Versão | Data | Resumo |
|--------|------|--------|
| 1.0 | 2026-06-23 | Versão inicial |
| 1.1 | 2026-06-23 | DPO nominal (placeholders), CNS/CNH, DeepSeek/China, N8N |
| 2.0 | 2026-07-02 | Site policy D23 v2 |
| **3.0** | **2026-07-17** | **Multi-canal + LiteLLM/MiniMax/OpenClaw/LobeChat; oposição parcial à IA; retenção LLM 90d; matriz DPA; G7 Wave 27** |

---

## 17. Vigência do rascunho v3

Esta **v3.0** entra em vigor na **data de publicação no site** (não nesta data de
rascunho), após:

1. Preenchimento de placeholders (CNPJ, endereço, DPO nominal/telefone);  
2. Aprovação do DPO e do Tabelião;  
3. Execução do checklist `docs/PRIVACY_POLICY_V3_PUBLISH_CHECKLIST_G7.md`;  
4. Atualização do hash/versão no banner de consentimento do bot.

Até lá, a política **publicada** vigente permanece a última versão no site
(referência documental interna: v1.1 em `docs/privacy-policy.md` e materiais D23).

---

## 18. Aprovação (em branco — sem assinatura simulada)

```
DPO: ___________________________ Data: ___/___/______
Tabelião(a): ___________________ Data: ___/___/______
Comitê / compliance (se houver): _____________________
```

**Base legal consultada:** LGPD (Lei 13.709/2018); Provimento CNJ 74/2018;
Resoluções ANPD; boas práticas de privacy by design.

---

**Modified by Gustavo Almeida + cartorio-lgpd — G7 Wave 27 (G7.19.T3 draft READY; publish SUI)**
