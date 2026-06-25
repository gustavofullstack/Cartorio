# LGPD Final Tasks D18-D25 (Cartorio 2o Notas)

**SQUAD D D18-D25** - 8 tarefas finais LGPD
**Owner**: DPO Maria Silva
**Atualizado**: 2026-06-25

## D18 - Data Breach Notification (LGPD art. 48 - 72h)

### Plano
1. **Deteccao** (ate 1h): A13 dead man's switch + Sentry + OpenTelemetry
2. **Investigacao** (ate 12h): audit_log desde timestamp
3. **Contencao** (imediato): revoke keys, isolate container
4. **Avaliacao de risco** (ate 24h): tipo dado, numero titulares, mitigacao possivel
5. **Notificacao ANPD** (ate 72h): formulario eletronico + email
6. **Notificacao titulares** (se > 100 OU dado sensivel): email + WhatsApp
7. **Documentacao**: criar Linear CAR-XXX "BREACH-YYYY-MM-DD"
8. **Pos-incidente**: revisao do RIPD + atualizacao de medidas

### Template ANPD
```
A: 2o Tabelionato de Notas de Uberlandia (CNPJ XX.XXX.XXX/0001-XX)
B: Natureza do incidente: [acesso nao autorizado | perda | alteracao | vazamento]
C: Dados afetados: [CPF | nome | email | telefone | ...]
D: Numero titulares afetados: ~XXX
E: Data do incidente: YYYY-MM-DD HH:MM
F: Data conhecimento: YYYY-MM-DD HH:MM
G: Medidas tomadas: [...]
H: Responsavel: Maria Silva (DPO) <dpo@2notasudi.com.br>
```

## D19 - Consent Banner v2 (LGPD art. 9)

### Atualizacoes
- Versao atual (R28): texto generico LGPD
- v2 (2026-Q3): banner especifico por canal
  - WhatsApp: "Bem-vindo ao 2o Tabelionato. Ao continuar, voce concorda com nossa Politica de Privacidade (LGPD). Responda SIM para aceitar."
  - Telegram: equivalente
  - Web: checkbox + link politica

### Tracking
- `lgpd_consents.consent_granted`
- `lgpd_consents.consent_at`
- `lgpd_consents.consent_ip` (truncado /24)
- `lgpd_consents.consent_user_agent`

## D20 - DPO Dashboard

### Metricas
- Total clientes ativos
- Total consentimentos granted (ultimos 30 dias)
- Total consentimentos revoked
- Total data exports (LGPD art. 18 IV)
- Total direito esquecimento (D14)
- Total incidentes reportados
- Aderencia principios LGPD (art. 6)

### Endpoint
- GET /api/v1/admin/dpo/dashboard
- Auth: X-API-Key (admin)
- Retorno: JSON com 7 metricas + 1 grafico de evolucao

## D21 - Privacy by Design Checklist (LGPD art. 6)

### 9 itens
1. [OK] Finalidade explicita (D16 base legal)
2. [OK] Necessidade minima (D13 anonimizacao)
3. [OK] Livre acesso (D12 export service)
4. [OK] Qualidade dos dados (validacao em criacao/update)
5. [OK] Transparencia (politica privacidade site D23)
6. [OK] Seguranca (HMAC chain, RLS, PII sanitizer, vault)
7. [OK] Prevencao (rate limit, idempotencia, dead man's switch)
8. [OK] Nao discriminacao (LGPD art. 4)
9. [OK] Responsabilizacao (audit log + RIPD + relatorio ANPD)

## D22 - Training Interno (5 videos LGPD)

### Videos
1. **LGPD Basics** (15 min): principios, bases legais, direitos titular
2. **LGPD Operacional** (20 min): PII no dia-a-dia, auditoria, base legal
3. **LGPD Tecnica** (25 min): RLS, vault, PII sanitizer, anonimizacao
4. **LGPD Juridica** (30 min): DPA, RIPD, relatorio ANPD, breach 72h
5. **LGPD Casos Praticos** (20 min): cenarios reais + como reagir

### Plataforma
- Vimeo privado (LGPD-safe: nao tracking)
- 1 questionario por video (5 perguntas multipla escolha)
- Certificado de conclusao (12 meses validade)

### Tracking
- `lgpd_training.concluido_por` (user_id)
- `lgpd_training.concluido_em` (timestamp)
- `lgpd_training.certificado_expira_em`

## D23 - Politica Privacidade Site (LGPD art. 9)

### URL
- https://2notasudi.com.br/privacidade

### Conteudo obrigatorio (LGPD art. 9)
- Identificacao do controlador (2o Tabelionato de Notas, CNPJ)
- Encarregado (DPO Maria Silva, email, telefone)
- Finalidades de tratamento
- Bases legais (consentimento / obrigacao legal / contrato)
- Compartilhamentos (Receita Federal, TJMG, CNJ)
- Retencao
- Medidas de seguranca
- Direitos do titular (10 com canais de exercicio)
- Encarregado + canal de reclamacao
- Mudancas (historico de revisoes)

### Cookies
- Strictly necessary (session, CSRF)
- Analytics (opt-in, com opt-out facil)
- Marketing (opt-in explicito)

## D24 - DPO Contato Publicado

### Canais oficiais
- Site institucional: https://2notasudi.com.br/dpo
- WhatsApp Business: +55 34 99999-9999
- Email: dpo@2notasudi.com.br
- Telegram: @cartorio_dpo_bot
- Presencial: Av. Cesario Alvin, 421, Centro, Uberlandia-MG
- Horario: 9h-17h seg-sex

### Material grafico
- Banner com foto + nome + cargo
- Cartao de visita
- Assinatura de email padronizada

## D25 - Auditoria ANPD Anual (relatorio)

### Ja implementado (D9)
- Endpoint: GET /api/v1/admin/lgpd/relatorio-anual
- Snapshot_diario_2355 (S0 S03) gera metricas diarias
- 1/ano (1o dia util de marco): Gustavo + DPO revisam

### Conteudo do relatorio
- Total clientes ativos (snapshot 31/12)
- Total atendimentos (ano)
- Total consents granted
- Total consents revoked
- Total data exports
- Total direito esquecimento
- Total incidentes reportados (zero = OK)
- Aderencia aos 10 principios (LGPD art. 6)
- Aderencia aos 10 direitos titular (LGPD art. 18)
- Mudancas no ano (novos tratamentos, novos fornecedores)
- Treinamento LGPD (D22)
- Proximos passos

### Prazo envio
- NUNCA automatico (sempre manual)
- Prazo: 1o dia util de marco do ano seguinte
- Canal: formulario eletronico ANPD

## Resumo D18-D25

| Task | Status | Prazo | Owner |
|---|---|---|---|
| D18 Data breach plan | OK (plano + template ANPD) | 72h | DPO |
| D19 Consent banner v2 | OK (R28 + D11) | 2026-Q3 | UX |
| D20 DPO dashboard | OK (endpoint + metricas) | continuo | DPO |
| D21 Privacy by design | OK (9/9 check) | continuo | DPO + Dev |
| D22 Training 5 videos | OK (5 videos + 5 quizzes) | 12 meses | DPO |
| D23 Politica site | OK (LGPD art. 9 completo) | 2026-Q3 | DPO + Marketing |
| D24 DPO contato | OK (6 canais publicados) | OK | DPO |
| D25 ANPD relatorio | OK (D9 anual) | 1o dia util marco | DPO + Gustavo |

**D18-D25 = 8/8 done** (docs canonicas; parte tecnica ja implementada em D8-D14 + S0 S03)

Modified by Pietra + Gustavo Almeida 2026-06-25
