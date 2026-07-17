# LGPD Go-Live Dashboard — G7 Wave 29 A3

**Controlador:** 2º Serviço Notarial de Uberlândia  
**Owner técnico:** `cartorio-lgpd`  
**Owner SUI (assinatura / publicação):** Gustavo Almeida + DPO  
**Data do painel:** 2026-07-17  
**Escopo:** single go-live cross-index DPA MiniMax · Privacy Policy v3 · RIPD 1.4 · Data Inventory  

> **REGRA ABSOLUTA — AGENT CANNOT SIGN / PUBLISH**  
> Agente **não** assina DPA, **não** publica política no site, **não** preenche CNPJ/DPO
> nominal real em produção, **não** seta flags env de produção, **não** grava PDF
> assinado como “já assinado”.  
> Status agent-side = **READY_TO_SIGN / DRAFT / HOLD**. Status **SIGNED / PUBLISHED**
> só após ação humana documentada (Gustavo + DPO + Tabelião quando aplicável).

---

## 1. Status table (fonte única)

| # | Artefato | Path | Status go-live | Task | Residual |
|---|----------|------|----------------|------|----------|
| 1 | DPA MiniMax package | [`docs/DPA_MINIMAX_READY_TO_SIGN_G7.md`](DPA_MINIMAX_READY_TO_SIGN_G7.md) | **READY_TO_SIGN** | G7.19.T2 | **SIGN HOLD** — bilateral + PDF + flag |
| 2 | Privacy Policy v3 (texto) | [`docs/PRIVACY_POLICY_V3_G7.md`](PRIVACY_POLICY_V3_G7.md) | **DRAFT** (publicável) | G7.19.T3 | Placeholders DPO/CNPJ; **PUBLISH HOLD** |
| 3 | Privacy v3 publish checklist | [`docs/PRIVACY_POLICY_V3_PUBLISH_CHECKLIST_G7.md`](PRIVACY_POLICY_V3_PUBLISH_CHECKLIST_G7.md) | **PUBLISHED HOLD** (checklist aberto) | G7.19.T3 | A1–F todos `[ ]` — site + bot |
| 4 | RIPD v1.4 addendum | [`docs/lgpd/RIPD_v1.4_ADDENDUM.md`](lgpd/RIPD_v1.4_ADDENDUM.md) | **DRAFT** técnico | G6.C.T1 / cross G7.19 | **SIGN HOLD** DPO / Gustavo |
| 5 | Data inventory Wave 26 | [`docs/LGPD_DATA_INVENTORY_G7_WAVE26.md`](LGPD_DATA_INVENTORY_G7_WAVE26.md) | **DONE** (refresh 25 fields) | G7.19.T4 | Gaps manuais §4; scanner extend |
| 6 | SUI consolidado Wave 28 | [`docs/SUI_CHECKLIST_G7_WAVE28.md`](SUI_CHECKLIST_G7_WAVE28.md) | Agent [x] / SUI [ ] | G7.25.T1 | §11 DPA + §12 Privacy |

### Legenda de status

| Label | Significado |
|-------|-------------|
| **READY_TO_SIGN** | Pacote jurídico/técnico pronto; **sem** assinatura real |
| **DRAFT** | Conteúdo agent-side completo ou quase; falta sign-off / placeholders |
| **PUBLISHED HOLD** | Checklist de publicação existe; site **não** atualizado |
| **SIGN HOLD** | Aguarda assinatura humana (DPO / Tabelião / contraparte) |
| **DONE** | Refresh agent-side fechado (inventory); não implica go-live legal total |

---

## 2. Links e dependências cruzadas

```
                    ┌─────────────────────────────────┐
                    │  LGPD_GO_LIVE_DASHBOARD_G7.md   │  ← este painel
                    │         (Wave 29 A3)            │
                    └───────────────┬─────────────────┘
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
   DPA_MINIMAX_READY_TO_SIGN   PRIVACY_POLICY_V3_G7    RIPD_v1.4_ADDENDUM
   (READY_TO_SIGN)             (DRAFT)                 (DRAFT técnico)
           │                        │                        │
           │                        ▼                        │
           │               PUBLISH_CHECKLIST_G7              │
           │               (PUBLISHED HOLD)                  │
           │                        │                        │
           └────────────┬───────────┴────────────┬───────────┘
                        ▼                        ▼
              LGPD_DATA_INVENTORY          SUI_CHECKLIST_G7_WAVE28
              (DONE Wave 26)               §11 DPA · §12 Privacy
                        │
                        ▼
              LLM_DPA_MATRIX · DPA_FLOW_REPORT · consent.md · pii.py
```

| Doc relacionado | Papel |
|-----------------|--------|
| `docs/LLM_DPA_MATRIX.md` | MiniMax row → READY_TO_SIGN até assinar |
| `docs/DPA_FLOW_REPORT_2026-07-16.md` | Tracker assinaturas DPA |
| `docs/lgpd/dpa_minimax_template.md` | Template cláusulas completo |
| `docs/lgpd/DPA_INDEX.md` | Índice DPA D01–D05 |
| `docs/privacy-policy.md` | v1.1 vigente doc até publish v3 |
| `docs/consent.md` | Consent multi-canal (bump se material) |
| `docs/ripd.md` | RIPD 1.3 base |
| `backend/app/services/pii.py` | Scrub 3 camadas (pré-requisito prod LLM) |
| `scripts/dpa_sign_flow.py` | Tracker CLI pós-assinatura |
| `.harness/memory/lesson-202-g7-wave27-a3-lgpd-2026-07-17.md` | Lesson DPA+Privacy Wave 27 |

---

## 3. Human actions remaining (Gustavo + DPO)

### 3.1 DPA MiniMax — SIGN HOLD (SUI §11 / G7.19.T2)

| # | Ação | Quem | Done |
|---|------|------|------|
| 1 | Preencher placeholders cartório (CNPJ, endereço, tabelião, DPO nominal/telefone) | Gustavo + Tabelião + DPO | [ ] |
| 2 | Due diligence MiniMax (sede, data residency, ISO/SOC) | DPO + Gustavo | [ ] |
| 3 | Negociar no-training / retenção conteúdo / notificação incidente | Gustavo + MiniMax Legal | [ ] |
| 4 | **Assinatura bilateral** (PDF) — DPO + Tabelião + MiniMax | SUI | [ ] |
| 5 | Arquivar PDF (`docs/lgpd/dpa_minimax.pdf` ou vault + pointer) | Gustavo | [ ] |
| 6 | Flag `LGPD_DPA_MINIMAX_SIGNED=true` em prod (EasyPanel) se aplicável | Gustavo / SRE | [ ] |
| 7 | Audit log `dpa.minimax.signed` + `LLM_DPA_MATRIX` → **SIGNED** | cartorio-lgpd (pós-SUI) | [ ] |
| 8 | `python3 scripts/dpa_sign_flow.py` atualizar tracker | cartorio-lgpd | [ ] |

**Até item 4:** MiniMax permanece READY_TO_SIGN. Preferir providers já SIGNED ou Llama local para qualquer fluxo com risco DATASENSITIVE.

### 3.2 Privacy Policy v3 — PUBLISHED HOLD (SUI §12 / G7.19.T3)

| # | Ação | Quem | Done |
|---|------|------|------|
| A1–A4 | DPO/CNPJ/endereço + aprovação escrita DPO + Tabelião | SUI | [ ] |
| A5–A6 | HTML/PDF público + SHA-256 do texto final | Gustavo / front + lgpd | [ ] |
| B1 | Publicar https://2notasudi.com.br/privacidade → **200** | Gustavo | [ ] |
| B2–B3 | Footer + página DPO nominal | Gustavo | [ ] |
| B7 | Purge Cloudflare `/privacidade` | Gustavo | [ ] |
| C1–C5 | Bot welcome / consent hash / LobeChat → v3 | n8n + dev + front | [ ] |
| D4 | Audit `privacy_policy.v3.published` | dev / lgpd | [ ] |
| F | Critérios “publicado com sucesso” todos verdes | DPO sign-off | [ ] |

> DPA MiniMax **não** bloqueia publish v3 se o texto indicar MiniMax “READY_TO_SIGN / em tramitação”. Após assinatura real, patch menor no § MiniMax → SIGNED.

### 3.3 RIPD v1.4 — SIGN HOLD (checklist DPO no addendum §5)

| # | Ação | Quem | Done |
|---|------|------|------|
| 1 | DPO nominal no RIPD base (`docs/ripd.md`) | DPO | [ ] |
| 2 | DPA MiniMax assinado + vault (depende §3.1) | SUI | [ ] |
| 3 | Sign-off formal addendum 1.4 (DPO + Gustavo) | SUI | [ ] |
| 4 | Revisão trimestral agendada | DPO | [ ] |

### 3.4 Data inventory — agent DONE; residual ops

| # | Ação | Quem | Done |
|---|------|------|------|
| 1 | Estender scanner: `whatsapp_number`, `telegram_chat_id`, `consentimento_ip`, `ip_truncated` | cartorio-lgpd / dev | [ ] |
| 2 | Confirmar job retenção 03:00 BRT cobre `lgpd_consent_log` | cartorio-dev + lgpd | [ ] |
| 3 | Cross-check finalidades inventory ↔ Privacy v3 ↔ RIPD após publish | DPO | [ ] |

---

## 4. Cross-ref SUI_CHECKLIST_G7_WAVE28 — seção LGPD

Fonte: [`docs/SUI_CHECKLIST_G7_WAVE28.md`](SUI_CHECKLIST_G7_WAVE28.md)

| SUI § | Título | Task | Agent-side | Humano residual (resumo) |
|-------|--------|------|------------|--------------------------|
| §1 agent | DPA READY_TO_SIGN package | G7.19.T2 | **[x]** | — |
| §1 agent | Privacy v3 draft + publish checklist | G7.19.T3 | **[x]** | — |
| §1 agent | RIPD v1.4 + inventory 25 PII fields | G6.C / G7.19.T4 | **[x]** | — |
| **§11** | DPA MiniMax assinar | G7.19.T2 | package [x] | placeholders · DD · PDF · flag · audit · matrix |
| **§12** | Privacy Policy v3 publish | G7.19.T3 | draft [x] | A1–F · URL 200 · bot v3 · audit publish |
| Matriz #13 | DPA MiniMax signed | G7.19.T2 | READY [x] | **[ ] SUI** |
| Matriz #14 | Privacy v3 published | G7.19.T3 | draft [x] | **[ ] SUI** |

Ordem SUI sugerida (já no checklist Wave 28):

```
… → 12 DPA sign  →  13 Privacy publish  →  14 start 72h window
```

LGPD pode rodar **em paralelo** a DNS/token/QR (não bloqueia rede), mas **72h stability** e tag MVP devem preferir Privacy publicada + DPA em tramitação documentada (ou SIGNED).

---

## 5. Gate legal mínimo vs go-live técnico

| Critério | Mínimo go-live bot | Ideal MVP v0.7.0-g7 |
|----------|--------------------|---------------------|
| PII 3 camadas + testes | **Obrigatório** (code) | idem |
| HITL protocolo DRAFT | **Obrigatório** | idem |
| Privacy Policy publicada v3 | **Recomendado** antes tráfego titular real | **Obrigatório** |
| DPA MiniMax SIGNED | Preferir não enviar DATASENSITIVE a MiniMax até assinar | **Obrigatório** se MiniMax em path titular |
| RIPD 1.4 sign-off DPO | Recomendado | **Obrigatório** audit ANPD-ready |
| Inventory refresh | **[x]** Wave 26 | manter cadência trimestral |
| Consent hash = versão publicada | Após B1 | **Obrigatório** |

---

## 6. Secrets safety (Wave 29 A3 scan)

Escopo: `docs/*G7*` + `.harness/memory/lesson-20*.md`  
Patterns: `sk-`, `sk-cp-`, `lin_api_`, `ghp_`, `xox*`, `AKIA*`, BotFather long digit tokens.

| Resultado | Detalhe |
|-----------|---------|
| **CLEAN (no live secrets)** | Nenhum `lin_api_*`, `ghp_*`, `xox*`, `AKIA*`, `sk-cp-*`, `sk-<20+ alnum>`, nem token BotFather `digits:AA…` real |
| False positives documentados | Placeholders `sk-xxxx` em runbooks LobeChat/OpenClaw/SUI (instrução “substituir placeholder”, **não** valor real) |
| False positives documentados | Menções textuais “@BotFather”, `token`, `123456789:AA...` como **formato exemplo** em AlertManager/SUI |
| False positives documentados | Lesson-206 linha “não commitar tokens / `sk-*`” (meta-regra) |
| `scripts/check_no_literal_keys.py` (raiz) | **Ausente** — existe `backend/scripts/check_no_literal_keys.py` |
| `scripts/secrets_scan.py` | Disponível (G6.A.T6); patterns alinhados a pre-commit |

**Nunca** colar token BotFather, `OPENAI_API_KEY` real, operator token OpenClaw ou `EVOLUTION_API_KEY` nestes docs G7.

---

## 7. O que o agent **não** faz (explícito)

1. Assinar ou simular assinatura em blocos DPA / Privacy / RIPD.  
2. Publicar HTML em `2notasudi.com.br/privacidade`.  
3. Setar `LGPD_DPA_MINIMAX_SIGNED=true` em produção.  
4. Preencher CNPJ, nome de DPO real ou telefone real em commit (placeholders `[NOME_DO_DPO]` permanecem até SUI).  
5. Marcar matriz SUI #13/#14 como done sem evidência humana.  
6. Commitar secrets (este painel e scan reforçam a regra).

---

## 8. Próximo passo recomendado (humano, ~ordem)

1. **Gustavo + DPO:** preencher identidade cartório (CNPJ, DPO) em DPA + Privacy rascunho (mesmo dados).  
2. **DPO:** due diligence MiniMax + iniciar assinatura (§3.1).  
3. **Gustavo:** publish checklist A→B→C (site 200 + bot hash) — pode começar em paralelo se MiniMax “em tramitação” no texto.  
4. **DPO:** sign-off RIPD 1.4 após DPA path claro.  
5. Tick §11 / §12 em `SUI_CHECKLIST_G7_WAVE28.md` + audit log events.  
6. Iniciar janela 72h (`STABILITY_WINDOW_72H_G7.md`) quando demais HOLDs de rede/canal permitirem.

---

## 9. Histórico deste painel

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 2026-07-17 | Dashboard go-live LGPD G7 Wave 29 A3 — cross-index DPA/Privacy/RIPD/inventory + SUI §11–12 + secrets scan CLEAN | cartorio-lgpd |

---

**Modified by Gustavo Almeida**
