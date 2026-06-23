# Relatório de Impacto à Proteção de Dados Pessoais (RIPD) — Cartório 2 Notas Uberlândia

**Versão:** 1.0
**Data:** 23 de junho de 2026
**Controlador:** Cartório 2º Ofício de Notas de Uberlândia
**Encarregado de Dados (DPO):** dpo@2notasudi.com.br
**Base normativa:** LGPD Lei 13.709/2018 art. 38; Resolução CD/ANPD nº 4/2023 (RIPD); Provimento CNJ 74/2018

> Documento elaborado conforme **Resolução CD/ANPD nº 4/2023**, que disciplina a hipótese de elaboração de Relatório de Impacto à Proteção de Dados Pessoais. Este RIPD descreve o tratamento de dados pessoais realizado pelo chatbot do Cartório 2 Notas Uberlândia (WhatsApp/Telegram/Web) e pelos sistemas operacionais internos (API FastAPI, n8n, Evolution API, OpenClaw, Supabase).

---

## 1. Identificação do controlador e do encarregado

| Item | Valor |
|------|-------|
| Controlador | Cartório 2º Ofício de Notas de Uberlândia |
| CNPJ | XX.XXX.XXX/0001-XX |
| Endereço | Uberlândia/MG |
| Encarregado (DPO) | dpo@2notasudi.com.br |
| Operadores principais | Supabase (Postgres + Storage), Hostinger (VPS), Cloudflare (CDN/WAF), OpenAI / Anthropic (LLM), Evolution API (WhatsApp) |

---

## 2. Descrição dos tratamentos

### 2.1. Tratamento 1 — Atendimento ao público via chatbot

| Item | Descrição |
|------|-----------|
| Finalidade | Responder dúvidas sobre emolumentos, status de protocolo, agendamento de serviços notariais. |
| Base legal | LGPD art. 7º I (consentimento) + art. 7º V (exercício regular de direitos) |
| Categorias de titulares | Clientes do cartório, cidadãos em geral, escreventes |
| Categorias de dados | Nome, telefone, conteúdo da conversa (texto, áudio, imagem), metadados técnicos (IP, user-agent) |
| Dados sensíveis | Não tratados |
| Origem | Coleta direta (titular envia pelo WhatsApp/Telegram/Web) |
| Operações | Coleta, armazenamento, leitura, transmissão a LLM externo (com scrubbing), pseudonimização, anonimização após retenção |
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

---

## 11. Anexos

- `docs/privacy-policy.md` — Política de Privacidade
- `docs/consent.md` — Termo de Consentimento
- `docs/prospeccao-roteiro.md` — Roteiro de Prospecção LGPD-safe
- `docs/leads/roteiros/` — 3 variantes táticas (WhatsApp curto, e-mail institucional, LinkedIn tabelião)
- `backend/app/services/pii.py` — Implementação do PII scrubber
- `backend/app/services/audit.py` — Implementação do audit log

Modified by Gustavo Almeida