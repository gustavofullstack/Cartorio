# CARTORIO

Núcleo de domínio do 2º Serviço Notarial de Uberlândia (2026-07-20).

## Serventia

- **2º Cartório de Notas de Uberlândia/MG** — domínio `2notasudi.com.br`.
- Atos: escrituras, procurações, atas notariais, reconhecimento de firma, autenticações, certidões.
- Base legal: Provimentos CNJ, Lei 8.935/94, tabela de emolumentos MG 2026.

## Regras de ouro do domínio

1. **HITL obrigatório**: protocolo nasce `DRAFT`; escrevente valida antes de qualquer processamento.
2. Bot **nunca** decide: isenção, urgência, validação jurídica, emissão de certidão/escritura.
3. Estimativas de emolumento são informativas (`emolumento.py`, tabela MG 2026) — valor final só após conferência humana.
4. Documentos do usuário: checklist por ato (`cartorio/DOCUMENT_CHECKLISTS.md`); pendências registradas, nunca inventadas.

## Serviços e prazos

- Certidões (nascimento/casamento/óbito via interligação), escrituras (compra/venda, procurações, atas).
- Prazos e níveis de serviço em `cartorio/DEADLINES.md` e `cartorio/SERVICE_LEVELS.md`.
- Agendamento presencial via `/agendar` → `agendamento` model → confirmação humana.

## Compliance

- LGPD-by-design: minimização, finalidade, retenção programada (03:00 BRT), direitos Art. 18 completos.
- Audit log tamper-evident (SHA256 chain + HMAC) para todo ato sensível — exigência CNJ.
- Export massivo CNJ: endpoint DPO com streaming + scrub + hash do pacote (commits `ff599aa`+).
- Recusas e exceções documentadas em `cartorio/REFUSALS.md` e `cartorio/EXCEPTIONS.md`.
