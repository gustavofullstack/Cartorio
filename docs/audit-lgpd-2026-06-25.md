# Auditoria LGPD - Cartorio 2o Notas

**SQUAD C C7** - procedures de auditoria LGPD
**Owner**: DPO Maria Silva
**Atualizado**: 2026-06-25

## 1. Audit Log (LGPD art. 37)

### 1.1 Estrutura
- Tabela: `audit_log`
- Campos: actor_id, actor_type, action, resource, payload (jsonb), ip, ip_truncated, user_agent, request_id, canal, prev_hash, hash, hmac_signature, timestamp
- Chain: HMAC-SHA256 encadeado (prev_hash + hash + hmac_signature)
- Retencao: 5 anos (LGPD art. 37 + art. 50)
- Volume: ~500 entries/dia (estimativa)

### 1.2 Query comum
```sql
-- Eventos do cliente X
SELECT * FROM audit_log
WHERE payload->>'cliente_id' = '123'
ORDER BY id DESC LIMIT 50;

-- Eventos do dia
SELECT actor_id, action, resource, timestamp
FROM audit_log
WHERE timestamp::date = CURRENT_DATE
ORDER BY id DESC;

-- Chain broken?
SELECT * FROM fn_audit_chain_verify(0, NULL);
-- {total_checked, chain_ok, first_bad_id}
```

### 1.3 Verificacao automatica
- S0 S03 pg_cron: `audit_verify_diario` 06:00 UTC (03:00 BRT)
- A13: dead man's switch (alerta Telegram GRUPO Pietra se > 1h stale)

## 2. Direitos do Titular (LGPD art. 18)

### 2.1 Confirmacao de tratamento (art. 18 I)
**Endpoint**: GET /api/v1/lgpd/clientes/{id}/historico
**Retorno**: array de eventos onde cliente aparece
**Prazo**: imediato
**Auditado**: action=`lgpd.confirmacao` em audit_log

### 2.2 Acesso aos dados (art. 18 II)
**Endpoint**: GET /api/v1/lgpd/export?cliente_id=X
**Retorno**: JSON com {clientes, protocolos, atendimentos, documentos, ...}
**Prazo**: imediato
**Auditado**: action=`lgpd.export` em audit_log

### 2.3 Correcao (art. 18 III)
**Endpoint**: PATCH /api/v1/clientes/{id}
**Prazo**: ate 5 dias uteis
**Auditado**: action=`lgpd.correcao` em audit_log (old + new)

### 2.4 Anonimizacao (art. 18 IV)
**Endpoint**: DELETE /api/v1/lgpd/clientes/{id}
**Service**: lgpd_direito_esquecimento.py (D14)
**Prazo**: 15 dias uteis
**Reversibilidade**: 30 dias
**Auditado**: action=`lgpd.direito_esquecimento` em audit_log

### 2.5 Portabilidade (art. 18 IV)
**Endpoint**: GET /api/v1/lgpd/export?cliente_id=X (D12)
**Service**: lgpd_export.py
**Formato**: JSON estruturado + (futuro) ZIP com PDFs
**Prazo**: 15 dias uteis
**Auditado**: action=`lgpd.export` em audit_log

### 2.6 Eliminacao (art. 18 VI)
**Endpoint**: DELETE /api/v1/lgpd/clientes/{id}
**Service**: lgpd_direito_esquecimento.py (D14)
**Soft delete + anonimizacao** (LGPD: dado pode ser mantido para obrigacao legal)

### 2.7 Compartilhamentos (art. 18 VII)
**Endpoint**: GET /api/v1/lgpd/compartilhamentos?cliente_id=X
**Retorno**: lista de entidades que receberam dados
**Padrao**: Receita Federal (DOI/COAF), TJMG (emolumentos), CNJ

### 2.8 Revogacao consentimento (art. 18 IX)
**Endpoint**: DELETE /api/v1/lgpd/consent?cliente_id=X
**Service**: lgpd_consent.py (D11)
**Efeito**: futuro (dados ja tratados sob base legal NAO sao apagados)

## 3. Base Legal por Tratamento (LGPD art. 7)

Ver `docs/lgpd-base-legal-2026-06-25.json` (D16).

Resumo:
- **consentimento** (art. 7 I): revogavel
- **cumprimento_obrigacao_legal** (art. 7 II): NAO revogavel
- **execucao_contrato** (art. 7 V): enquanto contrato vigente
- **exercicio_regular_de_direitos** (art. 7 VI): durante processo
- **obrigacao_legal_operacao_cartorio** (art. 7 II + Lei 8.935/94): NAO revogavel

## 4. Retencao (LGPD art. 16)

| Dado | Retencao | Base |
|---|---|---|
| audit_log | 5 anos | LGPD art. 37 + 50 |
| clientes (PF/PJ) | 5 anos pos-relacionamento | Lei 8.935/94 + CTN art. 173 |
| protocolos | 20 anos | Lei 8.935/94 art. 23 + 25 |
| emolumentos | 5 anos | CTN art. 173 |
| conversas WhatsApp | 6 meses | LGPD art. 6 IV (necessidade) |
| consent_granted | ate revogacao + 5 anos | LGPD art. 7 I + art. 37 |
| IP em logs | 6 meses | LGPD art. 6 VIII (minimizacao) |

## 5. RIPD (Relatorio Impacto Protecao Dados - LGPD art. 38)

Ver `docs/ripd-cartorio-2026-06-25.md` (D17).

8 secoes:
1. Descricao do tratamento
2. Avaliacao necessidade/proporcionalidade
3. Riscos identificados (5)
4. Medidas mitigacao (10 tecnicas + 6 organizacionais)
5. Direitos titular (10 com endpoints)
6. Plano resposta incidentes
7. Revisao periodica (semestral)
8. Aprovacao (DPO + Controlador + Tecnico)

## 6. Relatorio ANPD Anual (D9)

Endpoint: GET /api/v1/admin/lgpd/relatorio-anual

Inclui:
- Total clientes ativos
- Total atendimentos
- Total consents granted
- Total consents revoked
- Total data exports
- Total direito esquecimento
- Total incidentes reportados
- Aderencia aos principios LGPD

Prazo: anual (1o dia util de marco)

## 7. Data Breach (LGPD art. 48)

Prazo: 72h para ANPD + clientes afetados

Plano (ver `docs/runbook-operacoes.md` 4.6):
1. Contain: revoke keys, isolate container
2. Investigate: audit_log desde timestamp
3. ANPD notification
4. Customer notification (> 100 clientes OU dado sensivel)
5. Document incident
6. Linear CAR-XXX "BREACH-YYYY-MM-DD"

## 8. DPO (Encarregado de Dados - LGPD art. 41)

- **Nome**: Maria Silva
- **Email**: dpo@2notasudi.com.br
- **Telefone**: (34) 99999-9999
- **Horario**: 9h-17h seg-sex
- **Atribuicoes**:
  - Receber reclamacoes dos titulares
  - Orientar funcionarios sobre LGPD
  - Executar RIPD
  - Comunicar ANPD em caso de breach
  - Aceitar sugestoes do conselho (se houver)

## 9. Auditoria Externa (semestral)

DPO Maria Silva + Gustavo Almeida:
- Revisar `audit_log` (eventos de mutacao)
- Revisar `lgpd_consents` (revogacoes)
- Revisar `lgpd_direito_esquecimento` (execucoes)
- Revisar `relatorio-anual` (gerado 1x/ano)
- Atualizar RIPD (mudancas significativas)

## 10. Politica de Privacidade (D23 - site institucional)

Publicado em https://2notasudi.com.br/privacidade
Conteudo obrigatorio (LGPD art. 9):
- Identificacao do controlador (2o Tabelionato de Notas)
- Encarregado (DPO Maria Silva)
- Finalidades de tratamento
- Bases legais
- Direitos do titular
- Compartilhamentos (Receita/TJMG/CNJ)
- Retencao
- Medidas de seguranca

Modified by Pietra + Gustavo Almeida 2026-06-25
