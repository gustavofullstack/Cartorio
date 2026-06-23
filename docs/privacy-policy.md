# Política de Privacidade — Cartório 2 Notas Uberlândia

**Versão:** 1.0
**Data de entrada em vigor:** 23 de junho de 2026
**Data da última atualização:** 23 de junho de 2026
**Controlador:** Cartório 2º Ofício de Notas de Uberlândia — 2 Notas Udi LTDA
**Encarregado de Dados (DPO):** dpo@2notasudi.com.br

> Este documento é parte do Programa de Conformidade LGPD do Cartório 2 Notas Uberlândia e descreve, de forma clara e acessível, como tratamos dados pessoais no chatbot WhatsApp/Telegram/Web e nos sistemas internos (API FastAPI, n8n, Evolution API, OpenClaw, Supabase). Elaborado em conformidade com a **Lei nº 13.709/2018 (LGPD)** e com o **Provimento CNJ nº 74/2018**.

---

## 1. Quem somos (controlador)

Cartório 2º Ofício de Notas de Uberlândia, pessoa jurídica de direito público delegado, registrado sob CNPJ nº XX.XXX.XXX/0001-XX, com sede em Uberlândia/MG. Atuamos como **controlador** dos dados pessoais coletados pelo chatbot e pelos sistemas operacionais do cartório, nos termos do art. 5º, VI, da LGPD.

Para qualquer dúvida sobre este documento, entre em contato com o nosso Encarregado de Dados (DPO):

- **E-mail:** dpo@2notasudi.com.br
- **Canal web:** https://2notasudi.com.br/dpo
- **Prazo de resposta:** até 15 (quinze) dias úteis, conforme LGPD art. 18 §5º

---

## 2. Dados pessoais que coletamos

Coletamos apenas os dados estritamente necessários para a finalidade declarada, em conformidade com o princípio da **necessidade** (LGPD art. 6º, III) e da **minimização** (LGPD art. 6º, VIII):

| Categoria | Exemplos | Finalidade |
|-----------|----------|-----------|
| Identificação | Nome completo, CPF (hasheado), RG (hasheado), CNPJ (hasheado) | Identificar partes em protocolo notarial |
| Contato | Telefone (WhatsApp/Telegram), e-mail | Responder solicitações e enviar notificações |
| Conteúdo da conversa | Texto, áudio (transcrito), imagens (descrição) | Executar o serviço solicitado |
| Dados do ato | Tipo de ato, valor, partes envolvidas, documentos | Cumprir obrigação legal (Provimento CNJ 74/2018) |
| Metadados técnicos | Endereço IP, agente do navegador, identificador de sessão | Segurança, auditoria (LGPD art. 37) e prevenção a fraude |

**Importante:** números brutos de CPF, RG, CNPJ, cartão de crédito, telefone e e-mail são **automaticamente mascarados** antes de qualquer chamada a modelos de linguagem (LLM) externos. Apenas hashes SHA-256 com salt por cliente são armazenados no banco de dados, jamais os valores originais em texto claro fora do campo específico do ato (LGPD art. 46).

---

## 3. Bases legais para o tratamento

Tratamos dados pessoais com fundamento nas seguintes hipóteses do art. 7º da LGPD:

- **Inciso I — Consentimento:** para finalidades que não são obrigação legal do cartório (ex.: envio de newsletter, pesquisas de satisfação, prospecção por WhatsApp).
- **Inciso II — Cumprimento de obrigação legal:** para guardar protocolos, documentos, livros e audit log pelo prazo previsto no Provimento CNJ 74/2018 e em legislação tributária.
- **Inciso V — Exercício regular de direitos:** para atender solicitações do titular, da corregedoria, do Poder Judiciário ou do Ministério Público.
- **Inciso VI — Interesse público:** para finalidades de auditoria interna, segurança da informação e prevenção a fraudes (LGPD art. 37).

Quando o tratamento se basear em **consentimento**, você pode revogá-lo a qualquer momento, sem prejuízo da licitude do tratamento realizado anteriormente (LGPD art. 8º §5º).

---

## 4. Finalidades de uso

Seus dados pessoais são utilizados **exclusivamente** para:

1. **Atendimento ao público via chatbot** — responder dúvidas sobre emolumentos, andamento de protocolos, agendamento e serviços notariais.
2. **Execução do serviço notarial** — lavratura de escrituras, procurações, atas, reconhecimento de firmas, autenticações.
3. **Cumprimento de obrigações legais e regulatórias** — guarda de livros e documentos (Provimento 74/2018), prestação de contas à corregedoria, emissão de certidões, retenção tributária.
4. **Segurança da informação e auditoria** — registro de acesso (LGPD art. 37), hash chain de auditoria (LGPD art. 50), prevenção a incidentes.
5. **Comunicação** — envio de notificações sobre o andamento do ato, confirmação de presença, retorno de solicitações.

**Não utilizamos seus dados para:** marketing agressivo, venda para terceiros, treinamento de modelos de IA sem o seu consentimento explícito e adicional, ou qualquer finalidade distinta das acima sem novo consentimento.

---

## 5. Compartilhamento

Compartilhamos dados pessoais **apenas** quando estritamente necessário:

| Destinatário | Hipótese | Base legal |
|--------------|----------|-----------|
| Corregedoria Geral de Justiça (MG) | Prestação de contas, fiscalização | Obrigação legal (LGPD art. 7º II) |
| Poder Judiciário e MP | Citação, intimação, requisição | Obrigação legal (LGPD art. 7º II) |
| Receita Federal / SEFAZ | Retenção de impostos, DOI, DIMOB | Obrigação legal |
| OpenClaw / LLM (Claude, GPT) | Apenas dados **scrubbed** (mascarados) | Consentimento + operador (LGPD art. 39) |
| Fornecedores de infraestrutura (Hostinger, Supabase, Cloudflare) | Operação e segurança | Execução de contrato (LGPD art. 7º V) |
| Autoridade Nacional de Proteção de Dados (ANPD) | Notificação de incidente, requisição | Obrigação legal (LGPD art. 48) |

Todo operador (LGPD art. 5º, VII) contratado pelo cartório assina contrato com cláusulas específicas de proteção de dados, conforme art. 39 da LGPD, e está proibido de tratar dados para finalidade própria.

---

## 6. Retenção de dados

Aplicamos o princípio da **necessidade de retenção** (LGPD art. 16):

| Tipo de dado | Prazo de retenção | Base legal | Ação após o prazo |
|--------------|-------------------|------------|-------------------|
| Conversa do chatbot (texto scrubbed) | 365 dias | Consentimento (LGPD art. 7º I) | Apagada |
| Áudio/imagem da conversa | 365 dias | Consentimento | Apagada |
| Protocolo notarial | 5 anos após o ato | Provimento CNJ 74/2018 | Anonimizado |
| Documento notarial (escritura, procuração) | 20+ anos | Obrigação legal | Mantido (anonimização de partes não essenciais) |
| Audit log (LGPD art. 37) | 5 anos | Obrigação legal + interesse público | Mantido (sem PII) |
| Log de acesso (LGPD art. 37) | 5 anos | Obrigação legal | Mantido |
| Tabela de emolumentos | Indeterminado | Obrigação legal | Mantida |
| Registro de consentimento | Enquanto durar a relação + 5 anos | Obrigação legal | Mantido registro da revogação |

Passado o prazo, os dados são **apagados** ou **anonimizados** (LGPD art. 12), conforme o caso. A anonimização impede a reidentificação, segundo critérios técnicos razoáveis.

---

## 7. Direitos do titular (LGPD art. 18)

Você tem os seguintes direitos sobre seus dados pessoais. Para exercê-los, envie solicitação a **dpo@2notasudi.com.br** com cópia de documento de identificação:

1. **Confirmação da existência de tratamento** — saber se tratamos seus dados.
2. **Acesso aos dados** — receber cópia dos dados que temos sobre você.
3. **Correção de dados incompletos, inexatos ou desatualizados.**
4. **Anonimização, bloqueio ou eliminação** de dados desnecessários, excessivos ou tratados em desconformidade.
5. **Portabilidade** — receber seus dados em formato estruturado e interoperável.
6. **Eliminação dos dados tratados com consentimento.**
7. **Informação sobre entidades públicas e privadas com as quais houve compartilhamento.**
8. **Informação sobre a possibilidade de não fornecer consentimento e suas consequências.**
9. **Revogação do consentimento** (LGPD art. 8º §5º).
10. **Oposição a tratamento** realizado com fundamento em interesse público ou interesse legítimo, em caso de descumprimento da LGPD.

**Resposta:** até 15 (quinze) dias úteis, contados do recebimento da solicitação completa (LGPD art. 18 §5º).

---

## 8. Segurança da informação (LGPD art. 46)

Adotamos medidas técnicas e administrativas para proteger seus dados:

- **Criptografia em trânsito** (TLS 1.3) e em repouso (Postgres + Storage criptografados).
- **PII scrubbing em 3 camadas** — toda mensagem é varrida por regex calibrada para CPF, RG, CNPJ, telefone, e-mail, cartão, CEP, PIS e título de eleitor **antes** de qualquer chamada a LLM externo.
- **Audit log imutável** — todas as mutações em dados pessoais são registradas em cadeia append-only com SHA-256 + HMAC (LGPD art. 50 — boas práticas). Verificação automática diária.
- **Hash de PII** — CPF, RG e CNPJ são armazenados como `SHA-256(salt + valor)`, permitindo *lookup* sem guardar o valor original.
- **Princípio do menor privilégio** — cada operador/rein do nosso sistema de agentes tem acesso apenas ao necessário.
- **Backups diários** — criptografados, retenção 30 dias, restauráveis mediante aprovação do DPO.
- **Logs de acesso** — quem acessou, quando, de onde, com qual finalidade (LGPD art. 37).
- **Human-in-the-loop** — o bot **nunca** decide sozinho em ato jurídico final (isenção, urgência, validade, emissão de certidão/escritura).

Em caso de incidente de segurança que possa acarretar risco ou dano relevante, notificaremos a **ANPD em até 72 horas** e os **titulares afetados sem demora indevida**, conforme LGPD art. 48.

---

## 9. Transferência internacional

Dados pessoais podem ser transferidos a operadores internacionais (OpenAI, Anthropic, Cloudflare, Hostinger) sediados nos EUA e União Europeia, sempre com:

- Cláusulas contratuais específicas (LGPD art. 33, II);
- Garantia de adequação ao GDPR (LGPD art. 33, I) quando aplicável;
- Registro da transferência no nosso inventário de tratamento.

**Importante:** dados enviados a LLMs externos são **sempre scrubbed** (CPF, RG, CNPJ, telefone, e-mail mascarados). Apenas dados não sensíveis e não identificáveis chegam a esses operadores.

---

## 10. Cookies e tecnologias de rastreamento

O chatbot web utiliza cookies estritamente necessários para sessão e segurança. **Não utilizamos** cookies de rastreamento publicitário, Facebook Pixel, Google Ads ou similares sem consentimento específico (LGPD art. 8º).

---

## 11. Crianças e adolescentes

O chatbot **não se destina** a crianças menores de 12 anos (LGPD art. 14). Para adolescentes entre 12 e 18 anos, o tratamento ocorre apenas com consentimento específico do responsável legal, em sintonia com o art. 14 §4º.

---

## 12. Encarregado de Dados (DPO)

**E-mail:** dpo@2notasudi.com.br
**Canal web:** https://2notasudi.com.br/dpo
**Atribuições:** LGPD art. 41 §2º — aceitar reclamações, prestar esclarecimentos, receber comunicações da ANPD, orientar colaboradores, executar a política de privacidade.

---

## 13. Como reclamar à ANPD

Se você considerar que seus direitos não foram atendidos, registre reclamação diretamente com a **Autoridade Nacional de Proteção de Dados**:

- Site: https://www.gov.br/anpd
- E-mail: atendimento@anpd.gov.br
- Telefone: 0800 979 4040

---

## 14. Alterações desta política

Esta política pode ser revisada periodicamente para refletir mudanças operacionais, legais ou regulatórias. A versão atual é sempre a publicada em https://2notasudi.com.br/privacidade.

Mudanças materiais serão comunicadas com **antecedência razoável** pelo chatbot e por e-mail, solicitando novo consentimento quando exigido por lei.

---

## 15. Vigência

Esta versão entra em vigor em **23 de junho de 2026** e permanece válida até ser substituída por versão posterior.

---

**Aprovação interna:**

- DPO — [assinatura digital]
- Tabelião(a) — [assinatura digital]
- Comitê de Compliance — [ata da reunião]

**Base legal consultada:** LGPD Lei 13.709/2018; Provimento CNJ 74/2018; Resoluções ANPD; GDPR (referência).

Modified by Gustavo Almeida