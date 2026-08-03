# Relatório de Drift & Conciliação · Cartório Super Graph

**Data:** 2026-08-03  
**Status:** APROVADO (FLASH + PRO Review)

## Conciliação de Desvios Detectados

1. **Drift de Ingestão de Conhecimento:**
   - *Estado no Briefing/Histórico:* Suposição de necessidade de construir do zero um pipeline de conhecimento.
   - *Estado Real no Repo/ZIP:* O pipeline privado já processou as 90 fontes (hash `ce236ba3...`), 3.087 unidades sanitizadas, `published_eligible=0`.
   - *Resolução:* Revalidar e estender o pipeline existente em `app/services/conhecimento_pipeline.py`. Não recriar pipeline concorrente.

2. **Drift de Camadas de Preço:**
   - *Estado no Briefing/Histórico:* Suspeita de divergência de valores de emolumentos entre backend e tabelas do ZIP (ex. R$ 11,21 vs R$ 11,61).
   - *Estado Real no Repo/ZIP:* Há duas camadas legítimas: `REGULATORY_TJMG` (Portaria 8.664/2025) vs `OPERATIONAL_POS_2NOTAS` (ZIP 79 linhas com decomposição de ISS/RECOMPE/fundos).
   - *Resolução:* Manter modelo dual explícito. Nenhuma camada sobrescreve a outra. Anomalia de R$ 0,01 no ISS da faixa 1606-3 registrada em `CONFLICT_REGISTRY_2026.csv`.

3. **Drift do Arquitetura Lark:**
   - *Estado no Briefing/Histórico:* Coexistência potencial de standalone Flask, routers alternativos ou múltiplos processos.
   - *Estado Real no Repo/ZIP:* Apenas Hermes por WebSocket deve ser o consumidor ativo. Bloqueadores anteriores: falta de prova do evento P2 `im.message.receive_v1` e ocorrência de `processor not found` no logs legados.
   - *Resolução:* Garantir 1 réplica, 1 conexão, consumidor único no Lark, verifier P2 e fallback seguro.

4. **Drift de Git / Workflow:**
   - *Estado no Briefing/Histórico:* Instruções antigas de push direto em master.
   - *Estado Real:* Regra estrita: branch a partir de `master`, worktree isolada, zero push direto, PR + review independente + `make qa` verde.

