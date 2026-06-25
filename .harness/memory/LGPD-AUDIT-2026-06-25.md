# Relatorio ANPD - 2026

**Gerado em**: 2026-06-25T10:53:29.674922+00:00
**Gerado por**: system:cartorio-dpo
**Hash anchor (SHA256)**: `76cd6290da0f491206daf26280dbdecd65a8c2dbd495618bff680285ffcda7bf`

## 1. Titulares

- Total: **2**
- Ativos: **2**
- Anonimizados/deletados: **0**

## 2. Operacoes

- Protocolos emitidos em 2026: **1**
- Atividades de tratamento (audit log): **488**
- Audit chain total: **488** entries

## 3. Direitos dos Titulares (art. 18)

- Total exercidos: **0**

  - confirmacao_existencia: 0
  - acesso_dados: 0
  - correcao: 0
  - anonimizacao_bloqueio_eliminacao: 0
  - portabilidade: 0
  - revogacao_consentimento: 0
  - oposicao: 0

## 4. Incidentes de Seguranca (art. 48)

- total: 0
- comunicados_anpd: 0
- vazamentos_dados_pessoais: 0
- ataques_mitigados: 0

## 5. Tipos de Dados Tratados

- dados_identificacao (nome, cpf, rg, data_nascimento)
- dados_contato (telefone, email, endereco)
- dados_ato_juridico (tipo, valor, partes, data_ato)
- dados_documento (pdf, imagem, hash_integridade)
- dados_audit (request_id, ip_truncado, user_agent, canal)
- dados_lgpd (consentimento, retencao, anonimizacao, opt_in)

## 6. Finalidades de Uso

- Prestacao de servicos notariais (Lei 8.935/94 art. 6)
- Cumprimento de obrigacao legal (CGJ, CNJ, Receita Federal)
- Atendimento ao cliente via WhatsApp/Telegram/balcao
- Auditoria ANPD e ANOREG/BR
- Retencao legal por 5 anos (clientes COM protocolo) / 2 anos (inativos)

## 7. Medidas de Seguranca (art. 46)

- Criptografia at-rest no DB (volume LUKS/ZFS)
- TLS 1.3 em transito (Traefik + certs LE)
- MFA admin via Tailscale + X-API-Key
- Audit log chain SHA256 (qualquer alteracao invalida chain)
- Backup 4x/dia (7d local, mensal S3)
- Sanitizacao PII em logs (CPF/CNPJ/email/phone/RG)
- Soft delete (deleted_at) + anonimizacao automatica 5y/2y
- OpenClaw agent com 1M context + thinkings adaptativo

## 8. Encarregado (DPO) - art. 41

- nome: Gustavo Almeida
- email: dpo@2notasudi.com.br
- telefone: +55 34 99999-9999
- papel: Encarregado/DPO (LGPD art. 41)

## 9. Base Legal

- principal: LGPD Lei 13.709/2018
- setorial: Lei 8.935/94 (Notarios e Registradores)
- regulamentacao: Resolucao CNJ 81/2009 + Provimento CNJ 74/2018

## 10. Observacoes

Sistema self-hosted. Todos os dados em VPS no Brasil (Hostinger). Stack: FastAPI + Postgres + N8N + Chatwoot + Evolution + Redis. Total 488 audit entries (imutavel, SHA256 chain).
