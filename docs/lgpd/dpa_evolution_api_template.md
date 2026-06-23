<!-- Modified by Gustavo Almeida (via cartorio-lgpd) -->

# Template de Data Processing Agreement (DPA) — Evolution API (WhatsApp BR)

**Versão:** 1.0 (template)
**Data:** 23 de junho de 2026
**Status:** **MODELO PARA NEGOCIAÇÃO JURÍDICA** — sem assinatura
**Sub-processor:** Evolution API (Brasil) — integração WhatsApp Business API
**Base legal:** LGPD art. 7º, **II** (cumprimento de obrigação legal — Provimento CNJ 74/2018) + art. 7º, V (execução de contrato)

> **ATENÇÃO:** A Evolution API é um **sub-processor brasileiro** que opera o canal de mensageria WhatsApp Business API. Por ser BR (país com adequação) e baseado em cumprimento de obrigação legal, este DPA é **significativamente mais simples** que o DPA da DeepSeek (China) — sem transferência internacional, sem cláusulas de SCC, e com retenção regida principalmente pelo Provimento CNJ 74/2018.

---

## Contexto Diferencial

A Evolution API é uma **solução brasileira** (hospedada em VPS no Brasil via Easypanel) que faz a integração técnica com a **WhatsApp Business API** (Meta). Características:

1. **Opera dados no Brasil** — VPS na Hostinger/Easypanel, sem跨境.
2. **Base legal primária: obrigação legal** (LGPD art. 7º, II) — o cartório DEVE manter canal de atendimento ao público (Provimento CNJ 74/2018 + Lei 8.935/94).
3. **Função técnica:** receber/enviar mensagens WhatsApp em nome do cartório, com webhook para o backend FastAPI.
4. **NÃO treina modelos, NÃO compartilha com terceiros** fora do fluxo técnico WhatsApp.
5. **Compartilhamento com Meta Platforms (WhatsApp):** apenas metadados técnicos (conta, número, template messages) — WhatsApp Business API opera sob contrato Meta + LGPD.

Por essas razões, este DPA é **significativamente mais simples** e foca em:

- Continuidade operacional do canal (SLA);
- Retenção de logs para cumprimento de obrigação legal;
- Medidas de segurança (criptografia, controle de acesso);
- Direito do titular sobre mensagens (acesso, eliminação dentro do prazo legal).

---

## Partes

**Controlador (Outorgante):**
- **Nome:** Cartório 2º Ofício de Notas de Uberlândia
- **CNPJ:** XX.XXX.XXX/0001-XX
- **Endereço:** Uberlândia/MG, Brasil
- **Representante legal:** `[NOME_DO_TABELIAO]`
- **Encarregado de Dados (DPO):** `[NOME_DO_DPO]` · dpo@2notasudi.com.br · `[TELEFONE_DO_DPO]`

**Operador (Outorgado):**
- **Nome:** Evolution API (provedor de integração WhatsApp Business API)
- **Endereço:** `[A PREENCHER — provedor do software Evolution]`
- **CNPJ:** `[A PREENCHER]`
- **Representante legal:** `[A PREENCHER]`
- **Encarregado de Dados (DPO):** `[A PREENCHER]`
- **Hospedagem:** VPS Hostinger (Brasil) — contrato à parte com Hostinger

**Sub-processor (não-parte deste DPA, contratualmente vinculado):**
- **Meta Platforms, Inc.** (WhatsApp Business API) — contrato Meta + termos de uso WhatsApp Business

---

## Cláusula 1ª — Objeto e Finalidade

1.1. O presente DPA tem por objeto regular a prestação de serviço de **integração técnica com WhatsApp Business API** pela Evolution API, em nome do **Cartório 2º Ofício de Notas de Uberlândia** (controlador), para a finalidade de:

- (a) Receber mensagens WhatsApp de clientes do cartório;
- (b) Enviar respostas automáticas (via backend FastAPI do controlador);
- (c) Roteamento de mensagens para Chatwoot (atendimento humano, quando necessário);
- (d) Manutenção de canal de atendimento ao público em cumprimento ao Provimento CNJ 74/2018.

1.2. A Evolution API atuará **exclusivamente** como intermediária técnica entre o WhatsApp Business API (Meta) e o backend do controlador. Não armazenará mensagens além do necessário para SLA de roteamento.

1.3. **É vedado** à Evolution API:
- (a) Inspecionar, modificar ou analisar o conteúdo das mensagens para finalidade própria;
- (b) Compartilhar dados com terceiros além da Meta (WhatsApp);
- (c) Usar dados para treinamento de modelos, marketing, ou qualquer finalidade não autorizada;
- (d) Transferir dados para fora do Brasil.

---

## Cláusula 2ª — Base Legal

2.1. O tratamento de dados realizado pela Evolution API fundamenta-se em:
- **LGPD art. 7º, II** — cumprimento de obrigação legal (Provimento CNJ 74/2018 + Lei 8.935/94 — serviço público delegado de cartório);
- **LGPD art. 7º, V** — execução de contrato (prestação do serviço de mensageria contratado pelo controlador);
- **LGPD art. 7º, IX** — interesse legítimo do controlador (operação eficiente do canal de atendimento), respeitados os direitos do titular (art. 10).

2.2. **NÃO há transferência internacional** pela Evolution API — VPS no Brasil, sem跨境. O compartilhamento com a Meta (WhatsApp Business API) é regido pelo contrato Meta + termos de uso do WhatsApp Business, que já preveem cláusulas de proteção de dados (Meta é signatária do Privacy Shield sucessor — Data Privacy Framework UE-EUA, embora não diretamente aplicável ao Brasil).

2.3. Quando a Meta processar dados de titulares brasileiros, o faz sob **Privacy Policy do WhatsApp Business** (https://www.whatsapp.com/legal/business-policy/) e **Terms of Service** próprios — sem necessidade de DPA adicional com o controlador, embora o controlador mantenha o **direto controle** sobre os dados (acesso, eliminação via API).

---

## Cláusula 3ª — Tipos de Dados Tratados

3.1. **Dados de canal (necessários para operação WhatsApp):**
- Número de telefone do titular (identificador WhatsApp);
- Nome do perfil WhatsApp (quando o titular permite);
- Mensagens trocadas (texto, áudio, imagem, vídeo, documentos);
- Metadados de mensagem (timestamp, status de entrega, confirmação de leitura);
- ID da instância Evolution (cartório-2notas).

3.2. **Dados do controlador:**
- Credenciais de API (instance token, webhook secret);
- Configuração de webhook (URL do backend FastAPI);
- Templates de mensagem pré-aprovados pela Meta.

3.3. **Dados sensíveis (LGPD art. 5º, II):**
- Podem ser tratados se o titular enviar (ex.: CNS em contexto de procuração para tratamento de saúde, imagem de documento com foto);
- Mitigação: PII scrubbing em 3 camadas (input do webhook, pre-LLM, output do LLM) no backend do controlador **ANTES** de persistir ou rotear;
- A Evolution API **NÃO** tem obrigação de scrubbing — ela roteia, o controlador trata.

3.4. **Categorias de titulares:** clientes do cartório, cidadãos em geral, escreventes, tabelião(a) — qualquer pessoa que inicie conversa WhatsApp com o cartório.

---

## Cláusula 4ª — Duração e Retenção

4.1. **Mensagens em trânsito (na memória da Evolution API):** retidas por **≤ 1 hora** para garantia de entrega. Após, eliminadas automaticamente.

4.2. **Logs de SLA e billing (Evolution API):** retidos por **90 dias** para fins de auditoria técnica e billing.

4.3. **Mensagens persistidas (no banco do controlador, NÃO na Evolution):** regidas pela política de retenção do controlador:
- Conversa de bot: **365 dias** (LGPD art. 7º, I — consentimento);
- Protocolo notarial: **5 anos** (Provimento CNJ 74/2018);
- Documentos: **20+ anos** (obrigação legal).

4.4. **Retenção obrigatória de logs de auditoria** (LGPD art. 37): **5 anos** mantidos pelo controlador.

4.5. **Eliminação mediante revogação do consentimento:** em até **30 dias**, a Evolution API eliminará metadados de roteamento; a eliminação das mensagens em si é responsabilidade do controlador (via `DELETE /cliente/{id}` — LGPD art. 18, VI).

---

## Cláusula 5ª — Obrigações do Operador (LGPD art. 39)

A Evolution API obriga-se a:

5.1. Roteamento **exclusivo** entre WhatsApp Business API (Meta) e o backend do controlador. **NÃO** inspecionar, modificar ou analisar o conteúdo das mensagens para finalidade própria.

5.2. Manter **criptografia em trânsito** (TLS 1.3) e em repouso (banco de dados criptografado).

5.3. Implementar **controle de acesso** ao painel administrativo da Evolution (apenas DPO + tabelião + admin técnico autorizado).

5.4. **NÃO** compartilhar dados com terceiros além da Meta (WhatsApp) e do controlador.

5.5. **Notificar o controlador** em **≤ 24 horas** de qualquer incidente de segurança (Cláusula 7ª).

5.6. **Manter logs de auditoria** (quem acessou o painel, quando) por **5 anos**.

5.7. **Cooperar** com o controlador no atendimento de direitos do titular (Cláusula 9ª).

5.8. **Conformidade com Meta (WhatsApp Business):** seguir as **WhatsApp Business Policy** e **Commerce Policy** (quando aplicável), sob pena de bloqueio do número WhatsApp.

---

## Cláusula 6ª — Confidentialidade

6.1. A Evolution API manterá **sigilo absoluto** sobre todas as mensagens e metadados roteados.

6.2. O dever de sigilo subsiste **indefinidamente**, mesmo após o término do contrato.

---

## Cláusula 7ª — Notificação de Incidentes

7.1. A Evolution API **notificará o controlador** em **≤ 24 horas** de qualquer:
- (a) Incidente de segurança que afete dados pessoais;
- (b) Acesso não autorizado ao painel;
- (c) Perda de mensagens em trânsito;
- (d) Bloqueio do número WhatsApp pela Meta;
- (e) Indisponibilidade do serviço por mais de 1 hora.

7.2. Notificação seguirá o formato padrão (descrição, escopo, medidas, plano de remediação).

7.3. Em caso de **risco ou dano relevante** aos titulares, o controlador notificará a ANPD em **≤ 72 horas** (LGPD art. 48) e os titulares afetados.

---

## Cláusula 8ª — Sub-processadores

8.1. **Único sub-processor:** **Meta Platforms, Inc.** (WhatsApp Business API), regido pelo contrato Meta + WhatsApp Business Policy.

8.2. A Evolution API **NÃO** subcontratará nenhum sub-processor adicional sem notificação prévia de 30 dias e autorização do controlador.

8.3. A hospedagem (VPS Hostinger) é coberta por contrato à parte com a Hostinger, com cláusulas de proteção de dados (DPA Hostinger padrão).

---

## Cláusula 9ª — Direitos do Titular (LGPD art. 18)

9.1. O controlador atenderá os direitos do titular **diretamente** (tempo de resposta: 15 dias úteis conforme LGPD art. 18, §5º).

9.2. Quando o titular solicitar exclusão de mensagens, o controlador:
- (a) Eliminará as mensagens do banco do controlador em **≤ 30 dias**;
- (b) Solicitará à Evolution API a eliminação de metadados de roteamento em **≤ 15 dias**;
- (c) Manterá registro da revogação (LGPD art. 8º, §5º).

9.3. A Evolution API **NÃO** atenderá solicitações diretas de titulares** que chegarem pelos canais da Evolution — **redirecionará ao controlador** em até 48 horas.

9.4. **Atenção:** mensagens que constituam **obrigação legal** (ex.: registro de conversa para fins de protocolo notarial) **NÃO** podem ser eliminadas a pedido do titular (LGPD art. 16). O controlador informará o titular dessa exceção.

---

## Cláusula 10ª — Auditoria

10.1. A Evolution API disponibilizará **anualmente** relatório de:
- (a) Conformidade com este DPA;
- (b) Estatísticas de uso e SLA;
- (c) Histórico de incidentes.

10.2. O controlador poderá, mediante notificação de 30 dias, realizar **auditoria presencial** ou contratar auditor independente.

---

## Cláusula 11ª — Devolução ou Eliminação de Dados

11.1. Ao término do DPA, a Evolution API:
- (a) Eliminará todas as mensagens em trânsito (≤ 1 hora após término);
- (b) Devolverá ao controlador os logs de SLA/billing (formato JSON + CSV) em **≤ 15 dias**;
- (c) Eliminará os logs de auditoria próprios em **≤ 90 dias**;
- (d) Fornecerá **certificado de eliminação** assinado por representante legal.

11.2. **Não há base de dados persistente** de mensagens na Evolution API para devolver — toda persistência é feita pelo controlador (backend Supabase).

---

## Cláusula 12ª — Responsabilidade

12.1. A Evolution API responde por danos causados por:
- (a) Inspecionar, modificar ou analisar conteúdo de mensagens;
- (b) Compartilhar dados com terceiros não autorizados;
- (c) Falha de segurança (vazamento, acesso não autorizado);
- (d) Indisponibilidade prolongada (SLA não cumprido);
- (e) Bloqueio do número WhatsApp por descumprimento da WhatsApp Business Policy.

12.2. **Limite de responsabilidade** (a negociar com jurídico):
- (a) Até o valor total pago pelo controlador nos 12 meses imediatamente anteriores;
- (b) Sem limite em caso de dolo ou culpa grave.

12.3. Em qualquer caso, sem prejuízo de:
- Multas administrativas da ANPD (até 2% do faturamento, limitado a R$ 50M por infração);
- Indenização aos titulares por danos morais e materiais.

12.4. A Evolution API manterá **seguro de RC** com cobertura mínima de **R$ 2.000.000,00**.

---

## Cláusula 13ª — Rescisão e Sanções

13.1. **Causas de rescisão imediata** pelo controlador:
- (a) Descumprimento material deste DPA;
- (b) Quebra de sigilo;
- (c) Inspecionar/armazenar conteúdo de mensagens;
- (d) Compartilhamento não autorizado;
- (e) Perda de certificações de segurança exigidas;
- (f) Recusa em auditoria;
- (g) Bloqueio do número WhatsApp por descumprimento da WhatsApp Business Policy.

13.2. **Notificação prévia** de 30 dias para rescisão por conveniência.

13.3. Em caso de rescisão, aplicam-se Cláusulas 11ª (eliminação/devolução) e 12ª (responsabilidade).

---

## Cláusula 14ª — Lei Aplicável e Foro

14.1. Este DPA é regido pela **lei brasileira** (LGPD Lei 13.709/2018), com aplicação subsidiária do Código Civil e do Código de Defesa do Consumidor.

14.2. Fica eleito o **foro da Comarca de Uberlândia, Estado de Minas Gerais**, Brasil, com renúncia a qualquer outro.

---

## Cláusula 15ª — Disposições Finais

15.1. Este DPA entra em vigor na data de sua assinatura e vigorará por **prazo indeterminado**, enquanto perdurar a relação entre controlador e Evolution API.

15.2. Alterações exigirão **termo aditivo escrito** assinado por ambas as partes.

15.3. As partes declaram ter lido e compreendido todas as cláusulas, em especial a gravidade das sanções da LGPD.

15.4. Este DPA é **complementar** ao contrato principal de hospedagem Evolution API + Easypanel + Hostinger.

15.5. Em caso de conflito entre este DPA e a WhatsApp Business Policy da Meta, prevalece a WhatsApp Business Policy para aspectos técnicos do WhatsApp; este DPA prevalece para aspectos de proteção de dados pessoais.

---

## Assinaturas

**Pelo Controlador (Cartório 2º Ofício de Notas de Uberlândia):**

- Tabelião(a) titular: `[NOME_DO_TABELIAO]` — Assinatura: ___________________ Data: ___/___/______
- Encarregado de Dados (DPO): `[NOME_DO_DPO]` — Assinatura: ___________________ Data: ___/___/______

**Pela Operadora (Evolution API):**

- Representante legal: `[NOME_DO_REP]` — Cargo: `[CARGO]` — Assinatura: ___________________ Data: ___/___/______
- Encarregado de Dados (DPO): `[NOME_DO_DPO_EVOLUTION]` — Assinatura: ___________________ Data: ___/___/______

---

## Histórico de Versões

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 23/06/2026 | Versão inicial do template — sub-processor BR (Evolution API), base legal art. 7º II (obrigação legal) + art. 7º V (execução de contrato). 15 cláusulas simplificadas (sem跨境, sem SCC, retenção regida por Provimento CNJ 74/2018). Pendente negociação com provedor Evolution + revisão jurídica externa. | Rein `cartorio-lgpd` (sessão `mvs_d4fa1b1a154149dfb0bbadbb117ad1c1`) |

## Cross-References

- `docs/lgpd/dpa_deepseek_template.md` — DPA principal (sub-processor China)
- `docs/lgpd/dpa_opencode_go_template.md` — DPA gateway
- `docs/ripd.md` v1.4 — Tratamento 1 (atendimento chatbot) + Tratamento 4 (logs)
- `docs/consent.md` v1.1 — Item 3 (compartilhamento com Evolution)
- `docs/privacy-policy.md` v1.1 — Seção 5 (compartilhamento)
- `infra/evolution-api-integration.md` — Documentação técnica da integração

Modified by Gustavo Almeida (via cartorio-lgpd)
