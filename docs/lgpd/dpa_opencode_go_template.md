<!-- Modified by Gustavo Almeida (via cartorio-lgpd) -->

# Template de Data Processing Agreement (DPA) — OpenCode-Go (Gateway)

**Versão:** 1.0 (template)
**Data:** 23 de junho de 2026
**Status:** **MODELO PARA NEGOCIAÇÃO JURÍDICA** — sem assinatura
**Sub-processor primário:** **DeepSeek** (China) — DPA principal em `docs/lgpd/dpa_deepseek_template.md`
**Função do OpenCode-Go:** Gateway técnico de API (compat OpenAI Chat Completions) que roteia inferência para DeepSeek

> **ATENÇÃO:** Este template é específico para o **OpenCode-Go como gateway técnico**. O sub-processor primário (quem de fato processa os dados) é a **DeepSeek** (China), e o DPA principal está em `dpa_deepseek_template.md`. Este template cobre apenas os aspectos técnicos do gateway — autenticação, roteamento, logs de SLA, billing — que **NÃO** envolvem armazenamento ou processamento de conteúdo de mensagens.

---

## Contexto Diferencial

Diferentemente da DeepSeek (que efetivamente processa o conteúdo das mensagens), o **OpenCode-Go atua como gateway de rede** com as seguintes características:

1. **NÃO persiste** conteúdo de mensagens — apenas metadados de billing/SLA (tokens consumidos, latência, modelo, timestamp, request_id).
2. **NÃO treina modelos** com os dados roteados — repasse puro.
3. **Tunela** as requisições para o sub-processor primário (DeepSeek) sem inspeção de conteúdo.
4. **Autentica** o controlador via Bearer token e roteia para o modelo configurado (`deepseek-v4-flash`).

Por essas razões, este DPA é **mais simples** que o DPA da DeepSeek — não há armazenamento de PII, treinamento de modelo, ou transferência internacional adicional (a跨境 é feita pela DeepSeek, já coberta no DPA principal).

---

## Partes

**Controlador (Outorgante):**
- **Nome:** Cartório 2º Ofício de Notas de Uberlândia
- **CNPJ:** XX.XXX.XXX/0001-XX
- **Endereço:** Uberlândia/MG, Brasil
- **Representante legal:** `[NOME_DO_TABELIAO]`
- **Encarregado de Dados (DPO):** `[NOME_DO_DPO]` · dpo@2notasudi.com.br · `[TELEFONE_DO_DPO]`

**Operador (Outorgado) — Gateway:**
- **Nome:** OpenCode-Go (operado por `[OPERADOR_OPENCODE_GO]`)
- **Endereço:** `[A PREENCHER]`
- **Contato técnico:** `[A PREENCHER]`
- **Encarregado de Dados (DPO):** `[A PREENCHER]`

**Sub-processor primário (não-parte deste DPA, mas contratualmente vinculado):**
- **DeepSeek** — DPA principal: `docs/lgpd/dpa_deepseek_template.md`

---

## Cláusula 1ª — Objeto e Finalidade

1.1. O presente DPA tem por objeto regular a atuação da **OpenCode-Go como gateway técnico** de API (compat OpenAI Chat Completions), roteando requisições de inferência de modelos de linguagem do **Cartório 2º Ofício de Notas de Uberlândia** (controlador) para o sub-processor primário **DeepSeek**, sem armazenamento, inspeção ou modificação do conteúdo das mensagens.

1.2. **É vedado** à OpenCode-Go:
- (a) Inspecionar, registrar ou armazenar o conteúdo das mensagens roteadas;
- (b) Realizar qualquer forma de treinamento, fine-tuning ou improvement de modelos com os dados roteados;
- (c) Redirecionar requisições para sub-processadores não autorizados pelo controlador;
- (d) Compartilhar metadados de billing/SLA com terceiros sem autorização.

1.3. A OpenCode-Go limitar-se-á a:
- (a) Autenticar o controlador via Bearer token;
- (b) Roteamento para o sub-processor primário autorizado;
- (c) Coletar metadados de SLA/billing (tokens, latência, modelo, timestamp, request_id) **sem conteúdo**;
- (d) Disponibilizar painel de monitoramento de uso ao controlador.

---

## Cláusula 2ª — Base Legal

2.1. O tratamento de metadados realizado pela OpenCode-Go fundamenta-se em:
- **LGPD art. 7º, V** — execução de contrato (prestação do serviço de gateway contratado pelo controlador);
- **LGPD art. 7º, VI** — interesse público (operação do chatbot do cartório).

2.2. **Não há transferência internacional de dados pessoais** pela OpenCode-Go, pois o conteúdo das mensagens **não** é processado nem armazenado pelo gateway — apenas roteado. A transferência internacional é de responsabilidade do sub-processor primário (DeepSeek), coberta pelo DPA principal.

---

## Cláusula 3ª — Tipos de Dados Tratados

3.1. **Única e exclusivamente metadados de SLA/billing** (NÃO conteúdo de mensagens):
- Tokens consumidos (input e output);
- Latência da requisição;
- Modelo utilizado (`deepseek-v4-flash` ou outro autorizado);
- Timestamp da requisição (granularidade de segundo);
- Request ID (para correlação com logs do controlador);
- **Nenhum conteúdo de mensagem, PII ou dado pessoal é tratado pela OpenCode-Go**.

3.2. **Vedação absoluta:** a OpenCode-Go NÃO terá acesso a:
- Conteúdo de mensagens (texto, áudio, imagem);
- Identificadores do titular (telefone, e-mail, nome, CPF, etc);
- Contexto da conversa;
- Hash do cliente.

3.3. **Categorias de titulares:** não aplicável — não há tratamento de dados pessoais pelo gateway.

---

## Cláusula 4ª — Duração e Retenção

4.1. Os metadados de SLA/billing serão retidos pela OpenCode-Go por **90 dias** para fins de billing e suporte técnico.

4.2. Após 90 dias, os metadados serão **anonimizados** (remoção de request_id correlacionável) ou **eliminados**.

4.3. Logs de auditoria da OpenCode-Go (quem acessou o painel, quando) serão retidos por **5 anos** (LGPD art. 37 + Provimento CNJ 74/2018).

---

## Cláusula 5ª — Obrigações do Operador (LGPD art. 39)

A OpenCode-Go obriga-se a:

5.1. **NÃO inspecionar, registrar ou armazenar** o conteúdo de mensagens roteadas (Cláusula 3.2).

5.2. Roteamento **exclusivo** para sub-processadores autorizados — atualmente apenas DeepSeek (Cláusula 1.3.c).

5.3. Implementar **medidas técnicas de segurança**:
- Criptografia TLS 1.3 em trânsito;
- Autenticação de controlador via Bearer token rotacionado trimestralmente;
- Logs de acesso imutáveis (append-only) ao painel;
- Plano de resposta a incidentes com equipe técnica de plantão.

5.4. **Disponibilizar painel** ao controlador com: (a) estatísticas de uso (tokens/dia, latência média, taxa de erro), (b) lista de sub-processadores ativos, (c) histórico de incidentes.

5.5. **Notificar** o controlador em até **24 horas** de qualquer incidente que afete a disponibilidade, integridade ou confidencialidade do serviço — mesmo que não envolva dados pessoais (princípio da precaução).

5.6. **Cooperar** com o controlador e com o sub-processor primário (DeepSeek) em caso de investigação de incidente.

5.7. **Sub-processor disclosure:** manter lista atualizada de sub-processadores (atualmente apenas DeepSeek) e comunicar mudanças com 30 dias de antecedência.

5.8. **Conformidade com o DPA principal:** ao rotear para o sub-processor primário, garantir que as medidas de segurança (PII scrubbing em 3 camadas, conforme `backend/app/services/pii.py`) **NÃO** sejam removidas ou desabilitadas pelo gateway.

---

## Cláusula 6ª — Confidentialidade

6.1. A OpenCode-Go manterá **sigilo absoluto** sobre os metadados tratados, sobre a configuração do controlador e sobre a identidade dos titulares (ainda que não tenha acesso direto a eles).

6.2. O dever de sigilo subsiste por **5 anos** após o término do contrato.

---

## Cláusula 7ª — Notificação de Incidentes

7.1. A OpenCode-Go notificará o controlador em **≤ 24 horas** de qualquer:
- (a) Incidente de segurança que afete metadados de SLA/billing (incluindo tentativas de acesso não autorizado);
- (b) Indisponibilidade do gateway por mais de 1 hora;
- (c) Mudança não-autorizada de sub-processor;
- (d) Comprometimento de credenciais (Bearer token, API keys).

7.2. Notificação de incidente seguirá o mesmo formato do DPA principal (Cláusula 7ª de `dpa_deepseek_template.md`).

---

## Cláusula 8ª — Sub-processadores

8.1. **Sub-processor atual:** DeepSeek (China), vinculado ao DPA principal `dpa_deepseek_template.md`.

8.2. **Novos sub-processadores** exigirão notificação prévia de 30 dias e autorização do controlador. Sub-processadores adicionais **NÃO** serão roteados sem aprovação.

8.3. A OpenCode-Go manterá **lista pública atualizada** de sub-processadores em sua documentação oficial, com data de vigência de cada um.

---

## Cláusula 9ª — Direitos do Titular (LGPD art. 18)

9.1. **A OpenCode-Go NÃO trata dados pessoais**, portanto a maioria dos direitos do titular não se aplica diretamente.

9.2. Quando o controlador solicitar informações sobre o tratamento de metadados (que são pseudonimizados), a OpenCode-Go responderá em até **5 dias úteis**.

9.3. Em caso de investigação da ANPD ou do controlador, a OpenCode-Go disponibilizará logs de auditoria e metadados pertinentes.

---

## Cláusula 10ª — Auditoria

10.1. A OpenCode-Go disponibilizará **anualmente** relatório de:
- (a) Conformidade com este DPA;
- (b) Estatísticas de uso e SLA;
- (c) Lista de sub-processadores ativos;
- (d) Histórico de incidentes.

10.2. O controlador poderá, mediante notificação de 30 dias, realizar **auditoria presencial** ou contratar auditor independente.

10.3. A OpenCode-Go manterá **certificação ISO 27001** ou equivalente durante toda a vigência do DPA.

---

## Cláusula 11ª — Devolução ou Eliminação de Dados

11.1. Ao término do DPA, a OpenCode-Go **eliminará** todos os metadados de SLA/billing em até **30 dias**, com **certificado de eliminação** assinado por representante legal.

11.2. Logs de auditoria da OpenCode-Go serão mantidos por **5 anos** para fins de prova de cumprimento contratual (Cláusula 4.3).

11.3. **Não há dados pessoais a devolver** — apenas metadados pseudonimizados.

---

## Cláusula 12ª — Responsabilidade

12.1. A OpenCode-Go responde por danos causados por:
- (a) Roteamento para sub-processor não autorizado;
- (b) Quebra de sigilo sobre metadados;
- (c) Indisponibilidade prolongada do serviço (SLA não cumprido);
- (d) Inspecionar/armazenar conteúdo de mensagens (quebra de vedação Cláusula 1.2.a).

12.2. **Limite de responsabilidade** (a negociar com jurídico):
- (a) Até o valor total pago pelo controlador nos 12 meses imediatamente anteriores;
- (b) Sem limite em caso de dolo ou culpa grave.

12.3. Em qualquer caso, sem prejuízo de:
- Multas administrativas da ANPD (até 2% do faturamento, limitado a R$ 50M por infração);
- Indenização aos titulares por danos morais e materiais.

12.4. A OpenCode-Go manterá **seguro de RC** com cobertura mínima de **R$ 2.000.000,00**.

---

## Cláusula 13ª — Rescisão e Sanções

13.1. **Causas de rescisão imediata** pelo controlador:
- (a) Descumprimento material deste DPA;
- (b) Quebra de sigilo;
- (c) Roteamento para sub-processor não autorizado;
- (d) Inspecionar/armazenar conteúdo de mensagens;
- (e) Perda de certificação ISO 27001 ou equivalente;
- (f) Recusa em auditoria.

13.2. **Notificação prévia** de 30 dias para rescisão por conveniência.

13.3. Em caso de rescisão, aplicam-se Cláusulas 11ª (eliminação) e 12ª (responsabilidade).

---

## Cláusula 14ª — Lei Aplicável e Foro

14.1. Este DPA é regido pela **lei brasileira** (LGPD Lei 13.709/2018), com aplicação subsidiária do Código Civil.

14.2. Fica eleito o **foro da Comarca de Uberlândia, Estado de Minas Gerais**, Brasil, com renúncia a qualquer outro.

---

## Cláusula 15ª — Disposições Finais

15.1. Este DPA entra em vigor na data de sua assinatura e vigorará por **prazo indeterminado**, enquanto perdurar a relação entre controlador e gateway.

15.2. Alterações exigirão **termo aditivo escrito** assinado por ambas as partes.

15.3. As partes declaram ter lido e compreendido todas as cláusulas, em especial a gravidade das sanções da LGPD.

15.4. Este DPA é **complementar e subordinado** ao DPA principal com a DeepSeek (`dpa_deepseek_template.md`). Em caso de conflito, prevalece o DPA principal para aspectos relacionados ao tratamento de conteúdo de mensagens; este DPA prevalece para aspectos técnicos de gateway.

---

## Assinaturas

**Pelo Controlador (Cartório 2º Ofício de Notas de Uberlândia):**

- Tabelião(a) titular: `[NOME_DO_TABELIAO]` — Assinatura: ___________________ Data: ___/___/______
- Encarregado de Dados (DPO): `[NOME_DO_DPO]` — Assinatura: ___________________ Data: ___/___/______

**Pela Operadora Gateway (OpenCode-Go):**

- Representante legal: `[NOME_DO_REP]` — Cargo: `[CARGO]` — Assinatura: ___________________ Data: ___/___/______
- Encarregado de Dados (DPO): `[NOME_DO_DPO_OPENCODE]` — Assinatura: ___________________ Data: ___/___/______

---

## Histórico de Versões

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 23/06/2026 | Versão inicial do template — gateway técnico OpenCode-Go, complementar ao DPA principal DeepSeek. 15 cláusulas reduzidas (sem armazenamento de PII, sem treinamento, sem跨境). Pendente negociação com OpenCode-Go + revisão jurídica externa. | Rein `cartorio-lgpd` (sessão `mvs_d4fa1b1a154149dfb0bbadbb117ad1c1`) |

## Cross-References

- `docs/lgpd/dpa_deepseek_template.md` — DPA principal (sub-processor primário)
- `docs/ripd.md` v1.4 — Tratamento 7 (OpenCode-Go / DeepSeek)
- `docs/consent.md` v1.1 — Item 3 (compartilhamento)
- `docs/privacy-policy.md` v1.1 — Seção 9 (transferência internacional)
- `backend/app/integrations/opencode_go.py` — Implementação técnica

Modified by Gustavo Almeida (via cartorio-lgpd)
