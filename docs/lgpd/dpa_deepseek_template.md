<!-- Modified by Gustavo Almeida (via cartorio-lgpd) -->

# Template de Data Processing Agreement (DPA) — DeepSeek (via OpenCode-Go)

**Versão:** 1.0 (template)
**Data:** 23 de junho de 2026
**Status:** **MODELO PARA NEGOCIAÇÃO JURÍDICA** — sem assinatura, **STAGING ONLY**
**Bloqueio:** LGPD-011 / LGPD-014 — Auditoria cartorio-lgpd v1.4 do RIPD

> **ATENÇÃO:** Este template é ponto de partida para negociação com a equipe jurídica da DeepSeek (Hangzhou DeepSeek Artificial Intelligence Co., Ltd.) e com o escritório de advocacia externo (Doneda/Patricia Peck). **Não é contrato assinado** e **não habilita uso de dados reais** até que (a) DPA seja assinado por ambas as partes, (b) DPO e Tabelião registrem a aprovação, e (c) o arquivo `docs/lgpd/dpa_deepseek.pdf` substitua este template.

---

## Partes

**Controlador (Outorgante):**
- **Nome:** Cartório 2º Ofício de Notas de Uberlândia
- **CNPJ:** XX.XXX.XXX/0001-XX
- **Endereço:** Uberlândia/MG, Brasil
- **Representante legal:** `[NOME_DO_TABELIAO]`, Tabelião(a) titular
- **Encarregado de Dados (DPO):** `[NOME_DO_DPO]` · dpo@2notasudi.com.br · `[TELEFONE_DO_DPO]`

**Operador (Outorgado):**
- **Nome:** Hangzhou DeepSeek Artificial Intelligence Co., Ltd. (operando como "DeepSeek")
- **Endereço:** Hangzhou, Zhejiang, República Popular da China
- **CNPJ estrangeiro:** N/A (sugerir campo de business registration number)
- **Representante legal:** `[A PREENCHER PELA DEEPSEEK]`
- **Contato de privacidade:** `[A PREENCHER PELA DEEPSEEK]`

---

## Cláusula 1ª — Objeto e Finalidade

1.1. O presente **Data Processing Agreement (DPA)** tem por objeto regular o tratamento de dados pessoais realizado pela **DeepSeek** (sub-processor) em nome do **Cartório 2º Ofício de Notas de Uberlândia** (controlador), por meio do gateway técnico **OpenCode-Go** (compatível com API OpenAI Chat Completions), para a finalidade **exclusiva** de execução de inferência de modelos de linguagem (LLM) aplicada ao chatbot do cartório — raciocínio, classificação de intenção, sumarização de contexto.

1.2. **É vedada** qualquer outra finalidade, em especial:
- (a) Treinamento, fine-tuning, improvement ou qualquer forma de uso dos dados para desenvolvimento de modelos da DeepSeek ou de terceiros;
- (b) Compartilhamento com terceiros, subcontratados não autorizados ou órgãos governamentais chineses sem ordem judicial internacional válida;
- (c) Criação de perfis, tracking de titulares brasileiros, ou qualquer forma de monitoramento comportamental;
- (d) Anonimização secundária para uso comercial próprio.

1.3. O modelo roteado é **`deepseek-v4-flash`** (compat OpenAI Chat Completions, low-cost). Qualquer mudança de modelo exige termo aditivo a este DPA.

---

## Cláusula 2ª — Base Legal e Hipótese de Transferência Internacional

2.1. O tratamento realizado pela DeepSeek fundamenta-se em:
- **LGPD art. 7º, V** — execução de contrato com o titular (prestação do serviço notarial solicitado via chatbot);
- **LGPD art. 7º, VI** — interesse público (serviço cartorário delegado, Provimento CNJ 74/2018);
- **LGPD art. 33, II** — cláusulas-padrão contratuais aprovadas pela ANPD ou, na ausência, padrões internacionais reconhecidos (SCC da Comissão Europeia), conforme Resolução CD/ANPD nº 4/2023.

2.2. **A República Popular da China NÃO possui adequação reconhecida pela ANPD.** Por isso, a transferência é realizada **exclusivamente** sob a égide do art. 33, II, exigindo-se cumulativamente:
- (a) **Consentimento específico e destacado** do titular, coletado no termo de consentimento (`docs/consent.md` v1.1+, Item 3);
- (b) **Cláusulas contratuais específicas** firmadas neste DPA, observado o art. 33, IX, da LGPD (cooperação entre ANPD e autoridades chinesas para fins de proteção de dados, quando aplicável);
- (c) **Due diligence reforçada** — relatório anual de auditoria demonstrando conformidade da DeepSeek com a LGPD.

2.3. A transferência ocorre **após** mitigação técnica por **PII scrubbing em 3 camadas** (input do usuário, pre-LLM, output do LLM) — vide `backend/app/services/pii.py`. **Dados brutos** (CPF, RG, CNPJ, CNS, CNH, telefone, e-mail, cartão, CEP, PIS, título, placa, data) **nunca** chegam ao servidor da DeepSeek.

---

## Cláusula 3ª — Tipos de Dados Tratados

3.1. **Dados pessoais tratados** (todos PII-scrubbed antes do envio):
- Texto livre da mensagem do cliente (com PII substituído por tokens `[CPF_REDACTED]`, `[EMAIL_REDACTED]`, etc.);
- Intenção classificada pelo backend;
- Contexto resumido da conversa (PII-scrubbed);
- Hash do cliente (SHA-256 com salt — para correlação sem expor identificador);
- Idioma detectado (ex.: "pt-BR");
- Timestamp aproximado (granularidade horária, não segundo).

3.2. **Dados SENSÍVEIS (LGPD art. 5º, II):**
- **CNS (Cartão Nacional de Saúde)** — pode aparecer em contexto se o titular mencionar dados de saúde;
- Mitigação: CNS detectado por regex anchored (palavra-chave + 30 caracteres de contexto + 2 formatos 15dig/17dig) e **redacted antes do envio**.

3.3. **É vedado** o tratamento de:
- (a) Imagens ou áudio bruto do cliente (dado biométrico — art. 5º, II);
- (b) Documentos jurídicos integrais (escritura, procuração) — apenas resumo PII-scrubbed;
- (c) Nome completo, endereço residencial, data de nascimento — substituídos por token genérico ou não enviados.

3.4. **Categorias de titulares:** clientes do chatbot do Cartório 2º Ofício de Notas de Uberlândia (pessoas físicas que iniciam conversa via WhatsApp/Telegram/Web).

---

## Cláusula 4ª — Duração e Retenção

4.1. A DeepSeek **NÃO** persiste instruções, prompts ou respostas para finalidade própria, salvo para:
- (a) SLA operacional (logs de requisição HTTP por ≤ 30 dias, **sem conteúdo de mensagens**);
- (b) Billing (contadores de tokens, timestamp, modelo — **sem conteúdo**);
- (c) Cumprimento de obrigação legal chinesa (quando aplicável — limitado a ≤ 6 meses).

4.2. **Retenção da auditoria do controlador** (no Brasil): o Cartório mantém log de auditoria próprio (audit log em Supabase Postgres) por **5 anos** (LGPD art. 37 + Provimento CNJ 74/2018), com `payload_hash` (SHA-256) e `scrubbed_payload` (sem dado bruto).

4.3. **Retenção de conversa** (no Brasil): **365 dias** (LGPD art. 7º, I — consentimento, com possibilidade de revogação). Após, anonimização ou eliminação conforme `docs/ripd.md` Tratamento 1.

4.4. **Eliminação mediante revogação do consentimento:** em até **30 dias** após revogação, todos os dados pessoais do titular são eliminados dos sistemas da DeepSeek (Cláusula 11ª).

---

## Cláusula 5ª — Obrigações do Operador (LGPD art. 39)

A DeepSeek, na qualidade de **operador** (art. 5º, VII), obriga-se a:

5.1. Tratar os dados pessoais **somente** para a finalidade descrita na Cláusula 1ª, seguindo as instruções documentadas do controlador.

5.2. **NÃO** transferir a terceiros, subcontratar ou compartilhar dados com qualquer entidade, pública ou privada, sem autorização **prévia, específica e por escrito** do controlador — exceto quando exigido por lei chinesa ou ordem judicial, hipótese em que a DeepSeek **notificará imediatamente** o controlador (Cláusula 7ª).

5.3. Implementar **medidas técnicas e administrativas** de segurança aptas a proteger os dados pessoais, conforme LGPD art. 46:
- Criptografia em trânsito (TLS 1.3) e em repouso (AES-256 ou superior);
- Controle de acesso por menor privilégio com autenticação multifator (MFA);
- Logs de acesso imutáveis (append-only com chain hash);
- Plano de resposta a incidentes com equipe de plantão 24/7;
- Testes de penetração anuais por terceiro independente.

5.4. **NÃO** realizar treinamento, fine-tuning, improvement, RLHF, ou qualquer forma de uso dos dados para desenvolvimento de modelos próprios ou de terceiros — **VEDAÇÃO EXPRESSA** (Cláusula 1ª, item 1.2.a).

5.5. Designar **Encarregado de Dados (DPO)** próprio, com contato direto ao DPO do controlador, e publicar política de privacidade própria em conformidade com PIPL (Personal Information Protection Law da China, equivalente à LGPD).

5.6. Manter **registro de todas as operações** de tratamento realizadas em nome do controlador, conforme LGPD art. 37, e disponibilizar ao controlador mediante solicitação (Cláusula 10ª).

5.7. **Eliminar ou devolver** todos os dados pessoais ao controlador ao término do contrato (Cláusula 11ª).

5.8. **Observar os princípios** do art. 6º da LGPD (finalidade, adequação, necessidade, livre acesso, qualidade dos dados, transparência, segurança, prevenção, não discriminação, responsabilização e prestação de contas) na execução do tratamento.

---

## Cláusula 6ª — Confidentialidade e Sigilo

6.1. A DeepSeek obriga-se a manter **sigilo absoluto** sobre os dados pessoais tratados, exigindo o mesmo compromisso de todos os seus colaboradores, subcontratados e terceiros com acesso aos dados.

6.2. O dever de sigilo subsiste **indefinidamente**, mesmo após o término deste DPA, por tempo indeterminado.

6.3. A quebra de sigilo, ainda que não resulte em dano imediato, é considerada **infração grave** deste DPA, sujeita às sanções da Cláusula 13ª e da legislação aplicável.

---

## Cláusula 7ª — Notificação de Incidentes de Segurança

7.1. A DeepSeek **notificará o controlador** sobre qualquer incidente de segurança que afete os dados pessoais tratados sob este DPA em prazo **não superior a 24 (vinte e quatro) horas** a partir da detecção — **mais restritivo** que o art. 48 da LGPD (que permite "razoável prazo").

7.2. A notificação conterá, no mínimo:
- (a) Descrição detalhada do incidente (tipo, causa, escopo);
- (b) Categorias e volume estimado de dados afetados;
- (c) Categorias e número estimado de titulares afetados;
- (d) Medidas técnicas e administrativas já adotadas para mitigação;
- (e) Plano de remediação com cronograma;
- (f) Ponto de contato para informações adicionais.

7.3. A DeepSeek cooperará com o controlador e com a ANPD em investigação subsequente, fornecendo logs, evidências forenses e relatórios de auditoria.

7.4. Se o incidente atingir **risco ou dano relevante** aos titulares, o controlador notificará a **ANPD em até 72 horas** (LGPD art. 48) e os **titulares afetados sem demora indevida**, com apoio da DeepSeek na apuração dos fatos.

---

## Cláusula 8ª — Sub-processadores

8.1. A DeepSeek **NÃO** subcontratará nenhum sub-processor para tratamento de dados pessoais sob este DPA sem autorização **prévia, específica e por escrito** do controlador.

8.2. Caso a DeepSeek deseje utilizar sub-processadores, deverá:
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

9.1. A DeepSeek auxiliará o controlador, mediante solicitação, no atendimento dos direitos do titular previstos no art. 18 da LGPD:
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

9.2. Prazo de resposta da DeepSeek: até **5 (cinco) dias úteis** contados da solicitação do controlador, para que este possa cumprir o prazo de 15 dias úteis ao titular (LGPD art. 18, §5º).

9.3. A DeepSeek **NÃO** atenderá diretamente solicitações de titulares** que chegarem pelos canais da DeepSeek — **redirecionará ao controlador** em até 48 horas.

---

## Cláusula 10ª — Auditoria e Transparência

10.1. A DeepSeek disponibilizará ao controlador, **anualmente** ou mediante solicitação justificada (ex.: incidente, fiscalização ANPD), relatório de auditoria de:
- (a) Conformidade com este DPA;
- (b) Medidas de segurança implementadas;
- (c) Lista atualizada de sub-processadores;
- (d) Estatísticas de incidentes de segurança (quantidade, tipo, severidade, resolução);
- (e) Resultados de testes de penetração e auditorias independentes.

10.2. O controlador poderá, mediante notificação prévia de **30 dias**, realizar **auditoria presencial** nas instalações da DeepSeek, ou contratar auditor independente, para verificar conformidade com este DPA. Custo da auditoria: por conta do controlador, salvo quando identificadas não-conformidades graves (custeadas pela DeepSeek).

10.3. A DeepSeek manterá **certificações de segurança** reconhecidas (ISO 27001, SOC 2 Tipo II, ou equivalentes) durante toda a vigência deste DPA, e comunicará perda ou suspensão imediatamente.

---

## Cláusula 11ª — Devolução ou Eliminação de Dados

11.1. Ao término deste DPA (rescisão, denúncia, ou qualquer causa), a DeepSeek **devolverá** ao controlador todos os dados pessoais tratados sob este DPA em formato estruturado e interoperável (JSON + CSV com dicionário de dados), em até **15 dias**.

11.2. Alternativamente, mediante opção do controlador, a DeepSeek **eliminará** definitivamente todos os dados pessoais, com **certificado de eliminação** assinado por representante legal, em até **30 dias**.

11.3. Logs de SLA e billing da DeepSeek serão **eliminados em até 90 dias** após o término, exceto quando retidos para cumprimento de obrigação legal chinesa específica.

11.4. Após eliminação/devolução, a DeepSeek **manterá apenas metadados** mínimos para fins de prova de cumprimento contratual (ex.: hash SHA-256 do conjunto de dados devolvido, data da eliminação, assinatura do responsável) por **5 anos**.

---

## Cláusula 12ª — Responsabilidade

12.1. A DeepSeek responde por **danos causados** ao controlador e aos titulares em decorrência de:
- (a) Tratamento de dados em descumprimento das instruções documentadas do controlador;
- (b) Falha nas medidas de segurança;
- (c) Quebra de sigilo;
- (d) Compartilhamento não autorizado;
- (e) Uso para finalidade diversa da contratada.

12.2. **Responsabilidade solidária** (LGPD art. 42): nas hipóteses do item 12.1, a DeepSeek responde **solidariamente** com o controlador perante os titulares, sem prejuízo do direito de regresso.

12.3. **Limite de responsabilidade** (a negociar com jurídico):
- (a) Para incidentes sem dolo: até o valor total pago pelo controlador nos 12 meses imediatamente anteriores, OU R$ 1.000.000,00 (o que for maior);
- (b) Para incidentes com dolo ou culpa grave: **sem limite** de responsabilidade;
- (c) Em qualquer caso, sem prejuízo de:
  - Multas administrativas da ANPD (até 2% do faturamento, limitado a R$ 50M por infração);
  - Indenização aos titulares por danos morais e materiais (LGPD art. 42, §1º).

12.4. **Seguro de responsabilidade civil**: a DeepSeek manterá apólice de seguro de RC com cobertura mínima de **R$ 5.000.000,00** (cinco milhões de reais) durante toda a vigência deste DPA, com cobertura específica para incidentes de dados pessoais.

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
- (h) Falência, insolvência ou dissolução da DeepSeek.

13.2. **Notificação prévia** de **30 dias** para rescisão por conveniência do controlador, sem multa.

13.3. **Sanções intermediárias** (antes da rescisão): advertência por escrito, com prazo de 15 dias para regularização, em caso de descumprimento não-material.

13.4. Em qualquer caso de rescisão, aplicam-se as Cláusulas 11ª (devolução/eliminação) e 12ª (responsabilidade).

---

## Cláusula 14ª — Lei Aplicável e Foro

14.1. Este DPA é regido pela **lei brasileira**, em especial pela **Lei nº 13.709/2018 (LGPD)**, com aplicação subsidiária do Código Civil e do Código de Defesa do Consumidor quando cabível.

14.2. Fica eleito o **foro da Comarca de Uberlândia, Estado de Minas Gerais**, Brasil, para dirimir quaisquer controvérsias, com renúncia expressa a qualquer outro, por mais privilegiado que seja.

14.3. Em caso de conflito entre este DPA e a legislação chinesa (PIPL), prevalece a LGPD para efeitos de tratamento de dados de titulares brasileiros, sem prejuízo da aplicação de PIPL para dados de titulares chineses eventualmente tratados pela DeepSeek em outros contextos.

---

## Cláusula 15ª — Disposições Finais

15.1. Este DPA entra em vigor na data de sua assinatura e vigorará por **prazo indeterminado**, enquanto perdurar a relação entre controlador e operador.

15.2. Alterações exigirão **termo aditivo escrito** assinado por ambas as partes.

15.3. A nulidade de qualquer cláusula não afeta a validade das demais.

15.4. Este DPA é parte integrante do **contrato principal** de prestação de serviços entre as partes, e quaisquer conflitos de interpretação serão resolvidos pela regra da **especialidade**.

15.5. As partes declaram ter lido e compreendido todas as cláusulas, estando cientes dos direitos e obrigações aqui previstos, em especial da gravidade das sanções da LGPD (multa de até 2% do faturamento, limitada a R$ 50 milhões por infração, art. 52).

15.6. A DeepSeek declara estar ciente de que o Brasil é país signatário de convenções internacionais de proteção de dados e que decisões da ANPD são vinculantes para operadores que tratam dados de titulares brasileiros, mesmo sediados no exterior.

---

## Assinaturas

**Pelo Controlador (Cartório 2º Ofício de Notas de Uberlândia):**

- Tabelião(a) titular: `[NOME_DO_TABELIAO]` — Assinatura: ___________________ Data: ___/___/______
- Encarregado de Dados (DPO): `[NOME_DO_DPO]` — Assinatura: ___________________ Data: ___/___/______
- Testemunha 1: _________________________________ CPF: _____________
- Testemunha 2: _________________________________ CPF: _____________

**Pela Operadora (Hangzhou DeepSeek Artificial Intelligence Co., Ltd.):**

- Representante legal: `[NOME_DO_REP]` — Cargo: `[CARGO]` — Assinatura: ___________________ Data: ___/___/______
- Encarregado de Dados (DPO): `[NOME_DO_DPO_DEEPSEEK]` — Assinatura: ___________________ Data: ___/___/______
- Testemunha 1: _________________________________ ID: _____________
- Testemunha 2: _________________________________ ID: _____________

**Reconhecido por:** Tabelião de Notas em Uberlândia/MG, Brasil, com Apostila de Haia para vigência na China (Convenção da Haia de 1961).

---

## Histórico de Versões do Template

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 23/06/2026 | Versão inicial do template — 15 cláusulas obrigatórias conforme modelo ANPD + Resolução CD/ANPD nº 4/2023 + IAPP. Pendente revisão jurídica externa (Doneda/Patricia Peck — 8-16h) e negociação com DeepSeek (2-6 semanas). Status: **STAGING ONLY** até `docs/lgpd/dpa_deepseek.pdf` substituir este template. | Rein `cartorio-lgpd` (sessão `mvs_d4fa1b1a154149dfb0bbadbb117ad1c1`) |

## Cross-References

- `docs/ripd.md` v1.4 — Tratamento 7 + R13–R17 + R18–R19
- `docs/consent.md` v1.1 — Item 3 (compartilhamento com DeepSeek + consentimento específico)
- `docs/privacy-policy.md` v1.1 — Seção 5 (compartilhamento) + Seção 9 (transferência internacional)
- `docs/lgpd/AUDITORIA_BLOCKERS.md` — Bloqueio #6 (DPA pendente)
- `backend/app/integrations/opencode_go.py` — PII scrubbing em 3 camadas (input/pre-LLM/output)
- `backend/app/services/pii.py` — Implementação do PII scrubber

Modified by Gustavo Almeida (via cartorio-lgpd)
