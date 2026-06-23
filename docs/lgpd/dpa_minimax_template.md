<!-- Modified by Gustavo Almeida (via cartorio-lgpd mvs_3c841fe2622b4755bcd39d89333d4037) -->

# Template de Data Processing Agreement (DPA) — MiniMax (MiniMax-M2.7 / M3)

**Versão:** 1.0 (template)
**Data:** 23 de junho de 2026 (20:13 BRT)
**Status:** **MODELO PARA NEGOCIAÇÃO JURÍDICA** — sem assinatura, **STAGING ONLY**
**Bloqueio:** LGPD-015 — Pendente assinatura Gustavo + DPO
**Provider real:** provider LLM externo (configurado em `.harness/reins/*/opencode/opencode.json` como provider `minimax`, baseURL `https://agent.minimax.io/mavis/api/v1/llm/v1`, API key armazenada em `.env` do OpenCode)

> **ATENÇÃO:** Este template é ponto de partida para negociação com a equipe jurídica da MiniMax (operadora do gateway LLM que serve os modelos `MiniMax-M2.7`, `MiniMax-M2.7-highspeed` e `MiniMax-M3`) e com o escritório de advocacia externo (Doneda/Patricia Peck). **Não é contrato assinado** e **não habilita uso de dados reais** até que (a) DPA seja assinado por ambas as partes, (b) DPO e Tabelião registrem a aprovação, e (c) o arquivo `docs/lgpd/dpa_minimax.pdf` substitua este template.

> **DIFERENÇA CRÍTICA vs DPA DeepSeek:** enquanto a DeepSeek é o sub-processor primário que processa conteúdo de **clientes finais** do chatbot WhatsApp, a MiniMax é o sub-processor que processa conteúdo **operacional do harness** — ou seja, dados pessoais que aparecem no código-fonte (`backend/app/services/pii.py`, `backend/app/api/v1/router.py`, `docs/ripd.md`, etc) que os reins (`cartorio-dev`, `cartorio-lgpd`, `cartorio-n8n`) leem para auditar, revisar, implementar, documentar. **Ambos são PII** (LGPD art. 5º, I) e **ambos exigem base legal específica** (LGPD art. 7º).

---

## Contexto Diferencial (MiniMax vs DeepSeek)

| Aspecto | DeepSeek (DPA principal) | MiniMax (este DPA) |
|---------|--------------------------|---------------------|
| **Função** | Sub-processor LLM de **cliente final** (chatbot WhatsApp) | Sub-processor LLM do **harness operacional** (reins de Mavis) |
| **Onde atua** | `backend/app/integrations/opencode_go.py` (`deepseek-v4-flash`) | `.harness/reins/*/opencode/opencode.json` (provider `minimax`) |
| **Quem usa** | Cliente final via webhook WhatsApp/Telegram/Web | Reins do harness (`cartorio-dev`, `cartorio-lgpd`, `cartorio-n8n`) |
| **Modelos** | `deepseek-v4-flash` | `MiniMax-M2.7`, `MiniMax-M2.7-highspeed`, `MiniMax-M3` (multimodal text/image/video) |
| **BaseURL** | `https://api.opencode.ai/v1` (via gateway OpenCode-Go) | `https://agent.minimax.io/mavis/api/v1/llm/v1` (direto) |
| **PII em risco** | Mensagens de clientes (texto, intenção, contexto) | Código-fonte com PII hardcoded/embed, documentação LGPD, audit reports, logs de conversa do harness |
| **Sede provável** | Hangzhou, China | A verificar (URL `minimax.io` + basepath `mavis` sugere integração Mavis-flavored, mas jurisdição TBD) |
| **Mecanismo跨境** | art. 33 II (SCC) + I (consent específico) — duplo | art. 33 II (SCC) + I (consent específico) — duplo (idêntico) |
| **Status DPA** | LGPD-014 (template existente) | **LGPD-015** (este template) |

---

## Partes

**Controlador (Outorgante):**
- **Nome:** Cartório 2º Ofício de Notas de Uberlândia
- **CNPJ:** XX.XXX.XXX/0001-XX
- **Endereço:** Uberlândia/MG, Brasil
- **Representante legal:** `[NOME_DO_TABELIAO]`, Tabelião(a) titular
- **Encarregado de Dados (DPO):** `[NOME_DO_DPO]` · dpo@2notasudi.com.br · `[TELEFONE_DO_DPO]`

**Operador (Outorgado):**
- **Nome:** MiniMax (operadora dos modelos MiniMax-M2.7 / M2.7-highspeed / M3) — razão social a preencher após due diligence
- **Endereço:** `[A VERIFICAR — jurisdição pendente due diligence]`
- **CNPJ estrangeiro / business registration:** `[A PREENCHER PELA MINIMAX]`
- **Representante legal:** `[A PREENCHER PELA MINIMAX]`
- **Contato de privacidade:** `[A PREENCHER PELA MINIMAX]`

> **⚠️ AÇÃO PRÉ-NEGOCIAÇÃO:** antes de enviar este template para a MiniMax, cartorio-dev + DPO devem (a) identificar sede legal da MiniMax, (b) obter business registration number, (c) confirmar país de operação dos data centers, (d) mapear jurisdição aplicável (LGPD art. 33 — verificar se país tem adequação ANPD).

---

## Cláusula 1ª — Objeto e Finalidade

1.1. O presente **Data Processing Agreement (DPA)** tem por objeto regular o tratamento de dados pessoais realizado pela **MiniMax** (sub-processor) em nome do **Cartório 2º Ofício de Notas de Uberlândia** (controlador), por meio de inferência de modelos de linguagem (LLM) **MiniMax-M2.7**, **MiniMax-M2.7-highspeed** e **MiniMax-M3**, para a finalidade **exclusiva** de execução de tarefas operacionais do harness do cartório — auditoria de código, revisão LGPD, implementação de features, geração de documentação, depuração — aplicadas aos reins do time (`cartorio-dev`, `cartorio-lgpd`, `cartorio-n8n`).

1.2. **É vedada** qualquer outra finalidade, em especial:
- (a) Treinamento, fine-tuning, improvement, RLHF, ou qualquer forma de uso dos dados para desenvolvimento de modelos da MiniMax ou de terceiros;
- (b) Compartilhamento com terceiros, subcontratados não autorizados ou órgãos governamentais sem ordem judicial internacional válida;
- (c) Criação de perfis, tracking de titulares brasileiros, ou qualquer forma de monitoramento comportamental;
- (d) Anonimização secundária para uso comercial próprio;
- (e) Uso para inferência em aplicações de **clientes finais** do cartório (este DPA cobre apenas o harness operacional — clientes finais são cobertos pelo DPA DeepSeek).

1.3. Os modelos roteados são **`MiniMax-M2.7`**, **`MiniMax-M2.7-highspeed`** e **`MiniMax-M3`** (este último com capacidade multimodal text/image/video). Qualquer mudança de modelo exige **termo aditivo** a este DPA.

1.4. O **endpoint técnico** é `https://agent.minimax.io/mavis/api/v1/llm/v1` (compat OpenAI Chat Completions). Mudança de endpoint exige notificação prévia de 30 dias e aceite escrito do controlador.

---

## Cláusula 2ª — Base Legal e Hipótese de Transferência Internacional

2.1. O tratamento realizado pela MiniMax fundamenta-se em:
- **LGPD art. 7º, V** — execução de contrato com o titular (prestação do serviço notarial solicitada via chatbot — o harness é instrumental ao serviço);
- **LGPD art. 7º, VI** — interesse público (serviço cartorário delegado, Provimento CNJ 74/2018);
- **LGPD art. 33, II** — cláusulas-padrão contratuais aprovadas pela ANPD ou, na ausência, padrões internacionais reconhecidos (SCC da Comissão Europeia), conforme Resolução CD/ANPD nº 4/2023.

2.2. **A jurisdição da MiniMax DEVE SER VERIFICADA pré-assinatura.** Se for país sem adequação ANPD (atualmente apenas EUA + UK + UE + alguns outros reconhecidos), a transferência é realizada **exclusivamente** sob a égide do art. 33, II, exigindo-se cumulativamente:
- (a) **Consentimento específico e destacado** dos titulares afetados (clientes do chatbot que têm seus dados refletidos em logs/código que o harness processa), coletado em termo específico;
- (b) **Cláusulas contratuais específicas** firmadas neste DPA, observado o art. 33, IX, da LGPD (cooperação entre ANPD e autoridades locais para fins de proteção de dados, quando aplicável);
- (c) **Due diligence reforçada** — relatório anual de auditoria demonstrando conformidade da MiniMax com a LGPD.

2.3. **PII scrubbing em 3 camadas** (input, pre-LLM, output) é aplicado pelo **harness** (Mavis runtime) antes de enviar prompts à MiniMax — vide `backend/app/services/pii.py`. **Dados brutos** (CPF, RG, CNPJ, CNS, CNH, telefone, e-mail, cartão, CEP, PIS, título, placa, data) **NUNCA** chegam ao servidor da MiniMax em produção — apenas em testes, onde devem ser sintéticos.

2.4. **Vedação específica para dados de harness:** o harness NÃO envia à MiniMax:
- (a) Mensagens originais de clientes (apenas metadados, código, documentação, logs scrubbed);
- (b) Áudio, imagem, vídeo de clientes (apenas em testes sintéticos);
- (c) Conteúdo integral do `audit_log` (apenas contagens agregadas);
- (d) Credenciais, API keys, secrets (substituídos por placeholders `[REDACTED]`).

---

## Cláusula 3ª — Tipos de Dados Tratados

3.1. **Dados pessoais tratados** (todos PII-scrubbed antes do envio pelo harness):
- Trechos de código-fonte do backend (com PII substituído por tokens);
- Trechos de documentação LGPD (`docs/ripd.md`, `docs/consent.md`, `docs/privacy-policy.md`, `docs/lgpd/*`);
- Logs de execução do harness (scrubbed);
- Mensagens de erro e stack traces (scrubbed);
- Hash SHA-256 do cliente (para correlação sem expor identificador);
- Idioma detectado (ex.: "pt-BR");
- Timestamp aproximado (granularidade horária, não segundo).

3.2. **Dados SENSÍVEIS (LGPD art. 5º, II):**
- **CNS (Cartão Nacional de Saúde)** — pode aparecer em exemplos de código/auditoria se o harness auditar logs que mencionam clientes com procurações de saúde;
- Mitigação: CNS detectado por regex anchored (palavra-chave + 30 caracteres de contexto + 2 formatos 15dig/17dig) e **redacted antes do envio** (`backend/app/services/pii.py`).

3.3. **É vedado** o tratamento de:
- (a) Mensagens brutas de clientes finais (cobertura: DPA DeepSeek);
- (b) Áudio, imagem, vídeo de clientes finais;
- (c) Conteúdo integral de `audit_log` (apenas contagens);
- (d) Credenciais, API keys, secrets (sempre placeholders);
- (e) Nome completo de titulares, endereço residencial, data de nascimento — substituídos por token genérico ou não enviados.

3.4. **Categorias de titulares afetados:**
- (a) **Indiretos** — clientes finais cujos dados aparecem em código/auditoria processada pelo harness (cobertura: DPA DeepSeek);
- (b) **Operacionais** — escreventes, tabelião, DPO que aparecem em logs de auditoria do harness (cobertura: este DPA);
- (c) **Equipe** — desenvolvedores e auditores do harness (cobertura: este DPA, base legal art. 7º, II — cumprimento de obrigação legal do controlador).

---

## Cláusula 4ª — Duração e Retenção

4.1. A MiniMax **NÃO** persiste instruções, prompts ou respostas para finalidade própria, salvo para:
- (a) SLA operacional (logs de requisição HTTP por ≤ 30 dias, **sem conteúdo de harness**);
- (b) Billing (contadores de tokens, timestamp, modelo — **sem conteúdo**);
- (c) Cumprimento de obrigação legal da jurisdição aplicável (quando aplicável — limitado a ≤ 6 meses).

4.2. **Retenção da auditoria do controlador** (no Brasil): o Cartório mantém log de auditoria próprio (audit log em Supabase Postgres) por **5 anos** (LGPD art. 37 + Provimento CNJ 74/2018), com `payload_hash` (SHA-256) e `scrubbed_payload` (sem dado bruto).

4.3. **Retenção de logs do harness** (no Brasil): **365 dias** (LGPD art. 7º, I — consentimento, com possibilidade de revogação). Após, anonimização ou eliminação conforme `docs/ripd.md` Tratamento 1.

4.4. **Eliminação mediante revogação do consentimento:** em até **30 dias** após revogação, todos os dados pessoais do titular são eliminados dos sistemas da MiniMax (Cláusula 11ª).

---

## Cláusula 5ª — Obrigações do Operador (LGPD art. 39)

A MiniMax, na qualidade de **operador** (art. 5º, VII), obriga-se a:

5.1. Tratar os dados pessoais **somente** para a finalidade descrita na Cláusula 1ª, seguindo as instruções documentadas do controlador.

5.2. **NÃO** transferir a terceiros, subcontratar ou compartilhar dados com qualquer entidade, pública ou privada, sem autorização **prévia, específica e por escrito** do controlador — exceto quando exigido por lei da jurisdição aplicável ou ordem judicial, hipótese em que a MiniMax **notificará imediatamente** o controlador (Cláusula 7ª).

5.3. Implementar **medidas técnicas e administrativas** de segurança aptas a proteger os dados pessoais, conforme LGPD art. 46:
- Criptografia em trânsito (TLS 1.3) e em repouso (AES-256 ou superior);
- Controle de acesso por menor privilégio com autenticação multifator (MFA);
- Logs de acesso imutáveis (append-only com chain hash);
- Plano de resposta a incidentes com equipe de plantão 24/7;
- Testes de penetração anuais por terceiro independente.

5.4. **NÃO** realizar treinamento, fine-tuning, improvement, RLHF, ou qualquer forma de uso dos dados para desenvolvimento de modelos próprios ou de terceiros — **VEDAÇÃO EXPRESSA** (Cláusula 1ª, item 1.2.a).

5.5. Designar **Encarregado de Dados (DPO)** próprio, com contato direto ao DPO do controlador, e publicar política de privacidade própria em conformidade com a legislação local aplicável.

5.6. Manter **registro de todas as operações** de tratamento realizadas em nome do controlador, conforme LGPD art. 37, e disponibilizar ao controlador mediante solicitação (Cláusula 10ª).

5.7. **Eliminar ou devolver** todos os dados pessoais ao controlador ao término do contrato (Cláusula 11ª).

5.8. **Observar os princípios** do art. 6º da LGPD (finalidade, adequação, necessidade, livre acesso, qualidade dos dados, transparência, segurança, prevenção, não discriminação, responsabilização e prestação de contas) na execução do tratamento.

---

## Cláusula 6ª — Confidencialidade e Sigilo

6.1. A MiniMax obriga-se a manter **sigilo absoluto** sobre os dados pessoais tratados, exigindo o mesmo compromisso de todos os seus colaboradores, subcontratados e terceiros com acesso aos dados.

6.2. O dever de sigilo subsiste **indefinidamente**, mesmo após o término deste DPA, por tempo indeterminado.

6.3. A quebra de sigilo, ainda que não resulte em dano imediato, é considerada **infração grave** deste DPA, sujeita às sanções da Cláusula 13ª e da legislação aplicável.

---

## Cláusula 7ª — Notificação de Incidentes de Segurança

7.1. A MiniMax **notificará o controlador** sobre qualquer incidente de segurança que afete os dados pessoais tratados sob este DPA em prazo **não superior a 24 (vinte e quatro) horas** a partir da detecção — **mais restritivo** que o art. 48 da LGPD (que permite "razoável prazo").

7.2. A notificação conterá, no mínimo:
- (a) Descrição detalhada do incidente (tipo, causa, escopo);
- (b) Categorias e volume estimado de dados afetados;
- (c) Categorias e número estimado de titulares afetados;
- (d) Medidas técnicas e administrativas já adotadas para mitigação;
- (e) Plano de remediação com cronograma;
- (f) Ponto de contato para informações adicionais.

7.3. A MiniMax cooperará com o controlador e com a ANPD em investigação subsequente, fornecendo logs, evidências forenses e relatórios de auditoria.

7.4. Se o incidente atingir **risco ou dano relevante** aos titulares, o controlador notificará a **ANPD em até 72 horas** (LGPD art. 48) e os **titulares afetados sem demora indevida**, com apoio da MiniMax na apuração dos fatos.

---

## Cláusula 8ª — Sub-processadores

8.1. A MiniMax **NÃO** subcontratará nenhum sub-processor para tratamento de dados pessoais sob este DPA sem autorização **prévia, específica e por escrito** do controlador.

8.2. Caso a MiniMax deseje utilizar sub-processadores, deverá:
- (a) Apresentar lista prévia de sub-processadores pretendidos, com descrição dos serviços e países de operação;
- (b) Celebrar contrato com cada sub-processor com cláusulas **equivalentes ou mais restritivas** que as deste DPA;
- (c) Manter **responsabilidade solidária** por atos e omissões dos sub-processadores (art. 42 da LGPD).

8.3. **Lista atual** de sub-processadores autorizados (a preencher antes da assinatura):
| Sub-processor | País | Serviço | Justificativa |
|---------------|------|---------|---------------|
| *(nenhum autorizado nesta data)* | — | — | — |

8.4. Mudança de sub-processor exige **notificação prévia de 30 dias** e **silêncio = rejeição** (opt-out).

---

## Cláusula 9ª — Direitos do Titular (LGPD art. 18)

9.1. A MiniMax auxiliará o controlador, mediante solicitação, no atendimento dos direitos do titular previstos no art. 18 da LGPD:
- (a) Confirmação da existência de tratamento;
- (b) Acesso aos dados;
- (c) Correção de dados incompletos, inexatos ou desatualizados;
- (d) Anonimização, bloqueio ou eliminação de dados desnecessários ou excessivos;
- (e) Portabilidade;
- (f) Eliminação dos dados tratados com consentimento;
- (g) Informação sobre entidades públicas e privadas com as quais houve compartilhamento;
- (h) Informação sobre a possibilidade de não fornecer consentimento e suas consequências;
- (i) Revogação do consentimento;
- (j) Oposição a tratamento.

9.2. Prazo de resposta da MiniMax: até **5 (cinco) dias úteis** contados da solicitação do controlador, para que este possa cumprir o prazo de 15 dias úteis ao titular (LGPD art. 18, §5º).

9.3. A MiniMax **NÃO** atenderá diretamente solicitações de titulares que chegarem pelos canais da MiniMax — **redirecionará ao controlador** em até 48 horas.

---

## Cláusula 10ª — Auditoria e Transparência

10.1. A MiniMax disponibilizará ao controlador, **anualmente** ou mediante solicitação justificada (ex.: incidente, fiscalização ANPD), relatório de auditoria de:
- (a) Conformidade com este DPA;
- (b) Medidas de segurança implementadas;
- (c) Lista atualizada de sub-processadores;
- (d) Estatísticas de incidentes de segurança (quantidade, tipo, severidade, resolução);
- (e) Resultados de testes de penetração e auditorias independentes.

10.2. O controlador poderá, mediante notificação prévia de **30 dias**, realizar **auditoria presencial** nas instalações da MiniMax, ou contratar auditor independente, para verificar conformidade com este DPA. Custo da auditoria: por conta do controlador, salvo quando identificadas não-conformidades graves (custeadas pela MiniMax).

10.3. A MiniMax manterá **certificações de segurança** reconhecidas (ISO 27001, SOC 2 Tipo II, ou equivalentes) durante toda a vigência deste DPA, e comunicará perda ou suspensão imediatamente.

---

## Cláusula 11ª — Devolução ou Eliminação de Dados

11.1. Ao término deste DPA (rescisão, denúncia, ou qualquer causa), a MiniMax **devolverá** ao controlador todos os dados pessoais tratados sob este DPA em formato estruturado e interoperável (JSON + CSV com dicionário de dados), em até **15 dias**.

11.2. Alternativamente, mediante opção do controlador, a MiniMax **eliminará** definitivamente todos os dados pessoais, com **certificado de eliminação** assinado por representante legal, em até **30 dias**.

11.3. Logs de SLA e billing da MiniMax serão **eliminados em até 90 dias** após o término, exceto quando retidos para cumprimento de obrigação legal específica.

11.4. Após eliminação/devolução, a MiniMax **manterá apenas metadados** mínimos para fins de prova de cumprimento contratual (ex.: hash SHA-256 do conjunto de dados devolvido, data da eliminação, assinatura do responsável) por **5 anos**.

---

## Cláusula 12ª — Responsabilidade

12.1. A MiniMax responde por **danos causados** ao controlador e aos titulares em decorrência de:
- (a) Tratamento de dados em descumprimento das instruções documentadas do controlador;
- (b) Falha nas medidas de segurança;
- (c) Quebra de sigilo;
- (d) Compartilhamento não autorizado;
- (e) Uso para finalidade diversa da contratada.

12.2. **Responsabilidade solidária** (LGPD art. 42): nas hipóteses do item 12.1, a MiniMax responde **solidariamente** com o controlador perante os titulares, sem prejuízo do direito de regresso.

12.3. **Limite de responsabilidade** (a negociar com jurídico):
- (a) Para incidentes sem dolo: até o valor total pago pelo controlador nos 12 meses imediatamente anteriores, OU R$ 1.000.000,00 (o que for maior);
- (b) Para incidentes com dolo ou culpa grave: **sem limite** de responsabilidade;
- (c) Em qualquer caso, sem prejuízo de:
  - Multas administrativas da ANPD (até 2% do faturamento, limitado a R$ 50M por infração);
  - Indenização aos titulares por danos morais e materiais (LGPD art. 42, §1º).

12.4. **Seguro de responsabilidade civil**: a MiniMax manterá apólice de seguro de RC com cobertura mínima de **R$ 5.000.000,00** (cinco milhões de reais) durante toda a vigência deste DPA, com cobertura específica para incidentes de dados pessoais.

---

## Cláusula 13ª — Rescisão e Sanções

13.1. **Causas de rescisão imediata** pelo controlador (sem necessidade de notificação prévia):
- (a) Descumprimento material de qualquer cláusula deste DPA;
- (b) Quebra de sigilo;
- (c) Uso de dados para finalidade diversa da contratada;
- (d) Compartilhamento não autorizado com terceiros;
- (e) Sub-contratação não autorizada;
- (f) Perda de certificações de segurança exigidas;
- (g) Recusa em submeter-se a auditoria;
- (h) Falência, insolvência ou dissolução da MiniMax.

13.2. **Notificação prévia** de **30 dias** para rescisão por conveniência do controlador, sem multa.

13.3. **Sanções intermediárias** (antes da rescisão): advertência por escrito, com prazo de 15 dias para regularização, em caso de descumprimento não-material.

13.4. Em qualquer caso de rescisão, aplicam-se as Cláusulas 11ª (devolução/eliminação) e 12ª (responsabilidade).

---

## Cláusula 14ª — Lei Aplicável e Foro

14.1. Este DPA é regido pela **lei brasileira**, em especial pela **Lei nº 13.709/2018 (LGPD)**, com aplicação subsidiária do Código Civil e do Código de Defesa do Consumidor quando cabível.

14.2. Fica eleito o **foro da Comarca de Uberlândia, Estado de Minas Gerais**, Brasil, para dirimir quaisquer controvérsias, com renúncia expressa a qualquer outro, por mais privilegiado que seja.

14.3. Em caso de conflito entre este DPA e a legislação da jurisdição da MiniMax, prevalece a LGPD para efeitos de tratamento de dados de titulares brasileiros.

---

## Cláusula 15ª — Disposições Finais

15.1. Este DPA entra em vigor na data de sua assinatura e vigorará por **prazo indeterminado**, enquanto perdurar a relação entre controlador e operador.

15.2. Alterações exigirão **termo aditivo escrito** assinado por ambas as partes.

15.3. A nulidade de qualquer cláusula não afeta a validade das demais.

15.4. Este DPA é parte integrante do **contrato principal** de prestação de serviços entre as partes, e quaisquer conflitos de interpretação serão resolvidos pela regra da **especialidade**.

15.5. As partes declaram ter lido e compreendido todas as cláusulas, estando cientes dos direitos e obrigações aqui previstos, em especial da gravidade das sanções da LGPD (multa de até 2% do faturamento, limitada a R$ 50 milhões por infração, art. 52).

15.6. A MiniMax declara estar ciente de que o Brasil é país signatário de convenções internacionais de proteção de dados e que decisões da ANPD são vinculantes para operadores que tratam dados de titulares brasileiros, mesmo sediados no exterior.

---

## Assinaturas

**Pelo Controlador (Cartório 2º Ofício de Notas de Uberlândia):**

- Tabelião(a) titular: `[NOME_DO_TABELIAO]` — Assinatura: ___________________ Data: ___/___/______
- Encarregado de Dados (DPO): `[NOME_DO_DPO]` — Assinatura: ___________________ Data: ___/___/______
- Testemunha 1: _________________________________ CPF: _____________
- Testemunha 2: _________________________________ CPF: _____________

**Pela Operadora (MiniMax — razão social a preencher):**

- Representante legal: `[NOME_DO_REP]` — Cargo: `[CARGO]` — Assinatura: ___________________ Data: ___/___/______
- Encarregado de Dados (DPO): `[NOME_DO_DPO_MINIMAX]` — Assinatura: ___________________ Data: ___/___/______
- Testemunha 1: _________________________________ ID: _____________
- Testemunha 2: _________________________________ ID: _____________

**Reconhecido por:** Tabelião de Notas em Uberlândia/MG, Brasil, com **Apostila de Haia** para vigência na jurisdição aplicável (Convenção da Haia de 1961).

---

## Histórico de Versões do Template

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 23/06/2026 20:13 BRT | Versão inicial do template — 15 cláusulas obrigatórias conforme modelo ANPD + Resolução CD/ANPD nº 4/2023 + IAPP. Baseado no template DPA DeepSeek, com adaptações específicas para o contexto do harness operacional (reins do Mavis runtime). Pendente revisão jurídica externa (Doneda/Patricia Peck — 8-16h) e due diligence sobre sede legal da MiniMax. Status: **STAGING ONLY** até `docs/lgpd/dpa_minimax.pdf` substituir este template. | Rein `cartorio-lgpd` (sessão `mvs_3c841fe2622b4755bcd39d89333d4037`) |

## Cross-References

- `docs/lgpd/dpa_deepseek_template.md` — DPA principal (sub-processor primário, cliente final)
- `docs/lgpd/dpa_opencode_go_template.md` — DPA gateway técnico (compat OpenAI Chat Completions)
- `docs/lgpd/dpa_evolution_api_template.md` — DPA Evolution API (sub-processor BR, WhatsApp)
- `docs/ripd.md` v1.3 — Tratamento 7 (referência a sub-processors LLM) + R13–R17
- `docs/consent.md` v1.0 — Item 3 (compartilhamento com sub-processors)
- `docs/privacy-policy.md` v1.0 — Seção 5 (compartilhamento) + Seção 9 (transferência internacional)
- `docs/lgpd/AUDITORIA_BLOCKERS.md` — Pendência #8 (4 NOVOS blockers) + Bloqueio histórico
- `.harness/reins/*/opencode/opencode.json` — Configuração técnica do provider `minimax`
- `.harness/TASKS.md` E6.S3.T15 / E6.S9.T4 — DPA MiniMax pendente (escalado Gustavo)
- `backend/app/services/pii.py` — PII scrubbing em 3 camadas (input/pre-LLM/output)
- `backend/app/integrations/opencode_go.py` — Provider LLM cliente (DeepSeek, NÃO MiniMax — não confundir)

Modified by Gustavo Almeida (via cartorio-lgpd mvs_3c841fe2622b4755bcd39d89333d4037)
