# RIPD - Relatorio de Impacto a Protecao de Dados Pessoais

**Controlador**: 2o Tabelionato de Notas de Uberlandia
**DPO (Encarregado)**: Maria Silva <dpo@2notasudi.com.br>
**Data**: 2026-06-25
**Versao**: 1.0.0
**Base legal LGPD**: art. 38 + art. 6 X (responsabilizacao e prestacao de contas)

## 1. Descricao do Tratamento

### 1.1 Natureza do Tratamento
- Coleta de dados pessoais de clientes do 2o Tabelionato via canais:
  - WhatsApp (Evolution API)
  - Telegram
  - Web (formulario)
  - Presencial (escritorio)
  - Telefone
- Armazenamento em Postgres (Supabase self-hosted) + Redis (cache)
- Compartilhamento com: Receita Federal (DOI/COAF), TJMG (emolumentos), CNJ
- Operacao de tratamento: leitura, escrita, consulta, anonimizacao, exclusao logica

### 1.2 Finalidades
- Execucao de servicos notariais (Lei 8.935/94)
- Cumprimento de obrigacoes legais (LGPD art. 7 II)
- Marketing consentido (LGPD art. 7 I) - opcional
- Pesquisa de satisfacao (LGPD art. 7 I) - opcional
- Auditoria interna (LGPD art. 37)
- Backup e disaster recovery (LGPD art. 46)

### 1.3 Categorias de Titulares
- Clientes pessoas fisicas (PF): 95% do volume
- Clientes pessoas juridicas (PJ): 5% do volume
- Funcionarios (separado em outro RIPD)
- Provedores externos (DPAs separados)

### 1.4 Categorias de Dados
Ver `docs/lgpd-base-legal-2026-06-25.json` para mapeamento completo.

Dados pessoais comuns: nome, CPF, RG, CNS, CNH, data_nascimento, endereco.
Dados pessoais sensiveis: NAO tratamos (LGPD art. 5 II - religiao, saude, etc).

### 1.5 Volume de Titulares
- Estimativa: ~200 clientes/mes
- Pico: ~500 clientes/mes em meses de pico (IR, vendas imoveis)
- Total acumulado: ~5.000 clientes nos ultimos 5 anos (com soft delete)

### 1.6 Fluxo de Dados
```
[Titular] -> [WhatsApp/Telegram/Web/Presencial] -> [Evolution API] -> [API Cartorio]
                                                                  -> [N8N]
                                                                  -> [Chatwoot]
                                                                  -> [Postgres/Supabase]
                                                                  -> [Redis cache]
                                                                  -> [Storage: cliente-docs (PRIVATE) / protocolo-pdfs (PRIVATE) / satisfacao-forms (PUBLIC READ)]
                                                                  -> [Audit log com HMAC chain]
```

## 2. Avaliacao de Necessidade e Proporcionalidade

### 2.1 Base Legal
Ver `docs/lgpd-base-legal-2026-06-25.json`. Resumo:

| Finalidade | Base Legal | Retencao | Justificativa |
|---|---|---|---|
| Execucao de ato notarial | Obrigacao legal (Lei 8.935/94 + art. 7 II) | 20 anos | Lei 8.935/94 art. 23 + 25 |
| Identificacao de partes | Obrigacao legal | 20 anos | Lei 8.935/94 |
| Emolumentos | Obrigacao legal (fiscal) | 5 anos | art. 173 CTN |
| Marketing | Consentimento (art. 7 I) | Ate revogacao | Opt-in explicito |
| Pesquisa satisfacao | Consentimento (art. 7 I) | Ate revogacao | Opt-in explicito |
| Lembrete agendamento | Consentimento (art. 7 I) | Ate revogacao | Opt-in explicito |
| Auditoria | Obrigacao legal (art. 37) | 5 anos | LGPD art. 37 |
| Backup DR | Obrigacao legal (art. 46) | 5 anos | LGPD art. 46 |

### 2.2 Principio da Necessidade (art. 6 III)
- Coletamos APENAS dados necessarios para o ato notarial
- NAO coletamos: religiao, saude, opiniao politica, orientacao sexual
- NAO usamos para finalidade secundaria sem nova base legal

### 2.3 Principio da Adequacao (art. 6 II)
- Tratamento compativel com finalidade declarada
- Mudanca de finalidade exige nova base legal (consentimento novo)

## 3. Riscos Identificados

### 3.1 Risco R1: Acesso nao autorizado
- **Probabilidade**: Media
- **Impacto**: Alto
- **Mitigacao**:
  - X-API-Key gate em todos endpoints (B0.3.SEC)
  - RLS policies no Supabase (S0 S02)
  - HMAC chain no audit_log (LGPD art. 37)
  - Encryption at-rest (em producao - S0 S08 vault)
  - Rate limit (A2)

### 3.2 Risco R2: Vazamento de dados
- **Probabilidade**: Baixa
- **Impacto**: Critico
- **Mitigacao**:
  - PII sanitizer (D8)
  - Pseudonimizacao via HMAC-SHA256 (D13)
  - Anonimizacao em relatorios (D13)
  - Truncamento de IP /24 (D13)
  - Direito ao esquecimento (D14)
  - Soft delete + retencao minima

### 3.3 Risco R3: Perda de dados
- **Probabilidade**: Baixa
- **Impacto**: Critico
- **Mitigacao**:
  - Backup DB 4x/dia pg_basebackup + WAL (A14)
  - Restore test periodico
  - DR runbook

### 3.4 Risco R4: Uso para finalidade incompativel
- **Probabilidade**: Baixa
- **Impacto**: Alto
- **Mitigacao**:
  - Base legal documentada por campo (D16)
  - Consentimento granular (D11)
  - Revogacao a qualquer momento (art. 8 §5)

### 3.5 Risco R5: Transferencia internacional
- **Probabilidade**: Nula (dados ficam no Brasil - Supabase self-hosted)
- **Impacto**: N/A
- **Mitigacao**: Apenas LLMs acessam dados de fora (opencode-go via API) - mas com PII sanitizer antes (D8)

## 4. Medidas de Mitigacao Implementadas

### 4.1 Tecnicas
- Criptografia em transito (TLS/HTTPS em todos endpoints)
- Criptografia em repouso (Vault Supabase S0 S08 + pgcrypto)
- HMAC chain no audit_log (LGPD art. 37)
- RLS policies (S0 S02)
- PII sanitizer (D8)
- Pseudonimizacao (D13)
- Anonimizacao em relatorios (D13)
- Rate limit (A2)
- Idempotency-Key (A6)
- Dead man's switch audit_log (A13)

### 4.2 Organizacionais
- DPO designado (Maria Silva)
- Treinamento interno (D22 - 5 videos LGPD)
- Politica de privacidade publicada (D23)
- Base legal documentada (D16)
- Relatorio ANPD anual (D9)
- Direito ao esquecimento implementado (D14)

## 5. Direitos do Titular (LGPD art. 18)

| Direito | Implementado | Endpoint |
|---|---|---|
| Confirmacao de existencia de tratamento | OK | GET /api/v1/lgpd/clientes/{id}/historico |
| Acesso aos dados | OK | GET /api/v1/lgpd/export {cliente_id} (D12) |
| Correcao de dados incompletos | OK | PATCH /api/v1/clientes/{id} |
| Anonimizacao, bloqueio ou eliminacao | OK | DELETE /api/v1/lgpd/clientes/{id} |
| Portabilidade | OK | GET /api/v1/lgpd/export {cliente_id} |
| Eliminacao dos dados tratados com consentimento | OK | DELETE /api/v1/lgpd/consent {cliente_id} |
| Informacao sobre entidades publicas e privadas com as quais houve compartilhamento | OK | GET /api/v1/lgpd/compartilhamentos {cliente_id} |
| Informacao sobre a possibilidade de nao fornecer consentimento e suas consequencias | OK | R28 (LGPD consent) |
| Revogacao do consentimento | OK | DELETE /api/v1/lgpd/consent {cliente_id} |
| Revisao de decisoes automatizadas | N/A (NAO usamos decisao automatizada) | -- |

## 6. Plano de Resposta a Incidentes (LGPD art. 48)

- Deteccao: Sentry + OpenTelemetry + audit_log dead man's switch
- Analise: DPO + equipe tecnica
- Contencao: revoke keys + isolate container
- Notificacao ANPD: ate 72h (D18)
- Notificacao titulares: caso afetar > 100 clientes ou dado sensivel
- Documentacao: audit_log imutavel

## 7. Revisao Periodica

- Frequencia: semestral
- Proxima revisao: 2026-12-25
- Responsavel: DPO + Gustavo Almeida
- Mudancas significativas: 1 (D14 - direito esquecimento cascade)

## 8. Aprovacao

- DPO: Maria Silva - 2026-06-25
- Controlador: Gustavo Almeida (Tabeliao) - 2026-06-25
- Tecnico responsavel: Pietra (Mavis) - 2026-06-25

---

Baseado no template da ANPD: https://www.gov.br/anpd/pt-br/documentos-e-publicacoes/guia-operacional-ripd.pdf
LGPD: Lei 13.709/2018
Lei Cartorio: 8.935/1994
Modified by Pietra + Gustavo Almeida 2026-06-25
