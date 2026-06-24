# LGPD — Política de Privacidade + Termo de Consentimento

> Documento LEGAL do Cartório Chatbot. Lei 13.709/2018 (LGPD) + Provimento 74/2018 CNJ.
> **DPO nominal**: ver `docs/RIPD.md` v1.3.
> **Última atualização**: 2026-06-24.

## 1. Identificação do Controlador

- **Razão social**: 2º Tabelionato de Notas e Protesto de Uberlândia
- **CNPJ**: [placeholder]
- **Endereço**: [placeholder]
- **DPO (Encarregado de Dados)**: [nome + email + telefone]
- **Site**: https://cartorio.local

## 2. Definições

- **Titular**: pessoa natural a quem se referem os dados pessoais (cliente do cartório)
- **Controlador**: 2º Tabelionato de Notas e Protesto de Uberlândia
- **Operador**: Mavis (MiniMax) — provedor de IA que processa dados em nome do controlador
- **Sub-operadores**: OpenCode-Go (LLM), Supabase (Postgres), N8N (workflow), OpenClaw (gateway), Evolution API (WhatsApp)
- **Encarregado/DPO**: pessoa designada pelo controlador para ser o canal de comunicação com titulares e ANPD

## 3. Dados pessoais tratados

| Categoria | Exemplos | Finalidade | Base legal |
|-----------|----------|-----------|-----------|
| Identificação | CPF, RG, CNS, CNH, CNPJ, título eleitor, PIS | Identificar titular, lavrar ato | Obrigação legal (Provimento 74 CNJ) + consentimento |
| Contato | Telefone, email, endereço | Contatar titular, enviar protocolo | Consentimento |
| Sensíveis (saúde) | CNS (CNS = Cartão Nacional de Saúde) | Compliance legal específico | Obrigação legal (LGPD art. 11 II) |
| Protocolo | Número CART-YYYY-XXXXXX, ato, valor, data | Controle cartorário | Obrigação legal (Provimento 74 CNJ) |
| Conversa (chat) | Texto trocado com bot | Atender, registrar | Consentimento |
| Áudio/imagem | Mídia anexada pelo titular | Atender, anexar ao protocolo | Consentimento |
| IP de conexão | IPv4 / IPv6 | Segurança, audit, anti-fraude | Legítimo interesse + consentimento (LGPD art. 37) |
| User agent | Navegador/app | Identificar canal | Legítimo interesse |

## 4. Finalidades específicas

1. **Atendimento ao cliente** via WhatsApp/Telegram/Web (LGPD art. 7 V — execução de contrato)
2. **Lavrar ato cartorário** (escritura, procuração, certidão) — Provimento 74 CNJ
3. **Calcular emolumentos** (LGPD art. 7 II — cumprimento de obrigação legal)
4. **Armazenar protocolo** por 5 anos (LGPD art. 16 + Provimento 74)
5. **Auditoria e compliance** (LGPD art. 37 — registro de operações)
6. **Segurança da informação** (anti-fraude, anti-spam, rate limit)

## 5. Bases legais

- **LGPD art. 7 I** — consentimento (para finalidades não obrigatórias, ex: marketing)
- **LGPD art. 7 II** — cumprimento de obrigação legal (cartório DEVE guardar protocolo 5 anos)
- **LGPD art. 7 V** — execução de contrato (atendimento ao titular que solicitou serviço)
- **LGPD art. 7 VI** — exercício regular de direitos (processo administrativo/judicial)
- **LGPD art. 7 IX** — interesse legítimo (segurança, anti-fraude)
- **LGPD art. 11 II** — dados sensíveis (saúde) — cumprimento de obrigação legal

## 6. Consentimento

### 6.1. Quando exigido
- Marketing / comunicação proativa
- Compartilhamento com terceiros NÃO obrigatórios
- Finalidades além das cartorárias (analytics, perfil, recomendação)

### 6.2. Como é coletado
- Mensagem WhatsApp/Telegram/Web ANTES de qualquer coleta de dado
- Bot exibe termo de consentimento resumido + link para este documento completo
- Cliente responde "SIM" (ou equivalente) → consentimento gravado com timestamp + IP + user agent

### 6.3. Como revogar
- A qualquer momento, via chat: "REVOGAR CONSENTIMENTO" ou "ESQUECER"
- Via email ao DPO: dpo@cartorio.local
- Via portal web: https://cartorio.local/revogar

Efeito: LGPDBlockedResponse em todas as próximas requisições + DELETE cliente + cascade.

### 6.4. O que acontece se revogar
- Conversas: anonimizadas imediatamente
- Protocolo COM ato lavrado: anonimizado APÓS 5 anos (Provimento 74) — não pode ser apagado antes
- Protocolo SEM ato: deletado imediatamente
- Audit log: preservado 5 anos (obrigação legal) — sem PII puro

## 7. Compartilhamento

### 7.1. Sub-operadores (todos com DPA assinado)

| Sub-operador | Finalidade | Localização |
|--------------|-----------|-------------|
| MiniMax (Mavis AI) | Processamento de linguagem natural | Brasil |
| OpenCode-Go (deepseek-v4-flash) | LLM provider | Global |
| Supabase | Banco de dados Postgres + Storage | Global |
| N8N | Workflow automation | Self-hosted |
| Evolution API | WhatsApp gateway | Self-hosted |
| OpenClaw | AI agent gateway | Self-hosted |

### 7.2. Quando compartilhamos com terceiros
- **Nunca** para finalidades de marketing de terceiros
- **Apenas** quando obrigado por lei (ex: corregedoria, ANPD, Receita Federal)
- **Apenas** com sub-operadores listados acima (DPA assinado)

## 8. Retenção

| Dado | Retenção | Base legal | Após retenção |
|------|----------|-----------|---------------|
| Conversa (texto scrubbed) | 365 dias | Consentimento | Apagar |
| Conversa (áudio/imagem) | 365 dias | Consentimento | Apagar |
| Protocolo COM ato lavrado | **5 anos** | Obrigação legal (Provimento 74) | Anonimizar (cpf_hash=NULL) |
| Protocolo SEM ato | Até revogação | Consentimento | Deletar |
| Documento jurídico | 20+ anos | Obrigação legal | Manter (anonimizar partes não essenciais) |
| Audit log (hash chain) | 5 anos | Obrigação legal + interesse público | Manter (sem PII puro) |
| Log de acesso (LGPD art. 37) | 5 anos | LGPD art. 37 | Manter |
| Emolumento snapshot | Indeterminado | Obrigação legal | Manter |
| Consentimento LGPD | Enquanto durar relação + 5y | Obrigação legal | Manter registro da revogação |
| IP de conexão (completo) | 2 anos | Legítimo interesse + LGPD art. 37 | Truncar /24 + reter truncado por mais 3y |
| PII em log (sem necessidade) | 0 dias | LGPD art. 50 boas práticas | NUNCA logar PII puro |

## 9. Direitos do titular (LGPD art. 18)

| Direito | Como exercer | Prazo |
|---------|-------------|-------|
| Confirmação da existência de tratamento | Chat / email DPO / portal | Imediato |
| Acesso aos dados | GET /api/v1/cliente/{id}/historico | Imediato |
| Correção de dados incompletos/incorretos | Chat / portal | 15 dias |
| Anonimização, bloqueio ou eliminação | "ESQUECER" no chat / DELETE cliente | 30 dias |
| Portabilidade | Solicitar ao DPO via email | 30 dias |
| Eliminação dos dados consentidos | "REVOGAR CONSENTIMENTO" | Imediato |
| Informação sobre entidades públicas e privadas com quem compartilhou | Solicitar ao DPO | 15 dias |
| Revisão de decisão automatizada | Solicitar ao DPO (HITL garantido) | 30 dias |

Para exercer: `dpo@cartorio.local` ou chat com escrevente.

## 10. Segurança da informação

- **Criptografia em trânsito**: HTTPS/TLS 1.3 (Traefik + Let's Encrypt)
- **Criptografia em repouso** (planejado M4.11): pgcrypto + Vault
- **PII scrubbing em 3 camadas**: input, pre-LLM, output
- **Audit log imutável**: SHA256 chain + HMAC, verificação diária 06:00
- **Rate limit**: 60 req/min/IP + 100 req/min DDoS (hard cap)
- **Webhook idempotency**: Redis SETNX com TTL 5min
- **Dead-letter queue**: webhooks falhados com retry 3x exp backoff
- **Auth inter-service**: header `X-API-Key` (openssl rand hex 32) + HMAC SHA256
- **2FA/MFA** (planejado): Sprint futuro

## 11. Incidentes

Em caso de incidente de segurança com risco aos titulares:
1. Detectar (alerta, reclamação, auditoria)
2. Conter (parar vazamento — bloquear endpoint)
3. Avaliar (que dados, quantos titulares, qual severidade)
4. Notificar DPO + Gustavo em até 24h
5. Se risco ≥ médio: notificar ANPD em até 72h (LGPD art. 48)
6. Notificar titulares afetados
7. Remediar (deploy fix)
8. Documentar timeline + lição + memória

## 12. Encarregado/DPO

- **Nome**: [placeholder]
- **Email**: dpo@cartorio.local
- **Telefone**: [placeholder]
- **Disponibilidade**: 24/7 via email, horário comercial via telefone
- **Função**: canal de comunicação entre controlador, titulares e ANPD

## 13. Alterações nesta política

Qualquer alteração será:
1. Comunicada por email aos titulares cadastrados (30 dias antes)
2. Publicada no site do cartório
3. Versão datada (LGPD art. 8)
4. Hash do documento armazenado para prova de integridade

## 14. Base legal completa

- **Lei 13.709/2018** (LGPD)
- **Provimento 74/2018 CNJ** (cartórios)
- **Lei 8.935/1994** (Lei dos Cartórios)
- **Lei 10.406/2002** (Código Civil — atos cartorários)
- **Resolução CNJ 35/2007** (normas técnicas)
- **LGPD art. 50** (boas práticas e governança)
- **LGPD art. 46** (segurança da informação)
- **LGPD art. 37** (registro de operações)
- **LGPD art. 48** (comunicação de incidente)

Modified by Mavis (Pietra root mvs_410a1b1266d64830b9dfa31973fdd9fe — 2026-06-24 10:50 BRT)