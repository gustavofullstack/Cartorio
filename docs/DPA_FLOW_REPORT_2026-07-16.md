# DPA Signing Flow Tracker

**Data**: 2026-07-16T15:42:43.425343+00:00

## Resumo

| Status | Count |
|---|---|
| ready_to_sign | 1 |
| pending_provider | 4 |
| signed | 4 |

> **Update 2026-07-17 (G7 Wave 27):** MiniMax passou de `pending_gustavo` → **`ready_to_sign`**.
> Pacote: `docs/DPA_MINIMAX_READY_TO_SIGN_G7.md`. Assinatura real continua SUI.

## DPA Matrix

| DPA | Status | Assinado | Renewal | Dias | Notes |
|---|---|---|---|---|---|
| MiniMax | 📝 ready_to_sign | - | 2027-01-01 | — | G7.19.T2 pacote READY_TO_SIGN. HOLD-GUSTAVO assinar + PDF `docs/lgpd/dpa_minimax.pdf` |
| Hostinger | ✅ signed | 2026-01-05 | 2027-01-05 | 172d | Contrato master Hostinger + addendum DPA. |
| Cloudflare | ✅ signed | 2026-01-10 | 2027-01-10 | 177d | Cloudflare DPA publico ja vigente. |
| opencode-go | ✅ signed | 2026-01-15 | 2027-01-15 | 182d | LGPD-008. Assinado Gustavo + opencode-go Inc. |
| DeepSeek | ✅ signed | 2026-02-20 | 2027-02-20 | 218d | LGPD-014. Assinado via DocuSign. |
| mimo | 🚧 pending_provider | - | - | - | mimo Corp sem DPA publico. Bloqueado ate assinar. |
| mistral-free | 🚧 pending_provider | - | - | - | Mistral.ai DPA tier free limitado. Bloqueado. |
| openrouter-free | 🚧 pending_provider | - | - | - | OpenRouter free tier. Bloqueado. |
| gemini-free | 🚧 pending_provider | - | - | - | Gemini free tier. Bloqueado. |

## Alertas

- 📝 **MiniMax**: READY_TO_SIGN — pacote G7 pronto; **assinatura SUI** Gustavo+DPO+MiniMax
- 🚧 **mimo**: Aguardando provider (mimo/mistral/openrouter/gemini)
- 🚧 **mistral-free**: Aguardando provider (mimo/mistral/openrouter/gemini)
- 🚧 **openrouter-free**: Aguardando provider (mimo/mistral/openrouter/gemini)
- 🚧 **gemini-free**: Aguardando provider (mimo/mistral/openrouter/gemini)

---

**Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 7 + G7 Wave 27 (MiniMax READY_TO_SIGN)**