# Cartorio Chatbot — Memoria compartilhada do time

> Licoes e decisoes que afetam MAIS DE UM rein. Licoes especificas de um rein ficam na resposta dele (nao aqui).
>
> Regra: "vale pra outro projeto?" -> NAO -> fica no PR / resposta do rein. SIM -> vai pra ca.

---

## Decisoes arquiteturais (NÃO reverter sem discussao)

### D1 — Hash chain em Postgres, NAO WAL shipping externo (2026-06-22)
- append-only com SHA256(prev_hash + payload + timestamp) + HMAC
- verificacao em milissegundos, sem storage externo caro
- HMAC requer chave do servidor -> DB editada sem chave nao forja
- HMAC key em env var, rotacionada anualmente
- VER: `backend/app/services/audit.py` e `docs/ARCHITECTURE.md`

### D2 — PII scrubbing em 3 camadas (2026-06-22)
| Camada | Quando | O que |
|--------|--------|-------|
| Input | Antes de logar conversa | mascara CPF/RG/email/etc, guarda hash + scrubbed |
| Pre-LLM | Antes de chamar Claude/GPT | garante zero PII puro pra API publica |
| Output | Antes de responder ao cliente | confirma que resposta nao vaza |
- Hash de CPF deterministico com salt por cartorio -> permite `WHERE cpf_hash = ?`
- VER: `backend/app/services/pii.py` e `docs/ARCHITECTURE.md`

### D3 — Human-in-the-loop obrigatorio (2026-06-22)
- Bot NUNCA decide sozinho em: isencao, urgencia, validacao juridica, emissao certidao/escritura
- Bot PODE sozinho: horario, calcular emolumento (read-only), consultar status protocolo, duvida documentacao
- Quando intent confidence < 0.7 OU categoria requer HITL -> escala para escrevente via Telegram interno
- VER: `docs/ARCHITECTURE.md`

### D4 — Tabela emolumento snapshot (NAO live) (2026-06-22)
- Toda tabela e snapshotada no momento do calculo com `tabela_referencia` e `valido_ate`
- Protocolos antigos NAO recalculam
- Job diario carrega nova tabela do DO do estado (MG)

### D5 — Multi-tenancy futuro (schema_name) (2026-06-22)
- `schema_name` em cada tabela de negocio
- `cartorio_id` em cada query
- Implementacao: Sprint 5+ (multi-cartorio white label)

### D6 — Decisao CEO D3.1: Sprint 1 faz SO consulta emolumento (2026-06-22)
- Status protocolo so Sprint 2
- Criar protocolo so pos 30d shadow mode
- Motivo: ship rapido + validar com escreventes reais antes de bot ganhar write access

---

## Golden rules (NÃO quebrar)

### GR1 — CPF nunca em log, response, ou LLM publico
- Toda string que pode conter CPF deve passar por `pii.scrub()` antes de qualquer saida
- Logger.debug NAO pode usar `f"... {cpf} ..."` -> usar `f"... {cpf_hash} ..."`
- LLM (Claude/GPT) NAO recebe CPF puro, recebe scrubbed text
- VER: AGENTS.md secao Datasensitive

### GR2 — Toda mutacao grava audit_log
- Esquecer = bug critico
- Tests verificam: criar cliente, criar protocolo, enviar mensagem, calcular emolumento -> todas geram audit entry

### GR3 — Coverage >= 90% nao negociavel
- CI falha se coverage cair
- Nova regra de emolumento: 1 nominal + 2-3 bordas
- Nova mudanca em audit/pii: teste que falha se regressao

### GR4 — Conventional Commits + Modified by Gustavo Almeida
- Mensagem de commit termina com `Modified by Gustavo Almeida`
- Tipo: feat / fix / docs / test / refactor / chore / perf

### GR5 — Mudanca em audit/pii exige review do cartorio-lgpd
- Implementar OK, MERGE so com review registrada
- Workflow: cartorio-dev implementa -> cartorio-lgpd revisa -> merge

---

## Licoes operacionais

### LO1 — Workflow n8n NAO acessa Postgres direto (2026-06-22)
- Sempre chamar endpoint FastAPI
- Garante que toda operacao passe pelo audit_log
- Anti-pattern: n8n com credencial Supabase fazendo query direto

### LO2 — Idempotencia de webhook Evolution (a descobrir em Sprint 1)
- Webhook pode entregar 2x (retries do Evolution)
- Chave dedup: `message_id` do Evolution
- Workaround: SET no Redis com TTL 24h

### LO3 — Hash chain verificacao diaria (a implementar em Sprint 0.5)
- Cron job percorre cadeia, retorna `(ok, last_valid_position)`
- Se `ok=false` -> alerta P0 imediato

---

## Cross-rein dependency matrix

| Task origem | Requer review de | Motivo |
|-------------|------------------|--------|
| Mudanca em `audit.py` | cartorio-lgpd | LGPD art. 37 + integridade juridica |
| Mudanca em `pii.py` | cartorio-lgpd | LGPD art. 50 (boas praticas) |
| Nova regra de emolumento | cartorio-dev | Spec do estado MG |
| Nova politica retencao | cartorio-lgpd (define) + cartorio-dev (implementa) | LGPD art. 16 |
| Mudanca em workflow que toca PII | cartorio-lgpd | Garantir copy + scrub |
| Mudanca em template mensagem juridica | cartorio-lgpd | Copy juridica valida |
| Nova integracao externa | Harness (orquestra review) | ACL + audit |

---

## Pendencias conhecidas

- [ ] Criar `docs/LGPD.md` com politica privacidade + termo consentimento + politica retencao (dono: `cartorio-lgpd`)
- [ ] Criar `infra/README.md` com runbook deploy Easypanel (dono: `cartorio-n8n`)
- [ ] Configurar Easypanel: cartorio.com.br -> Caddy/Traefik + WAF Cloudflare (dono: `cartorio-n8n`)
- [ ] Implementar job diario de verificacao hash chain (dono: `cartorio-dev`)
- [ ] Implementar job diario de retencao de conversas >365d (dono: `cartorio-dev`, policy: `cartorio-lgpd`)

---

## Convencoes de memoria

- Data ISO (YYYY-MM-DD) sempre no titulo da entrada
- Citar arquivo:line quando referenciar codigo
- Distinguir **decisao** (D-N) vs **golden rule** (GR-N) vs **licao operacional** (LO-N)
- Entradas nao revertidas sem debate no canal

Modified by Gustavo Almeida
