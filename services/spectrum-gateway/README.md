# Cartório Spectrum Gateway (scaffold / contracts)

**Runtime canônico de iMessage do Cartório OS NÃO é este processo.**

| Papel | Path / processo |
|---|---|
| **Runtime canônico (LIVE)** | Hermes profile `cartorio` — LaunchAgent `ai.hermes.gateway-cartorio` + Photon sidecar `127.0.0.1:8793` no projeto Spectrum `CARTORIO BOT TEST` |
| **Este tree** | `services/spectrum-gateway` — contratos tipados, guardrails, health contract e scaffold Spectrum-TS (referência). **Não** subir contra o mesmo `PHOTON_PROJECT_ID` do Hermes cartorio (rouba a stream). |
| **Fantasma** | `apps/spectrum-gateway` — **ABSENT** (nunca recriar como segundo runtime) |

Authority layer continua na API FastAPI + FastMCP. Este gateway (se algum dia for usado como consumer) só normaliza transporte e delega.

## Segurança operacional

- Linha shared/test = `inbound_scope=allowlist` (LIMITED_INBOUND). `PHOTON_ALLOW_ALL_USERS` / `ALLOW_ALL_INBOUND` **não** abrem a linha ao público — só afetam users já registrados no provider.
- `SPECTRUM_LINE_MODE=public` falha de propósito até existir linha dedicada Business com inbound público documentado.
- Nenhum segredo versionado. Phantom Panel permanece stub.
- PII scrub na saída; protocolos/atos jurídicos só via API + HITL.

## Verificação local

```bash
npm install
npm run typecheck
```

`CONNECTED` (Photon) ≠ `OPERATIONAL`. OPERATIONAL exige REAL_E2E_PASS: iPhone → linha → Hermes cartorio → resposta → iPhone.
