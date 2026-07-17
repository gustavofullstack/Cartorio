# Privacy Policy v3 — Publish Checklist (G7.19.T3)

**Rascunho fonte:** `docs/PRIVACY_POLICY_V3_G7.md`  
**Complemento técnico:** `docs/lgpd/policy/D23-site-privacy-policy-v3.md`  
**Legado:** `docs/privacy-policy.md` (v1.1)  
**Status:** HOLD-GUSTAVO — agente **não** publica no site  
**Data:** 2026-07-17 · Wave 27  

---

## Objetivo

Publicar a **Política de Privacidade v3** em https://2notasudi.com.br/privacidade
(e espelhos: footer, bot welcome, LobeChat banner), com versionamento, prova de
consentimento e alinhamento ao DPA MiniMax READY_TO_SIGN / demais operadores.

---

## A. Pré-publicação (conteúdo)

| # | Item | Responsável | Done |
|---|------|-------------|------|
| A1 | Preencher `[NOME_DO_DPO]`, `[TELEFONE_DO_DPO]`, CNPJ, endereço em `PRIVACY_POLICY_V3_G7.md` | Tabelião + Gustavo | [ ] |
| A2 | Revisar lista de sub-processors e status DPA vs `docs/LLM_DPA_MATRIX.md` | cartorio-lgpd / DPO | [ ] |
| A3 | Confirmar retenções (365d conversa / 90d LLM / 5y audit / Prov. 74) batem com job `retencao_scheduler` | cartorio-dev + lgpd | [ ] |
| A4 | Aprovação escrita DPO + Tabelião (assinatura digital ou e-mail formal) | SUI | [ ] |
| A5 | Gerar PDF/HTML “versão pública” a partir do markdown (sem paths internos de repo se possível) | Gustavo / front | [ ] |
| A6 | Calcular SHA-256 do texto final publicado (prova do que foi apresentado no consent) | cartorio-lgpd | [ ] |

---

## B. Publicação no site (HOLD-GUSTAVO)

| # | Item | Onde | Done |
|---|------|------|------|
| B1 | Publicar HTML em **https://2notasudi.com.br/privacidade** | CMS / static site / Traefik host | [ ] |
| B2 | Atualizar link no **footer** de todas as páginas | site | [ ] |
| B3 | Atualizar página DPO **https://2notasudi.com.br/dpo** (nome, e-mail, telefone) | site | [ ] |
| B4 | Espelho opcional: `politica-privacidade.2notasudi.com.br` se ainda em uso (ver RUNBOOK_VPS) | DNS/Traefik | [ ] |
| B5 | `curl -fsS -o /dev/null -w "%{http_code}\n" https://2notasudi.com.br/privacidade` → **200** | Gustavo | [ ] |
| B6 | Verificar TLS válido (Let's Encrypt) e redirect HTTP→HTTPS | SRE / Gustavo | [ ] |
| B7 | Cache Cloudflare: purge path `/privacidade` após publish | Gustavo | [ ] |

---

## C. Integração bot / consentimento

| # | Item | Onde | Done |
|---|------|------|------|
| C1 | Atualizar mensagem welcome (n8n / Evolution / Telegram) com **versão 3.0** + URL | cartorio-n8n | [ ] |
| C2 | Atualizar hash da política no registro de consentimento (Supabase / API) | cartorio-dev | [ ] |
| C3 | Banner LobeChat / widget web aponta para v3 | front / OpenClaw | [ ] |
| C4 | Termo `docs/consent.md` — bump de versão se texto material mudou; re-opt-in se exigido | cartorio-lgpd | [ ] |
| C5 | Comando `/lgpd` e fluxos Art. 18 ainda respondem e citam v3 | smoke Telegram/Web | [ ] |

---

## D. API e compliance interno

| # | Item | Done |
|---|------|------|
| D1 | Endpoint/health LGPD (se houver página `/lgpd` na API) retorna referência v3 | [ ] |
| D2 | Arquivar v1.1/v2 em `docs/archive/` com data (já existe padrão `privacy-policy_v1.0_*`) | [ ] |
| D3 | Atualizar `docs/privacy-policy.md` header → “substituída pela v3 publicada em …” **após** B1 | [ ] |
| D4 | Entrada no audit log: `privacy_policy.v3.published` (ator, hash, URL) | [ ] |
| D5 | Atualizar RIPD / inventory se finalidades mudaram materialmente | [ ] |

---

## E. Comunicação e go-live

| # | Item | Done |
|---|------|------|
| E1 | Aviso no chatbot (broadcast leve) se mudança material | [ ] |
| E2 | E-mail a base com consentimento de marketing (se houver) — só se mudança material | [ ] |
| E3 | Atualizar `docs/G7_SUI_WAVE14_CHECKLIST.md` / SUPER_PLANO residual | [ ] |
| E4 | Registrar em `.harness/memory/MEMORY.md` data de publicação real | [ ] |

---

## F. Critérios de “publicado com sucesso”

- [ ] URL pública 200 + conteúdo v3 visível  
- [ ] DPO nominal e telefone **sem** placeholder na página pública  
- [ ] Bot exibe link v3 no fluxo de consentimento  
- [ ] Hash SHA-256 do texto publicado armazenado  
- [ ] Audit log com evento de publicação  
- [ ] SUPER_PLANO G7.19.T3 residual SUI fechado  

---

## G. Rollback

Se a v3 publicada contiver erro jurídico material:

1. Restaurar HTML da versão anterior no mesmo path;  
2. Purge Cloudflare;  
3. Reverter hash de consentimento no bot para a versão anterior;  
4. Audit log `privacy_policy.v3.rollback`;  
5. Comunicar DPO + Tabelião em ≤ 24h.

---

## Ordem sugerida (≈ 45–90 min humanos)

```
A1–A4 → A5–A6 → B1–B7 → C1–C5 → D1–D5 → E1–E4 → F
```

**Dependência cruzada:** se DPA MiniMax ainda não assinado, a v3 **pode** ser
publicada com status “READY_TO_SIGN / em tramitação” (texto já prevê isso na §7.3).
Após assinatura real, republicar parágrafo MiniMax como **SIGNED** (patch menor).

---

**Modified by Gustavo Almeida + cartorio-lgpd — G7 Wave 27 (publish HOLD-GUSTAVO)**
