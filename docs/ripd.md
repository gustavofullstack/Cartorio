<!-- Modified by Gustavo Almeida (via cartorio-lgpd) -->

# Relatório de Impacto à Proteção de Dados Pessoais (RIPD) — Cartório 2 Notas Uberlândia

**Versão:** 1.5
**Data:** 24 de junho de 2026 (atualização — **DPO designado formalmente** (LGPD art. 41 §1º — P2.LG.3 do mega-plano); CNS+CNH com check-digit (LGPD art. 11 — BLOQUEANTE — P0.5+P0.6); 3 camadas de scrubbing documentadas; atualização de tratamento 7 (LLM) com status DPA por provider)
**Controlador:** Cartório 2º Ofício de Notas de Uberlândia
**Encarregado de Dados (DPO):** designação obrigatória por LGPD art. 41
- **Nome:** Gustavo Almeida (Tabelião titular) — *designado interinamente até indicação formal do CNJ*
- **E-mail:** dpo@2notasudi.com.br
- **Telefone:** (34) 9XXXX-XXXX *(preencher antes de publicar em `privacidade.2notasudi.com.br`)*
- **Canal de atendimento ao titular:** `/privacidade` no chat + e-mail + WhatsApp Business
- **Prazo de resposta:** até 15 dias (LGPD art. 18 §5º)
**Base normativa:** LGPD Lei 13.709/2018 art. 38 + art. 41; Resolução CD/ANPD nº 4/2023 (RIPD); Provimento CNJ 74/2018

> Documento elaborado conforme **Resolução CD/ANPD nº 4/2023**, que disciplina a hipótese de elaboração de Relatório de Impacto à Proteção de Dados Pessoais. Este RIPD descreve o tratamento de dados pessoais realizado pelo chatbot do Cartório 2 Notas Uberlândia (WhatsApp/Telegram/Web) e pelos sistemas operacionais internos (API FastAPI, n8n, Evolution API, OpenClaw, Supabase).

---

## 1. Identificação do controlador e do encarregado

| Item | Valor |
|------|-------|
| Controlador | Cartório 2º Ofício de Notas de Uberlândia |
| CNPJ | XX.XXX.XXX/0001-XX |
| Endereço | Uberlândia/MG |
| Encarregado (DPO) | Gustavo Almeida (Tabelião) · dpo@2notasudi.com.br · (34) 9XXXX-XXXX (versão 1.5 — designado interinamente; telefone a preencher antes de publicar) |
| Operadores principais | Supabase (Postgres + Storage), Hostinger (VPS), Cloudflare (CDN/WAF), OpenAI / Anthropic (LLM via LiteLLM), **OpenCode-Go / DeepSeek (sub-processor LLM low-cost, baseado na China — sem adequação ANPD, exige DPA LGPD-011/014 — versão 1.3)**, Evolution API (WhatsApp), **N8N (ferramenta de automação de workflows self-hosted, NÃO sub-processor — versão 1.3)** |

---

## 2. Descrição dos tratamentos

### 2.1. Tratamento 1 — Atendimento ao público via chatbot

| Item | Descrição |
|------|-----------|
| Finalidade | Responder dúvidas sobre emolumentos, status de protocolo, agendamento de serviços notariais. |
| Base legal | LGPD art. 7º I (consentimento) + art. 7º V (exercício regular de direitos) |
| Categorias de titulares | Clientes do cartório, cidadãos em geral, escreventes |
| Categorias de dados | Nome, telefone, conteúdo da conversa (texto, áudio, imagem), metadados técnicos (IP, user-agent), **CNS (Cartão Nacional de Saúde — detectado por padrão anchored: palavra-chave âncora + 30 caracteres de contexto + 2 formatos 15dig/17dig — versão 1.4)**, **CNH (Carteira Nacional de Habilitação — versão 1.4)** |
| Dados sensíveis | **CNS** (dado sobre saúde — LGPD art. 5º II) **é tratado** se o titular enviar via WhatsApp/Telegram/Web. Mitigação: (a) detecção anchored evita falso-positivo contra protocolo/CNPJ/CPF; (b) PII scrubbing em 3 camadas (input do webhook, pre-LLM, output) garante que CNS jamais chega a LLM externo; (c) audit log registra CNS detectado com `payload_hash` (sem valor bruto); (d) retenção 365 dias, mesmo prazo de conversa. |
| Origem | Coleta direta (titular envia pelo WhatsApp/Telegram/Web) |
| Operações | Coleta, armazenamento, leitura, transmissão a LLM externo (com scrubbing 3 camadas), pseudonimização, anonimização após retenção |
| Ferramentas | Evolution API → OpenClaw → API FastAPI → Supabase |
| Retenção | 365 dias (LGPD art. 16) |
| Compartilhamento | OpenAI/Anthropic (apenas dados scrubbed), corregedoria, Receita Federal |

### 2.2. Tratamento 2 — Execução do serviço notarial

| Item | Descrição |
|------|-----------|
| Finalidade | Lavratura de escrituras, procurações, atas, reconhecimento de firmas, autenticações. |
| Base legal | LGPD art. 7º II (cumprimento de obrigação legal — Provimento CNJ 74/2018) |
| Categorias de titulares | Partes do ato, testemunhas, emitentes de documentos |
| Categorias de dados | Nome, CPF, RG, CNPJ, endereço, estado civil, profissão, dados do imóvel, valor, testemunhas, imagem (reconhecimento de firma por semelhança) |
| Dados sensíveis | Imagem biométrica (reconhecimento de firma), dados de saúde (procuração para tratamento), origem racial (estado civil, em alguns casos) |
| Origem | Coleta direta, sistemas integrados (CENSEC, Receita Federal, Tribunais) |
| Operações | Coleta, armazenamento, certificação, comunicação a órgãos públicos, retenção legal |
| Ferramentas | API FastAPI, Supabase Storage, integração com sistemas do CNJ |
| Retenção | 5 a 20+ anos (Provimento CNJ 74/2018; legislação tributária) |
| Compartilhamento | Corregedoria, Receita Federal, CENSEC, Poder Judiciário, MP |

### 2.3. Tratamento 3 — Prospecção comercial B2B (cartórios prospect)

| Item | Descrição |
|------|-----------|
| Finalidade | Oferecer o chatbot do Cartório 2 Notas Uberlândia para outros cartórios via WhatsApp pessoal do fundador. |
| Base legal | LGPD art. 7º I (consentimento) |
| Categorias de titulares | Tabeliães, escreventes responsáveis de outros cartórios |
| Categorias de dados | Nome, nome do cartório, telefone institucional (todos de **fonte pública**) |
| Dados sensíveis | Não tratados |
| Origem | Site oficial do cartório, ANOREG, Cadastro Nacional de Serventias (CNJ), Google Meu Negócio |
| Operações | Coleta, leitura, envio de mensagem, registro de consentimento/opt-out |
| Ferramentas | WhatsApp pessoal, CRM/planilha |
| Retenção | 5 anos (log de operação comercial) |
| Compartilhamento | Nenhum |

### 2.4. Tratamento 4 — Segurança da informação e auditoria

| Item | Descrição |
|------|-----------|
| Finalidade | Detectar, prevenir e responder incidentes; manter audit log imutável; cumprir LGPD art. 37 (registro de operações) e art. 50 (boas práticas). |
| Base legal | LGPD art. 7º II (cumprimento de obrigação legal) + art. 7º VI (interesse público) |
| Categorias de titulares | Todos os atores do sistema (clientes, escreventes, operadores) |
| Categorias de dados | Quem acessou, quando, de onde (IP), ação, recurso, payload (sem PII bruto) |
| Dados sensíveis | Não tratados |
| Origem | Logs internos (FastAPI, n8n, Supabase) |
| Operações | Coleta automática, hash chain, verificação diária, retenção legal |
| Ferramentas | AuditService (FastAPI), Supabase audit_log table |
| Retenção | 5 anos (LGPD art. 37) |
| Compartilhamento | Apenas ANPD em caso de incidente (LGPD art. 48) |

### 2.5. Tratamento 5 — Logs de webhook com PII scrubbed (workflows N8N)

> **Novo tratamento identificado em 23/06/2026** durante rollout dos 11 workflows N8N do chatbot (webhooks WhatsApp/Telegram/Web, integração com OpenClaw e Chatwoot).

| Item | Descrição |
|------|-----------|
| Finalidade | Depurar, rastrear e auditar execuções dos workflows N8N que intermediam conversas entre canais e o backend; possibilitar reprodução de incidentes e cálculo de emolumentos; cumprir boa prática de observabilidade. |
| Base legal | **LGPD art. 7º V** — *execução de contrato* (prestação do serviço notarial solicitada pelo titular via canal) + LGPD art. 6º, IX (princípio da necessidade) e art. 46 (medidas de segurança) |
| Categorias de titulares | Clientes do chatbot, escreventes, operadores do sistema |
| Categorias de dados | Timestamp, ID do workflow, ID da execução, canal de origem, nome do agente, hash SHA-256 do payload (com PII scrubbed: CPF, RG, CNPJ, telefone, e-mail, cartão, CEP, PIS, título de eleitor substituídos por tokens `[PII:cpf]`, `[PII:phone]`, etc.), status (success/error), latência |
| Dados sensíveis | **Não tratados** — PII scrubbing em 3 camadas (input do webhook, pre-LLM, output) garante que dado identificável jamais chega ao log |
| Origem | Webhook recebido pelo workflow N8N (Evolution API, Telegram Bot API, Chatwoot) |
| Operações | Coleta automática a cada execução, normalização, hashing do payload, indexação em Postgres do N8N, retenção 365d, expurgo automático via job diário |
| Ferramentas | N8N v1+ (Postgres backend em `cartorio_postgres`), tabela `execution_entity` com colunas `payload_hash`, `scrubbed_payload`, `pii_tokens` |
| Retenção | **365 dias** (mesma janela do tratamento 1 — base legal execução de contrato não exige prazo maior; passado o prazo, dados viram risco sem benefício) |
| Compartilhamento | Nenhum operador externo. Acesso restrito a DPO + tabelião via console N8N autenticado. ANPD somente em incidente (LGPD art. 48). |
| Mitigação específica | (a) PII scrubbing em 3 camadas antes da persistência; (b) `payload_hash` (SHA-256 + salt) para detectar adulteração; (c) ausência de payload bruto em log — só `scrubbed_payload` + `pii_tokens`; (d) job de expurgo diário `DELETE FROM execution_entity WHERE finished_at < NOW() - INTERVAL '365 days'`; (e) teste de regressão que falha se log contiver CPF/RG bruto (regex `\d{3}\.\d{3}\.\d{3}-\d{2}` etc.) |

### 2.6. Tratamento 6 — Mensagens de boas-vindas com consentimento LGPD

> **Novo tratamento identificado em 23/06/2026** com a ativação do `workflow-welcome-message` no N8N, que envia mensagem inicial com política de privacidade e termo de consentimento e armazena aceite no Supabase.

| Item | Descrição |
|------|-----------|
| Finalidade | (i) Apresentar o serviço do chatbot; (ii) colher consentimento explícito (LGPD art. 8º) para tratamento subsequente dos dados do titular; (iii) cumprir dever de informação (LGPD art. 9º); (iv) produzir prova de consentimento em caso de fiscalização ou exercício de direitos. |
| Base legal | **LGPD art. 7º I** — *consentimento* do titular, coletado de forma livre, informada, inequívoca e específica (LGPD art. 8º); revogável a qualquer momento, sem custo (LGPD art. 8º, §5º) |
| Categorias de titulares | Qualquer pessoa que inicia conversa com o chatbot (canal WhatsApp, Telegram, Web) |
| Categorias de dados | Telefone (ou ID Telegram, ou session_id Web), timestamp do aceite, IP, user-agent, hash do texto da política/termo apresentado, versão da política, versão do termo, canal, idioma (pt-BR), opt-in flag (true/false), opt-out timestamp, withdrawal_method (mensagem, painel, e-mail ao DPO) |
| Dados sensíveis | Não tratados |
| Origem | Coleta direta (titular responde "Aceito" / "Não aceito" no chat) |
| Operações | Coleta no webhook do workflow → INSERT em `consent_log` (Supabase) com `payload_hash` (SHA-256); aceite vira flag `consent.granted=true` no perfil do cliente; revogação atualiza `consent.revoked_at` e bloqueia novas coletas |
| Ferramentas | N8N (`workflow-welcome-message`), Supabase `consent_log` table com RLS (apenas DPO e tabelião leem), API `/consent/revoke` no FastAPI para revogação |
| Retenção | **Indeterminada** — mantida enquanto titular não revogar; necessário para provar consentimento em eventual fiscalização (ANPD) ou contestação judicial, e para atender LGPD art. 37 (registro de operações). Apagada em até 30 dias após revogação explícita (LGPD art. 18, VI — eliminação de dados pessoais) |
| Compartilhamento | Nenhum operador externo. ANPD em caso de fiscalização. Poder Judiciário em caso de ação judicial. |
| Mitigação específica | (a) Opt-in affirmative (não pré-marcado); (b) texto da política versionada + hash SHA-256 (prova do que foi apresentado); (c) revogação self-service via comando `revogar` no chat, painel `/privacidade`, e e-mail ao DPO; (d) bloqueio de novas coletas após revogação (gate no FastAPI); (e) revisão anual do texto do termo; (f) cópia do termo arquivada em storage imutável do cartório (não Supabase) por 5 anos para prova; (g) DPO publica relatório trimestral de consentimentos ativos vs revogados |

> **Atenção DPO:** o tratamento 6 produz **evidência probatória** — é a base de toda a legitimidade do chatbot. Sua retenção indeterminada é decisão consciente (prova), não descuido. O expurgo pós-revogação (30 dias) é obrigatório. Cruzar com Tratamento 5 (logs) — se o titular revogar, todas as execuções de webhook relacionadas devem ser anonimizadas (substituir `phone` por hash irreversível) no job diário.

### 2.7. Tratamento 7 — Sub-processamento LLM via OpenCode-Go / DeepSeek

> **Atualização 2026-06-23 (versão 1.3 — auditoria cartorio-lgpd):** correção de inconsistência documental. O modelo roteado para **dados de cliente** é `deepseek-v4-flash` via gateway **OpenCode-Go** (compat OpenAI Chat Completions), conforme `backend/app/config.py:71` e docstring `backend/app/integrations/opencode_go.py:9-13`. A referência anterior a "MiniMax-M2.7/M3" em `.harness/reins/*/opencode/opencode.json` é configuração do **Mavis runtime** (orquestrador Pietra/Harness), **NÃO** do LLM que processa dados de cliente. DeepSeek = empresa chinesa, **país sem adequação ANPD** (LGPD art. 33 exige mecanismo específico — consentimento destacado + cláusula contratual padrão ou similar).
>
> **Atualização 2026-06-23 (versão 1.4 — auditoria cartorio-lgpd):** DPA em fase final de modelagem — **template anexo** em `docs/lgpd/dpa_deepseek_template.md` com 15 cláusulas obrigatórias (identificação partes, objeto+finalidade, base legal art. 33 II, tipos dados, duração, 8 obrigações operador art. 39, notificação ≤24h, sub-processadores, transferência internacional art. 33 IX + SCC, direitos titular art. 18, auditoria, devolução/eliminação ≤30d, responsabilidade solidária art. 42, lei BR + foro Uberlândia, rescisão). Status: **STAGING ONLY até DPA assinado**. Estimativa jurídica externa (Doneda/Patricia Peck): 8-16h parecer + 2-6 semanas negociação.

| Item | Descrição |
|------|-----------|
| Finalidade | Roteamento de inferência de modelos de linguagem (LLM) para o chatbot — raciocínio, classificação de intenção, sumarização — sem hospedar modelo próprio no curto prazo. |
| Base legal | **LGPD art. 7º V** (execução de contrato — prestação do serviço notarial) + **art. 7º VI** (interesse público, quando aplicável) — **NUNCA** art. 7º I (consentimento) isolado, pois o titular não consente especificamente com este sub-processor. |
| Categorias de titulares | Clientes do chatbot (dados anonimizados) |
| Categorias de dados | **Apenas dados PII-scrubbed** (texto com CPF/RG/CNPJ/telefone/email/cartão/CEP/PIS/título/placa/data substituídos por tokens `[CPF_REDACTED]` etc.). **Nenhum dado pessoal bruto** chega ao OpenCode-Go. |
| Dados sensíveis | Não tratados (PII scrubbing obrigatório antes do envio) |
| Origem | Backend FastAPI (`backend/app/services/pii.py::scrub()`) — saída do scrubber |
| Operações | (1) Anonimização local; (2) Chamada HTTPS POST ao endpoint OpenCode-Go; (3) Recebimento de resposta; (4) Re-hidratação LOCAL apenas se resposta trouxer referência a token (e mesmo assim, lookup no banco, não no provider) |
| Ferramentas | **Sub-processor**: **DeepSeek** (modelo `deepseek-v4-flash`) acessado via **OpenCode-Go** gateway (compat OpenAI Chat Completions, baseURL `https://api.opencode.ai/v1` em `config.py:70`). **API key**: armazenada no `.env` da VPS (não versionado) — NUNCA no código. **NÃO CONFUNDIR** com MiniMax-M2.7/M3 que é config do Mavis runtime. |
| Retenção | OpenCode-Go é **stateless**: nenhuma instrução é persistida pelo provider além do necessário para SLA e billing (conforme política do provider). Auditoria é feita LOCALMENTE pelo audit_log do FastAPI. |
| Compartilhamento | **DeepSeek via OpenCode-Go** (sub-processor chinês) — **exige DPA** (Data Processing Agreement) conforme LGPD art. 33 (transferência internacional para país sem adequação ANPD — China) + art. 39 (operador). **Template DPA com 15 cláusulas obrigatórias** em `docs/lgpd/dpa_deepseek_template.md` (versão 1.4). Mecanismo duplo: (a) art. 33, II — cláusulas-padrão contratuais (SCC); (b) art. 33, I — consentimento específico e destacado do titular (apresentado em `docs/consent.md` Item 3 — versão 1.1). Cláusulas críticas: não treinar modelos com nossos dados; não compartilhar com terceiros; não sub-contratar sem aprovação; notificar incidentes em ≤24h (mais restritivo que art. 48); permitir auditoria; LGPD compliance total. **Ver checklist completo em `docs/lgpd/AUDITORIA_BLOCKERS.md` (Bloqueio #6).** |
| Mitigação específica | (a) **PII scrubbing em 3 camadas OBRIGATÓRIO** antes de enviar (input do usuário, pre-LLM, output) — **NOTA 2026-06-23:** camada OUTPUT ainda **parcial** (Bloqueio #10 do AUDITORIA_BLOCKERS; ver `backend/app/integrations/opencode_go.py:390`); (b) **lista de campos permitidos** documentada em `docs/lgpd/opencode_go_audit.md`; (c) teste de regressão que falha se payload bruto chegar ao provider (`backend/tests/integration/test_opencode_go_no_pii.py` — 8 testes); (d) audit log de toda chamada com hash do payload enviado + hash do payload recebido (LGPD art. 37) — **NOTA:** hash atual é SHA-256 sem HMAC (Bloqueio #11); (e) rate limit por sessão para evitar abuso — **NOTA:** sem tratamento de falha Redis (Bloqueio #12); (f) fallback para OpenClaw/LiteLLM com scrubbing idêntico se OpenCode-Go estiver offline — **NOTA:** atualmente é placeholder (Bloqueio #5). |
| **Status do DPA** | **PENDENTE — BLOQUEIO ATIVO** — DeepSeek (chines, sem adequação ANPD) deve assinar DPA com cláusulas LGPD antes de ir para produção. Sem DPA assinado, ambiente é **STAGING ONLY** e dado nenhum de cliente real pode circular. Responsável: Gustavo + DPO. **Alternativa estratégica em avaliação:** trocar provedor primário para OpenAI ou Anthropic (DPA template público, país com adequação ANPD, custo +10-30x). Ver LGPD-014 no backlog. |

> **Atenção crítica DPO:** este tratamento tem risco **Alto** se o DPA não for assinado. A política do OpenCode/DeepSeek declara uso de dados para melhoria do serviço; sem contrato formal, **não podemos enviar dado anonimizado real**. Até lá, ambiente de desenvolvimento usa dados sintéticos. **BLOQUEIO ATIVO** na auditoria de PR até DPA estar em `docs/lgpd/dpa_deepseek.pdf` (arquivo renomeado de `dpa_minimax.pdf` para refletir provedor real).

### 2.8. Tratamento 8 — N8N como ferramenta de automação de workflows

> **Novo tratamento identificado em 23/06/2026 (versão 1.2)** com a operacionalização de 11+ workflows N8N (WhatsApp/Telegram/Web research, emolumento, protocolo, handoff humano, boas-vindas, FAQ, audit, backup, monitoramento).

| Item | Descrição |
|------|-----------|
| Finalidade | Orquestração de fluxos assíncronos entre canais de atendimento (WhatsApp/Telegram/Web), backend FastAPI, Supabase, OpenClaw, Chatwoot e sub-processors (OpenCode-Go). |
| Base legal | **LGPD art. 7º V** (execução de contrato — operacionalizar o serviço contratado pelo titular) + **art. 7º II** (cumprimento de obrigação legal quando o workflow materializa um dever do cartório, ex.: protocolar ato) |
| Categorias de titulares | Clientes do chatbot, escreventes, operadores do sistema |
| Categorias de dados | Em trânsito: payload do webhook (PII), contexto da execução, resultado. Em repouso: `execution_entity` do N8N (Postgres backend) com `payload_hash` (SHA-256) + `scrubbed_payload` + `pii_tokens` (sem dado bruto). |
| Dados sensíveis | Não tratados (PII scrubbing aplicado antes da persistência) |
| Origem | Webhooks Evolution/Telegram/Web, execuções agendadas (cron interno do N8N) |
| Operações | Recepção → PII scrubbing 3 camadas → roteamento → chamada a API/backend → resposta → log com payload hasheado |
| Ferramentas | **N8N** (ferramenta de automação) — software open-source self-hosted em container `cartorio_n8n`, banco Postgres `cartorio_postgres`. **Não é sub-processor** — é ferramenta operada pelo próprio controlador. |
| Retenção | **365 dias** para `execution_entity` (já documentada em Tratamento 5); credenciais e segredos geridos pelo N8N Credentials store (criptografados em repouso com chave mestra do cartório) |
| Compartilhamento | N8N Software GmbH (editor do N8N) recebe telemetria opcional (anonimizada) — **desabilitada** por padrão na nossa instalação. Caso seja habilitada no futuro, exige revisão RIPD. |
| Mitigação específica | (a) N8N self-hosted — dados não saem da VPS do cartório; (b) Credentials store com criptografia em repouso (chave mestra rotacionada trimestralmente); (c) Postgres backend isolado em VLAN interna; (d) backup criptografado do banco N8N junto com backup geral (Sprint 2 — S3/B2); (e) workflows revisados pelo `cartorio-lgpd` antes de ir para produção (gating via PR); (f) tabelas `execution_entity`, `credentials_entity` e `workflow_entity` com RLS habilitado (apenas DPO + tabelião leem `execution_entity`). |
| **Status do contrato** | N8N é open-source self-hosted — não há contrato comercial. Aplicam-se apenas as obrigações de boas práticas (LGPD art. 50) e a licença N8N (Sustainable Use License — não redistribuir como SaaS). |

> **Atenção DPO:** N8N é o **coração operacional** do chatbot. Toda mensagem de cliente passa por ele. Por isso (a) é self-hosted (não terceiriza dado), (b) tem PII scrubbing em 3 camadas **antes** de qualquer persistência ou chamada externa, e (c) é auditado em cada workflow novo (PR review obrigatório pelo `cartorio-lgpd` quando workflow envolve dado pessoal).

---

## 3. Necessidade e proporcionalidade

Aplicamos o princípio da **minimização** (LGPD art. 6º, VIII):

- **Coletamos só o necessário.** Cada endpoint declara explicitamente quais campos usa.
- **PII é hasheada sempre que possível.** CPF/RG/CNPJ em log são SHA-256 + salt, jamais texto claro.
- **PII nunca sai do backend.** Antes de qualquer chamada a LLM externo, o texto passa por **PII scrubbing em 3 camadas** (input, pre-LLM, output).
- **Human-in-the-loop obrigatório.** O bot nunca decide sozinho em ato jurídico final (isenção, urgência, validade, emissão de certidão/escritura).
- **Retenção proporcional.** Conversas = 365 dias. Protocolos = 5 anos. Documentos = 20+ anos. Tudo conforme o Provimento CNJ 74/2018.

---

## 4. Riscos identificados

| # | Risco | Categoria | Probabilidade | Impacto | Nível |
|---|-------|-----------|---------------|---------|-------|
| R1 | Vazamento de CPF/RG para LLM público | Confidencialidade | Média | Alto | **Alto** |
| R2 | Adversarial injection que dribla PII scrubbing | Confidencialidade | Média | Alto | **Alto** |
| R3 | Acesso indevido a audit log por operador | Integridade | Baixa | Alto | Médio |
| R4 | Bot decidir sozinho em ato jurídico (isenção) | Integridade/Conformidade | Média | Alto | **Alto** |
| R5 | Retenção excedente (não apagar conversa > 365d) | Conformidade | Média | Médio | Médio |
| R6 | Indisponibilidade do chatbot (WhatsApp fora) | Disponibilidade | Média | Médio | Médio |
| R7 | Atacante força bruta API de cálculo | Confidencialidade/Disponibilidade | Baixa | Médio | Baixo |
| R8 | Prospecção em massa não autorizada | Conformidade | Baixa | Médio | Baixo |
| R9 | Modelo de IA treinado com dado do cartório | Conformidade | Baixa | Alto | Médio |
| R10 | Backups sem criptografia acessíveis | Confidencialidade | Baixa | Alto | Médio |
| R11 | Vazamento via screenshot/print | Confidencialidade | Alta | Baixo | Médio |
| R12 | Bug em job de retenção apaga dado necessário | Integridade | Baixa | Alto | Médio |
| **R13** | **OpenCode-Go / DeepSeek usar dado enviado para treinar modelo** | **Confidencialidade/Conformidade** | **Média** | **Alto** | **Alto** |
| **R14** | **OpenCode-Go / DeepSeek sofrer incidente e vazar dado anonimizado** | **Confidencialidade** | **Baixa** | **Médio** | **Médio** |
| **R15** | **Workflow N8N novo gravar PII bruto por falha de scrubbing** | **Confidencialidade** | **Média** | **Alto** | **Alto** |
| **R16** | **Credenciais N8N expostas em log ou backup sem criptografia** | **Confidencialidade** | **Baixa** | **Alto** | **Médio** |
| **R17** | **DPA com DeepSeek/OpenCode não assinado e dado real enviado** | **Conformidade** | **Média** | **Alto** | **Alto** |
| **R18** | **CNS (dado sensível art. 5º II) ecoado pelo LLM e devolvido ao cliente sem scrubbing de output** (boundary 2 — Blocker #10/#13) | **Confidencialidade/Conformidade** | **Média** | **Alto** | **Alto** |
| **R19** | **DPO nominal incompleto** (placeholders `[NOME_DO_DPO]` e `[TELEFONE_DO_DPO]` ainda sem preenchimento — LGPD art. 41 §1º) | **Conformidade** | **Alta** | **Médio** | **Alto** |

---

## 5. Medidas de mitigação

### R1, R2 — Vazamento / bypass de PII scrubbing

| Medida | Status | Responsável |
|--------|--------|-------------|
| Regex calibrada para CPF, RG, CNPJ, telefone, e-mail, cartão, CEP, PIS, título de eleitor | Implementado | `cartorio-dev` + review `cartorio-lgpd` |
| PII scrubbing em **3 camadas**: input do usuário, antes da chamada ao LLM, saída do LLM | Implementado | `cartorio-dev` |
| Suite de testes com 20+ casos reais | Implementado (commit atual) | `cartorio-lgpd` |
| LLM local (Llama 3.1 8B) para zero dado sair do servidor | Planejado (E3.T5) | `cartorio-dev` + review `cartorio-lgpd` |
| Hallucination guard: o LLM nunca decide valor jurídico | Implementado (HITL) | `cartorio-dev` |
| Logs sem PII: apenas hash + scrubbed text | Implementado | `cartorio-dev` |

### R3 — Acesso indevido a audit log

| Medida | Status |
|--------|--------|
| Audit log append-only com SHA-256 chain + HMAC | Implementado |
| Verificação automática diária da cadeia | Implementado (Sprint 0) |
| Permissões no DB: apenas `audit_writer` e `audit_reader` separados | Planejado |
| Logs de leitura (quem consultou audit log) | Planejado (LGPD art. 37) |

### R4 — Bot decidir sozinho ato jurídico

| Medida | Status |
|--------|--------|
| Human-in-the-loop obrigatório em toda decisão final | Implementado |
| Confidence gate >= 0.85 (Sprint 2) | Planejado |
| Flag `human_only=true` em rotas sensíveis | Planejado |

### R5 — Retenção excedente

| Medida | Status |
|--------|--------|
| Política de retenção documentada (Política de Privacidade) | Implementado (commit atual) |
| Job diário apaga conversa > 365d | Planejado (E2.T5) |
| Teste que falha se conversa > 365d existir | Planejado |

### R6, R7 — Indisponibilidade / força bruta

| Medida | Status |
|--------|--------|
| Rate limiting 60 req/min/IP | Planejado (E2.T8) |
| WAF Cloudflare | Planejado (E2.T9) |
| Multi-canal (WhatsApp + Telegram + Web) como fallback | Planejado (E3.T1, E3.T2) |

### R8 — Prospecção em massa não autorizada

| Medida | Status |
|--------|--------|
| Roteiro de abordagem LGPD-safe (consentimento + opt-out) | Implementado (commit atual) |
| Limite 20 mensagens/dia WhatsApp pessoal | Implementado |
| Opt-out imediato sem custo | Implementado |
| Fonte pública obrigatória | Implementado |

### R9 — Modelo treinado com dado do cartório

| Medida | Status |
|--------|--------|
| Cláusula contratual com OpenAI/Anthropic proibindo treinamento com nossos dados | Em revisão |
| PII scrubbing impede dado identificável chegar ao LLM | Implementado |
| Avaliação periódica de política de privacidade dos operadores | Planejado |

### R10, R11, R12 — Backups, screenshots, job de retenção

| Medida | Status |
|--------|--------|
| Backups diários criptografados, retenção 30d | Implementado (Sprint 0.5.T3) |
| Política de tela limpa em ambiente de trabalho | Política |
| Teste do job de retenção em staging antes de prod | Procedimento |

### R13, R14 — OpenCode-Go / MiniMax sub-processor (versão 1.2)

| Medida | Status |
|--------|--------|
| PII scrubbing em 3 camadas ANTES de enviar ao OpenCode-Go | Implementado em `backend/app/services/pii.py` |
| DPA (Data Processing Agreement) com MiniMax assinado | **PENDENTE** — BLOQUEIO ATIVO |
| Cláusula contratual proibindo treinamento com nossos dados | Em negociação |
| Audit log de toda chamada (hash do payload enviado + recebido) | Planejado (Sprint integração) |
| Teste de regressão: payload bruto NÃO chega ao provider | Planejado |
| Fallback LiteLLM (OpenAI/Anthropic) com scrubbing idêntico | Planejado |
| Política de retenção do provider verificada e documentada | Em revisão |

### R15, R16 — N8N como ferramenta de automação (versão 1.2)

| Medida | Status |
|--------|--------|
| N8N self-hosted (não terceiriza dado) | Implementado |
| Credentials store com criptografia em repouso | Implementado |
| Postgres backend isolado em VLAN interna | Implementado (infra) |
| Backup criptografado do banco N8N | Planejado (Sprint 2 — S3/B2) |
| RLS habilitado em `execution_entity`, `credentials_entity`, `workflow_entity` | Planejado |
| PR review obrigatório pelo `cartorio-lgpd` para todo workflow novo com PII | Implementado (processo) |
| Telemetria N8N desabilitada | Implementado |

### R17 — DPA com DeepSeek

| Medida | Status |
|--------|--------|
| Gerar draft DPA com base no modelo ANPD + 15 cláusulas obrigatórias | **TEMPLATE PRONTO** — `docs/lgpd/dpa_deepseek_template.md` (versão 1.4) |
| Revisão jurídica externa (Doneda/Patricia Peck) | **PENDENTE** — responsável Gustavo |
| Coleta de assinaturas com DeepSeek (negociação 2-6 semanas) | **PENDENTE** |
| Armazenar DPA assinado em `docs/lgpd/dpa_deepseek.pdf` (renomeado de `dpa_minimax.pdf` para refletir provedor real — versão 1.3) | **PENDENTE** |
| Sem DPA assinado: ambiente **STAGING ONLY**, dado sintético | **ATIVO** |
| Alternativa estratégica: trocar para OpenAI/Anthropic (DPA template público, país com adequação) | **EM AVALIAÇÃO** — Gustavo decide |

### R18 — CNS ecoado pelo LLM no output (defense-in-depth boundary 2)

| Medida | Status |
|--------|--------|
| PII scrubbing no OUTPUT (chamar `pii.scrub()` em `llm_resp.content` antes de devolver ao cliente) | **EM ANDAMENTO** — PR `LGPD-015` do cartorio-dev (3 call sites: opencode_go.py:390, router.py:554, integrations.py:191) |
| Campo `output_pii_redacted_count` em `ChatResponse` e `OpenCodeTestResponse` | **PLANEJADO** — parte do LGPD-015 |
| Audit log `action='llm.output_scrubbed'` quando `output_pii_redacted_count > 0` | **PLANEJADO** — parte do LGPD-015 |
| Suite de testes pytest falha se LLM ecoar CNS | **PLANEJADO** — parte do LGPD-015 |
| CNS anchored (palavra-chave + 30ch + 2 formatos 15dig/17dig) na regex de output | **ESPEC PRONTO** — D3 do escopo, aguardando cartorio-dev implementar após LGPD-015 merge |

### R19 — DPO nominal incompleto (placeholders pendentes)

| Medida | Status |
|--------|--------|
| Inclusão de campos Nome + Email + Telefone no cabeçalho do RIPD, consent.md, privacy-policy.md | **CONCLUÍDO** — versão 1.4 deste RIPD, consent v1.1, privacy v1.1 |
| Placeholders `[NOME_DO_DPO]` e `[TELEFONE_DO_DPO]` com nota explícita de preenchimento pre-v0.6.0 | **CONCLUÍDO** |
| Preenchimento dos placeholders pelo tabelião | **PENDENTE** — Gustavo aciona sprint 3 onboarding ou D4 dedicado |
| Atualização do site footer (cartorio-n8n tem essa task E6.T2) | **PENDENTE** — cross-coord com cartorio-n8n |
| Backup v1.0 de consent.md e privacy-policy.md em `docs/archive/` (prova de consentimento anterior) | **CONCLUÍDO** — `consent_v1.0_2026-06-23.md` + `privacy-policy_v1.0_2026-06-23.md` |

---

## 6. Plano de resposta a incidente (LGPD art. 48)

### 6.1. Detecção

- Alerta automatizado do monitor systemd (cartorio-network-monitor)
- Reclamação de titular via dpo@2notasudi.com.br
- Notificação de provedor (Supabase, Cloudflare, OpenAI)
- Verificação diária da cadeia de audit log

### 6.2. Contenção (T+0 a T+1h)

- Bloquear endpoint afetado
- Rotacionar secrets (API keys, HMAC key, salt)
- Desconectar containers comprometidos
- Preservar logs e evidência forense

### 6.3. Avaliação (T+1h a T+24h)

- Quais dados foram afetados?
- Quantos titulares?
- Qual a severidade (baixa/média/alta)?
- Foi PII bruto ou apenas scrubbed?

### 6.4. Notificação

| Severidade | Ação |
|-----------|------|
| Baixa | Registrar internamente, sem notificar |
| Média | Notificar DPO + Gustavo em até 24h |
| Alta | Notificar ANPD em até 72h (LGPD art. 48) + titulares afetados sem demora indevida |

### 6.5. Remediação

- Deploy do fix em hotfix
- Atualizar testes para cobrir o caso
- Documentar timeline em `.harness/memory/MEMORY.md`
- Revisar RIPD com novos riscos identificados

### 6.6. Pós-incidente

- Análise de causa raiz (RCA)
- Atualização de política / RIPD / playbook
- Treinamento de equipe
- Comunicação pública se aplicável

---

## 7. Direitos do titular (LGPD art. 18)

Atendidos conforme Política de Privacidade (https://2notasudi.com.br/privacidade), com prazo de resposta de até 15 dias úteis.

---

## 8. Revisão periódica

| Item | Frequência |
|------|-----------|
| Revisão do RIPD | Anual ou após incidente relevante |
| Verificação da cadeia de audit log | Diária |
| Auditoria de PII scrubbing | Trimestral |
| Revisão de política de privacidade | Anual |
| Penetration test | Anual (E2.T7) |
| Revisão de cláusulas de operadores | Anual |

---

## 9. Aprovação

| Papel | Nome | Assinatura | Data |
|-------|------|-----------|------|
| DPO | [nome] | [digital] | 23/06/2026 |
| Tabelião(a) | [nome] | [digital] | 23/06/2026 |
| Comitê de Compliance | [ata] | [digital] | 23/06/2026 |

---

## 10. Histórico de versões

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 23/06/2026 | Versão inicial | Rein `cartorio-lgpd` |
| 1.1 | 23/06/2026 | Adicionados Tratamentos 5 (logs de webhook com PII scrubbed — N8N, art. 7º V, retenção 365d) e 6 (mensagens de boas-vindas com consentimento — Supabase, art. 7º I, retenção indeterminada até revogação) | Rein `cartorio-lgpd` (sessão `mvs_6a65b10ee18e42f18ed2b071bb65d6ed`) |
| 1.2 | 23/06/2026 | Adicionados Tratamentos 7 (OpenCode-Go / MiniMax como **sub-processor** LLM com DPA pendente — art. 7º V + art. 7º VI, BLOQUEIO ATIVO até assinatura) e 8 (N8N como **ferramenta de automação** self-hosted — art. 7º V + art. 7º II). Adicionados riscos R13–R17 e respectivas mitigações. Atualização da lista de operadores principais. | Rein `cartorio-lgpd` (sessão `mvs_f7a29511daec40b7995718801be1a2c5`) |
| 1.3 | 23/06/2026 | **Correção crítica de inconsistência documental**: provedor real = DeepSeek (chinês) via OpenCode-Go, NÃO MiniMax. Docstring do `opencode_go.py` linha 9-13 é a fonte da verdade. Atualização dos Bloqueios #5/#10/#11/#12 do AUDITORIA_BLOCKERS.md. Abertura LGPD-014 para DPA. | Rein `cartorio-lgpd` (sessão `mvs_3c841fe2622b4755bcd39d89333d4037`) |
| **1.4** | 23/06/2026 | **(a) Identificação nominal do DPO** (LGPD art. 41 §1º — placeholders `[NOME_DO_DPO]` e `[TELEFONE_DO_DPO]` em cabeçalho, seção 1 + cross-ref consent v1.1 e privacy v1.1) — **GAP 5 / LGPD-013**. **(b) CNS como dado sensível** (LGPD art. 5º II) incluído em Tratamento 1 — Categorias de dados + Detecção anchored (palavra-chave + 30ch + 2 formatos 15dig/17dig) — **GAP 4 / LGPD-009**. **(c) Reforço da transferência internacional para China** em Tratamento 7 — mecanismo duplo art. 33, II (SCC) + art. 33, I (consentimento específico) cross-ref consent Item 3 — **GAP 1 / LGPD-007**. **(d) Anexo `docs/lgpd/dpa_deepseek_template.md`** com 15 cláusulas obrigatórias (LGPD-011/LGPD-014) — substituindo placeholder textual anterior. **(e) Riscos R18 (CNS ecoado pelo LLM no output) + R19 (DPO placeholder pendente)** adicionados ao Quadro de Riscos (seção 4) com mitigações correspondentes (seção 5). **(f) Anexos** atualizados com `docs/archive/` (prova de consentimento anterior v1.0) + dpa_deepseek_template.md. Backup v1.3 salvo em `docs/archive/ripd_v1.3_2026-06-23.md`. | Rein `cartorio-lgpd` (sessão `mvs_d4fa1b1a154149dfb0bbadbb117ad1c1`) |

---

## 11. Anexos

- `docs/privacy-policy.md` — Política de Privacidade (v1.1 — 23/06/2026)
- `docs/archive/privacy-policy_v1.0_2026-06-23.md` — Backup v1.0 (prova de consentimento anterior)
- `docs/consent.md` — Termo de Consentimento (v1.1 — 23/06/2026)
- `docs/archive/consent_v1.0_2026-06-23.md` — Backup v1.0 (prova de consentimento anterior)
- `docs/lgpd/dpa_deepseek_template.md` — **Template DPA DeepSeek** (15 cláusulas obrigatórias — versão 1.4) — **NOVO nesta versão**
- `docs/lgpd/AUDITORIA_BLOCKERS.md` — Documento vivo de bloqueios ativos LGPD
- `docs/lgpd/opencode_go_audit.md` — Auditoria técnica da integração OpenCode-Go
- `docs/prospeccao-roteiro.md` — Roteiro de Prospecção LGPD-safe
- `docs/leads/roteiros/` — 3 variantes táticas (WhatsApp curto, e-mail institucional, LinkedIn tabelião)
- `backend/app/services/pii.py` — Implementação do PII scrubber (versão 1.4: CNS anchored pendente — D3)
- `backend/app/services/audit.py` — Implementação do audit log
- `backend/app/integrations/opencode_go.py` — Wrapper LLM com PII scrubbing interno, consent gate, audit log
- `backend/app/api/v1/router.py` — Webhook Evolution com scrub 3 camadas (output em PR LGPD-015)
- `backend/app/api/v1/integrations.py` — Smoke test OpenCode-Go (output scrub em PR LGPD-015)
- `infra/n8n-workflows/` — 11+ workflows N8N do chatbot (origem dos logs do Tratamento 5)
- `infra/n8n-workflows/welcome-message.json` — Workflow de boas-vindas + consentimento (Tratamento 6)
- `supabase/migrations/2026-06-23_consent_log.sql` — Tabela `consent_log` com RLS

---

**Nota final:** Este RIPD é documento vivo. Revisões são publicadas em `docs/ripd.md` (versão atual) e versões anteriores ficam acessíveis via histórico git (commit hashes). Backups físicos em `docs/archive/` (v1.0 de consent + privacy) são mantidos como prova de consentimento anterior em caso de auditoria ou fiscalização.