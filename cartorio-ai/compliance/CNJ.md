# cartorio-ai · compliance/CNJ.md

Exportação de dados para o **CNJ** (Padrão de interoperabilidade / logs de proteção de dados) e
garantias LGPD associadas. Código: `backend/app/api/v1/cnj_export.py` + `app/services/cnj_export.py`.

## Endpoint massivo

`GET /api/v1/lgpd/cnj-exports/massive-dump` (implementado em 2026-07-20 — commits `ff599aa`,
`0d15da6`, `6c029fc`):

- **AuthN/AuthZ**: `X-API-Key` do cartório (`require_cartorio_api_key`) **+** JWT com role DPO
  (`require_dpo_role`). Sem ambos → 401/403.
- **Audit gate**: antes de qualquer byte, registra `cnj.export.massive_dump` com `actor_id=sub`
  do DPO; falha no audit → 500 `AUDIT_FAILURE` e **nenhum dado sai**.
- **Streaming**: `StreamingResponse` + `yield_per(1000)` ordenado por `audit_log.id` — não estoura
  RAM em dump massivo. `Content-Disposition: attachment; cnj-lgpd-aggregated-<id>.json`.
- **Scrub**: cada payload passa por `pii.scrub` antes de serializar — PII/IP permanecem mascarados
  no pacote, preservando `id`, `actor_id`, `actor_type`, `action` e a **cadeia de hashes**.

## Fluxo com pedido formal (dupla aprovação DPO)

Além do dump ad-hoc, o router expõe o fluxo com pedido: `create_request` → `approve_request`
(dupla aprovação) → `build_approved_export` → `get_generated_export`, com status, período de
referência e hashes `report_sha256`/`manifest_sha256` no payload de status. Erros de domínio
viram `CNJ_EXPORT_INVALID_STATE` (404 inexistente / 409 conflito) sem detalhes internos.

## Garantias exigidas (G9 Squads 07–08)

1. Streaming sob volume alto com memória estável e JSON válido (G9.07.T2).
2. Audit gate testado — zero byte vazado em falha (G9.07.T3).
3. JWT DPO obrigatório com testes 401/403 (G9.08.T1).
4. **Verificação independente da hash chain** SHA256+HMAC sobre o pacote (G9.08.T2).
5. **Relatório de logs de proteção de dados** (acessos, exportações, mascaramentos) derivado do
   audit log (G9.08.T3) — é a peça que o CNJ consome como evidência de boas práticas LGPD.
6. RIPD atualizado com o fluxo (G9.08.T4); drill Art. 18 periódico (G9.21.T1).

## Base legal operacional

LGPD Art. 18 (direitos do titular — services `lgpd*`), Art. 37 (registro de operações — audit log),
Art. 46/47 (segurança e boas práticas — PII scrub 3 camadas + hash chain). Exportação CNJ é
cumprimento de obrigação legal/regulatória (Art. 7º, II c/c Art. 11, II, a).
