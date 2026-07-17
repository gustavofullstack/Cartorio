# DPA MiniMax — Pacote READY-TO-SIGN (G7.19.T2)

**Controlador:** 2º Serviço Notarial de Uberlândia (Cartório 2º Ofício de Notas)  
**Operador / sub-processor:** MiniMax (modelos MiniMax-M2.7 / MiniMax-M3 e variantes)  
**Documento:** Data Processing Agreement (Acordo de Tratamento de Dados Pessoais)  
**Versão pacote:** 1.0 — G7 Wave 27  
**Data do pacote:** 2026-07-17  
**Status:** **READY_TO_SIGN** — rascunho jurídico pronto; **sem assinatura real**  
**Owner técnico:** `cartorio-lgpd`  
**Owner de assinatura (SUI):** Gustavo + DPO + representante MiniMax  

> **NÃO é contrato assinado.** Este pacote consolida cláusulas LGPD-ready a partir de
> `docs/lgpd/dpa_minimax_template.md`, `docs/DPA_FLOW_REPORT_2026-07-16.md` e
> `docs/LLM_DPA_MATRIX.md`. Produção com dado real de titular depende de (1) assinatura
> bilateral, (2) armazenamento de PDF assinado em `docs/lgpd/dpa_minimax.pdf`,
> (3) flag `LGPD_DPA_MINIMAX_SIGNED=true` e (4) entrada no audit log.

---

## 1. Partes

### 1.1 Controlador (Outorgante)

| Campo | Valor |
|-------|--------|
| Nome | Cartório 2º Ofício de Notas de Uberlândia — 2º Serviço Notarial de Uberlândia |
| Natureza | Serviço notarial delegado (pessoa jurídica de direito público em sentido amplo / atividade delegada) |
| CNPJ | `[PREENCHER — CNPJ oficial do cartório]` |
| Endereço | Uberlândia/MG, Brasil — `[ENDEREÇO COMPLETO]` |
| Representante legal | `[NOME_DO_TABELIAO]`, Tabelião(a) titular |
| Encarregado (DPO) | `[NOME_DO_DPO]` · **dpo@2notasudi.com.br** · `[TELEFONE_DO_DPO]` |
| Contato jurídico | dpo@2notasudi.com.br |

### 1.2 Operador (Outorgado)

| Campo | Valor |
|-------|--------|
| Nome comercial | MiniMax |
| Razão social | `[A PREENCHER PELA MINIMAX — due diligence]` |
| Registro / business ID | `[A PREENCHER PELA MINIMAX]` |
| Sede / jurisdição | `[A VERIFICAR — país de incorporação e data centers]` |
| Modelos cobertos | MiniMax-M2.7, MiniMax-M2.7-highspeed, MiniMax-M3 (e variantes documentadas em aditivo) |
| Contato privacidade | `[A PREENCHER PELA MINIMAX]` |
| Representante legal | `[A PREENCHER PELA MINIMAX]` |
| Endpoint técnico de referência | conforme configuração LiteLLM / OpenClaw do controlador (sem hardcode de secrets) |

> **Pré-assinatura:** DPO + Gustavo devem completar due diligence (sede, data residency,
> certificações ISO/SOC) e preencher placeholders da MiniMax **antes** de solicitar
> contrassinatura. Placeholders do cartório (CNPJ, tabelião, DPO nominal) também.

---

## 2. Objeto e finalidade do tratamento

2.1. O presente DPA regula o tratamento de dados pessoais realizado pela **MiniMax**
na qualidade de **operador** (LGPD art. 5º, VII e art. 39), em nome do controlador,
para a finalidade **exclusiva** de:

**Inferência de modelos de linguagem (LLM) no bot multi-canal do cartório**
(WhatsApp / Telegram / Web / LobeChat / OpenClaw / LiteLLM), incluindo:

- compreensão de intenção e resposta assistida ao titular ou ao escrevente;
- apoio a fluxos de atendimento (emolumentos, protocolos, FAQ, handoff HITL);
- tarefas operacionais do harness/reins quando o mesmo provedor for roteado
  (código, documentação, logs **já scrubbed**).

2.2. **É vedado** à MiniMax:

| # | Vedação |
|---|---------|
| (a) | Treinar, fine-tune, RLHF, “model improvement” ou qualquer reuso dos dados para modelos próprios ou de terceiros |
| (b) | Compartilhar com terceiros / subcontratados não autorizados por escrito |
| (c) | Profiling, tracking comportamental ou publicidade com dados do cartório |
| (d) | Persistir conteúdo de prompts/respostas além do estritamente necessário a SLA/billing (ver §5) |
| (e) | Decidir atos jurídicos finais (isenção, urgência, validade, emissão de certidão/escritura) — **HITL obrigatório no controlador** |

2.3. Qualquer mudança de modelo, endpoint ou finalidade exige **termo aditivo** escrito.

---

## 3. Categorias de dados (escopo mínimo — NO raw CPF)

### 3.1 Dados que **podem** ser processados (sempre scrubbed)

| Categoria | Exemplos | Observação |
|-----------|----------|------------|
| Texto de conversa scrubbed | perguntas sobre emolumentos, status de protocolo, FAQ | PII mascarado **antes** do envio (`backend/app/services/pii.py`) |
| Intenção / metadados de diálogo | intent, canal (WhatsApp/Telegram/Web), idioma `pt-BR` | sem identificador direto |
| Hash / tokens opacos | hash de cliente, session id | sem reidentificação trivial |
| Conteúdo técnico scrubbed (harness) | trechos de código/docs com placeholders | sem secrets, sem CPF raw |
| Timestamps grosseiros | granularidade horária | não segundo |

### 3.2 Dados que **NUNCA** devem chegar à MiniMax em produção

| Categoria | Exemplos | Controle |
|-----------|----------|----------|
| **CPF / RG / CNPJ raw** | números em claro | 3 camadas: input → pre-LLM → output |
| CNS / CNH raw | identificadores de saúde / habilitação | regex anchored + redaction |
| Telefone / e-mail raw | contato em claro | mask |
| Protocolo / escritura raw | número de protocolo, teor de escritura | mask / não envio |
| Secrets | API keys, tokens, senhas | redacted |
| Áudio/imagem de titular (não sintético) | mídia original | fora de escopo deste DPA em prod |
| Conteúdo integral do audit_log | cadeia de auditoria | só contagens agregadas, se necessário |

> **Regra de ouro:** se o payload contiver tag `DATASENSITIVE` ou falhar scrub,
> o orquestrador **não** roteia para MiniMax (prioridade a provedores SIGNED / local).

### 3.3 Categorias de titulares

- Titulares (clientes) do atendimento multi-canal — dados **indiretos e scrubbed**;
- Escreventes / operadores em LobeChat ou harness — metadados operacionais;
- Equipe técnica (logs de erro scrubbed).

---

## 4. Base legal e transferência internacional

| Fundamento | Aplicação |
|------------|-----------|
| LGPD art. 7º, V | execução de contrato / prestação do serviço solicitado |
| LGPD art. 7º, II | cumprimento de obrigação legal notarial (instrumental) |
| LGPD art. 7º, VI | interesse público do serviço cartorário delegado |
| LGPD art. 33, II | cláusulas contratuais específicas (SCC / padrões reconhecidos) se país sem adequação ANPD |
| LGPD art. 33, I | consentimento específico do titular quando exigido (termo `docs/consent.md`) |
| LGPD art. 39 | obrigações do operador |

**Transferência:** se data centers da MiniMax estiverem em país **sem** adequação ANPD,
a transferência só ocorre com (i) cláusulas deste DPA + (ii) consentimento específico
quando aplicável + (iii) PII scrubbing obrigatório. Due diligence de jurisdição é
**HOLD-GUSTAVO** pré-assinatura.

---

## 5. Retenção

| Onde | O quê | Prazo |
|------|--------|-------|
| **MiniMax (operador)** | Conteúdo de prompt/resposta | **Zero-storage preferencial**; no máximo logs técnicos de SLA **≤ 30 dias sem conteúdo** de conversa |
| **MiniMax** | Billing (tokens, modelo, timestamp) | conforme obrigação fiscal do operador, **sem conteúdo** |
| **Controlador (BR)** | Conversas scrubbed no Postgres | 365 dias (ou 90 dias para logs LLM, ver Privacy Policy v3) |
| **Controlador (BR)** | Audit log (hash chain + HMAC) | 5 anos (LGPD art. 37 + Provimento CNJ 74/2018) |
| **Pós-rescisão** | Devolução / eliminação | 15 dias (devolução) ou 30 dias (eliminação com certificado) |

Eliminação sob revogação de consentimento: MiniMax coopera em **≤ 30 dias** após
solicitação formal do controlador.

---

## 6. Sub-processadores

6.1. MiniMax **não** subcontratará sub-processors sem autorização **prévia, escrita e específica** do controlador.

6.2. Lista autorizada na data deste pacote:

| Sub-processor | País | Serviço | Status |
|---------------|------|---------|--------|
| *(nenhum autorizado)* | — | — | Preencher na assinatura se MiniMax declarar infra cloud |

6.3. Mudança: notificação prévia **30 dias**; silêncio do controlador = **rejeição** (opt-out).

6.4. Responsabilidade solidária do operador pelos sub-processors (LGPD art. 42).

---

## 7. Medidas de segurança (mínimo obrigatório)

### 7.1 Do operador (MiniMax)

- TLS 1.3 em trânsito; criptografia em repouso (AES-256 ou superior) se houver qualquer persistência;
- Controle de acesso least-privilege + MFA;
- Logs de acesso auditáveis;
- Notificação de incidente ao controlador em **≤ 24h** da detecção;
- Cooperação com ANPD e com o DPO do cartório;
- Certificações reconhecidas (ISO 27001 / SOC 2 Type II ou equivalentes) — comprovar na due diligence;
- **No training** clause expressa (Cláusula 2.2.a).

### 7.2 Do controlador (já implementado — referência)

- PII scrubbing 3 camadas (`app/services/pii.py`);
- Audit log append-only SHA-256 + HMAC;
- Rate limit + idempotência Redis;
- HITL obrigatório em ato jurídico;
- Dead-man's switch de integridade do audit (15 min);
- Sentry `before_send` scrubber + log masker.

---

## 8. Direitos do titular (LGPD art. 18)

A MiniMax **auxilia** o controlador (não atende titular diretamente):

| Direito | Prazo MiniMax → Controlador |
|---------|------------------------------|
| Confirmação, acesso, correção, anonimização, portabilidade, eliminação, informação, oposição, revogação, não-automação | **5 dias úteis** da solicitação do controlador |

Prazo do controlador ao titular: **15 dias úteis** (art. 18 §5º).  
Canal titular: **dpo@2notasudi.com.br** / portal LGPD / chatbot (`/lgpd`).

---

## 9. Incidentes, auditoria, rescisão (resumo executivo)

| Tema | Regra |
|------|--------|
| Incidente | Notificar controlador ≤ 24h; controlador notifica ANPD ≤ 72h se risco relevante (art. 48) |
| Auditoria | Relatório anual + auditoria on-site com 30 dias de aviso |
| Rescisão imediata | Uso para treino, vazamento, sub-processamento não autorizado, recusa de auditoria |
| Lei / foro | Lei brasileira (LGPD); foro **Comarca de Uberlândia/MG** |
| Vigência | Indeterminada enquanto houver uso do serviço; aditivos por escrito |

Cláusulas completas de responsabilidade, limites e seguros: ver template-fonte
`docs/lgpd/dpa_minimax_template.md` (Cláusulas 12ª–15ª) — incorporadas por referência
a este pacote para assinatura em PDF consolidado.

---

## 10. Blocos de assinatura

> **Status:** em branco de propósito. Agente **não** simula assinatura.

### 10.1 Pelo Controlador — 2º Serviço Notarial de Uberlândia

```
Tabelião(a) titular: _________________________________
Nome: [NOME_DO_TABELIAO]
Assinatura: _______________________ Data: ___/___/______

Encarregado de Dados (DPO): ___________________________
Nome: [NOME_DO_DPO]
E-mail: dpo@2notasudi.com.br
Assinatura: _______________________ Data: ___/___/______

Testemunha 1: _____________________ CPF: _______________
Testemunha 2: _____________________ CPF: _______________
```

### 10.2 Pela Operadora — MiniMax

```
Representante legal: __________________________________
Nome: [NOME_DO_REP_MINIMAX]    Cargo: [CARGO]
Assinatura: _______________________ Data: ___/___/______

DPO / Privacy contact MiniMax: ________________________
Nome: [NOME_DPO_MINIMAX]
Assinatura: _______________________ Data: ___/___/______

Testemunha 1: _____________________ ID: ________________
Testemunha 2: _____________________ ID: ________________
```

### 10.3 Formalização recomendada

- Assinatura eletrônica qualificada (ICP-Brasil) **ou** DocuSign / equivalente com trilha de auditoria;
- Apostila de Haia se a MiniMax exigir reconhecimento no exterior;
- Cópia final: `docs/lgpd/dpa_minimax.pdf` + backup offsite criptografado;
- Hash SHA-256 do PDF registrado no audit log (`dpa.minimax.signed`).

---

## 11. HOLD-GUSTAVO — checklist para assinar de verdade

**SUI residual (assinatura / produção).** O deliverable do agente termina aqui;
os itens abaixo são **humanos**.

| # | Ação | Quem | Done |
|---|------|------|------|
| 1 | Preencher CNPJ, endereço, nome do Tabelião e DPO nominal | Gustavo + Tabelião | [ ] |
| 2 | Due diligence MiniMax: razão social, sede, data centers, certs, lista de sub-processors | DPO + cartorio-lgpd | [ ] |
| 3 | Revisão jurídica externa (opcional mas recomendada — Doneda/Patricia Peck ou escritório local) | Jurídico | [ ] |
| 4 | Enviar este pacote + template completo a MiniMax (legal/privacy) | Gustavo | [ ] |
| 5 | Negociar “no training”, retenção zero de conteúdo, notificação 24h | Gustavo + MiniMax Legal | [ ] |
| 6 | Assinar bilateralmente (DPO + Tabelião + MiniMax) | SUI | [ ] |
| 7 | Salvar PDF em `docs/lgpd/dpa_minimax.pdf` (git-lfs ou vault se confidencial) | Gustavo | [ ] |
| 8 | Atualizar `scripts/dpa_sign_flow.py` / tracker → status `signed` | cartorio-lgpd | [ ] |
| 9 | Setar `LGPD_DPA_MINIMAX_SIGNED=true` no `.env` prod (EasyPanel) | Gustavo / SRE | [ ] |
| 10 | Audit log entry `dpa.minimax.signed` + atualizar `docs/LLM_DPA_MATRIX.md` → **SIGNED** | cartorio-lgpd | [ ] |
| 11 | Atualizar Privacy Policy publicada (v3) com status DPA MiniMax assinado | cartorio-lgpd + site | [ ] |
| 12 | Quarterly review: `docs/lgpd/dpa_quarterly_review.md` | DPO | [ ] |

**Até o item 6 estar completo:** MiniMax permanece **READY_TO_SIGN** (não SIGNED).
Roteamento de PII/DATASENSITIVE deve preferir providers já **SIGNED** ou Llama local.

---

## 12. Cross-references

| Documento | Papel |
|-----------|--------|
| `docs/lgpd/dpa_minimax_template.md` | Template cláusulas 1–15 (fonte completa) |
| `docs/DPA_FLOW_REPORT_2026-07-16.md` | Tracker de assinatura |
| `docs/LLM_DPA_MATRIX.md` | Matriz de provedores × status |
| `docs/lgpd/DPA_INDEX.md` | Índice D01–D05 |
| `docs/lgpd/RIPD_v1.4_ADDENDUM.md` | T16 MiniMax no RIPD |
| `docs/PRIVACY_POLICY_V3_G7.md` | Política v3 (transparência ao titular) |
| `docs/consent.md` | Consentimento multi-canal |
| `backend/app/services/pii.py` | Scrubbing 3 camadas |
| `docs/lgpd/policy/LGPD-014-CHECKLIST.md` | Padrão de checklist de assinatura (DeepSeek) |

---

## 13. Histórico deste pacote

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 2026-07-17 | Pacote READY_TO_SIGN G7.19.T2 Wave 27 — finalidade bot multi-canal + scrub no raw CPF; blocos de assinatura vazios; HOLD-GUSTAVO 12 itens | cartorio-lgpd |

---

**Modified by Gustavo Almeida + cartorio-lgpd — G7 Wave 27 (G7.19.T2 READY_TO_SIGN; sign SUI)**
