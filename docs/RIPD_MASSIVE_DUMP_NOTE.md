# RIPD — Nota: Massive-Dump CNJ (G9.S4.T10 / E3.08)

> **Status do sign-off formal LGPD: `BLOCKED_HUMAN`** — esta nota mapeia o
> fluxo e os controles técnicos. O Relatório de Impacto à Proteção de
> Dados Pessoais (RIPD, LGPD art. 38 e Resolução CD/ANPD nº 18/2024)
> exige elaboração e assinatura pelo **encarregado (DPO) humano**;
> automação não substitui o sign-off.

## Fluxo mapeado

`GET /api/v1/lgpd/cnj-exports/massive-dump` — exportação em massa do
audit log (padrão CNJ), streaming `yield_per(1000)`, cadeia SHA256 + HMAC
preservadas verbatim para verificação independente pelo CNJ.

| Etapa | Controle | Onde |
| --- | --- | --- |
| **Base legal** | LGPD art. 7º, VI (exercício regular de direitos em processo judicial/administrativo) + art. 11, II, "d" — cumprimento de obrigação legal perante o CNJ (Provimento 100/2020 e corregedoria). Finalidade estrita: fiscalização notarial. | `app/api/v1/cnj_export.py` |
| **Autorização (dual security)** | API key **e** JWT com role DPO; `sub` obrigatório; 401/403 fail-closed; OpenAPI declara dual security. | `require_cartorio_api_key` + `require_dpo_role` |
| **Gate de audit (fail-closed)** | Falha ao registrar `cnj.export.massive_dump` no audit log → **500 sem body**, rollback, dump não inicia. Quem exporta fica registrado. | `massive_dump_cnj` |
| **Minimização** | Scrub por folha (`_scrub_payload_value`) no payload e nos campos top-level identificadores (`actor_id`, `resource`, `user_agent`, `request_id`, `canal`); IP sai apenas truncado (`/24`, `/32`). Números sem PII permanecem numéricos; JSON nunca trunca. | `app/api/v1/cnj_export.py` + `app/services/pii.py` |
| **Integridade** | `prev_hash`/`hash`/`hmac_signature`/`hmac_kid` saem verbatim — scrub NUNCA toca campos de integridade. | idem |
| **Canary PII** | Teste tripwire prova que CPF canário nunca sai raw em nenhuma superfície (scrub, bot output, stream massive-dump). | `tests/test_cnj_canary_g9.py` |
| **Relatório de proteção** | Agregados (acessos/exportações/mascaramentos/falhas auth/janela) a partir do audit log, RESTRICTED_AGGREGATED. | `app/services/cnj_protecao.py` + `docs/CNJ_PROTECAO_DADOS.md` |

## Riscos residuais (para o RIPD formal)

1. Volume do dump é integral do audit log — mitigação: acesso DPO-gated,
   audit-fail-closed, transmissão externa automática **vedada** por design
   (download local apenas).
2. Regex de PII tem limitações conhecidas (nomes livres, endereços) —
   mitigação: 3 camadas de scrub + HITL + retenção 365d (ver
   `app/services/pii.py`, "LIMITAÇÕES CONHECIDAS").
3. Retenção do artefato baixado pelo DPO é processo humano (fora do
   sistema) — cobrir no procedimento operacional do RIPD.

## Pendências para sign-off

- [ ] Elaboração do RIPD completo pelo encarregado (DPO) — **BLOCKED_HUMAN**.
- [ ] Aprovação formal do fluxo massive-dump pelo tabelião — **BLOCKED_HUMAN**.
- [ ] Procedimento de custódia/destruição do artefato baixado — **BLOCKED_HUMAN**.
