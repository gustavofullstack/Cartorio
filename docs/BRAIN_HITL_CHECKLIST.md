# Checklist HITL — Corpus BRAIN ConhecimentoInstitucional

**Batch:** `2026-07-31-ce236ba32b01`  
**Estado:** `PENDING_HUMAN_VALIDATION`  
**Publicação automática:** proibida  
**Hermes/prod:** intocados  
**T4/T5:** não declarados

## Pré-requisitos

- [x] Ingest offline (`is_blocked=false`, 90/90, 3.087 units)
- [x] Classificação local (`classification.sanitized.json`)
- [x] Fila HITL (`hitl_queue.sanitized.json`) gerada
- [x] Testes unitários do bounded context verdes
- [ ] Revisor humano designado (escrevente / tabelião)
- [ ] Parecer `cartorio-lgpd` para itens NORMATIVO / PII residual

## Como revisar (somente metadados)

```bash
# Regenerar fila (local)
uv run --project backend python scripts/brain_corpus_hitl_queue.py
# stdout: contagens por banda P0–P3, sem nomes de arquivo
```

Artefato privado:  
`.private/brain-ingest-quarantine/2026-07-31-ce236ba32b01/derived/hitl_queue.sanitized.json`

Cada item expõe apenas:
- `source_id` (SHA-256 opaco)
- `document_type_code` sugerido
- `priority_band` (P0_critical … P3_low)
- `vote_histogram`, `ambiguous`, `ocr_requires_human_review`
- `decision` ∈ `{PENDING, APPROVE, REJECT, RECLASSIFY}`

**Proibido na rationale:** texto bruto, CPF/RG, e-mail, telefone, path, nome de arquivo.

## Ordem de revisão sugerida

1. **P0_critical** — `OUTROS_ATOS`, normativos, OCR, ambíguos  
2. **P1_high** — testamento, inventário, usucapião, família  
3. **P2_medium** — escrituras, procurações, firmas  
4. **P3_low** — checklists / listas de documentos

## Decisões

| decision | Efeito no lifecycle | Publica no BRAIN? |
|---|---|---|
| `APPROVE` | → `APPROVED` | **Não** (passo separado) |
| `REJECT` | → `REJECTED` (terminal) | Não |
| `RECLASSIFY` | permanece pending; anotar tipo correto | Não |
| `PENDING` | sem mudança | Não |

Publicação (`APPROVED` → `PUBLISHED`) só após:
1. Item `APPROVE` registrado com `reviewer_id` + rationale ≥ 5 chars  
2. Sign-off DPO/LGPD separado, da mesma versão
3. `t4_authorized=true` somente em ambiente isolado; recuperação live continua desligada

API de apoio (código puro, sem rede):

```python
from app.services.conhecimento_validacao import (
    registrar_decisao_humana,
    publicar_versao,  # só depois de APPROVED + autorização
)
```

## Critérios de aceite por item

- [ ] Tipo documental correto (ou RECLASSIFY com código do catálogo)
- [ ] Conteúdo ainda vigente (senão REJECT)
- [ ] Sem PII desnecessária para o uso informativo
- [ ] Escopo de uso: informativo / checklist / cálculo / normativo
- [ ] reviewer_id identificável (matrícula ou papel, sem dado pessoal extra)

## Rollback

- Item publicado por engano → `revogar_publicacao` (estado `REVOKED`)
- Lote inteiro → manter `automatic_promotion_allowed=false` e não chamar publish
- Audit/trace preservados; sem mutação histórica

## Sign-off

| Papel | Nome | Data | Resultado |
|---|---|---|---|
| Escrevente / Tabelião | _pendente_ | | |
| cartorio-lgpd | _pendente_ | | |
| Ops (T4 only) | _não aplicável ainda_ | | |

---

Assinatura pipeline: **@Codex/hitl_queue** — geração automática; decisão humana obrigatória.
