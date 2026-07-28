# Lesson 287 — Tool call INLINE do MiniMax vaza markup `]<]minimax[>` em prod (bulk 10K)

> Data: 2026-07-28 · Severidade: **P0** (internal vocab leak customer-facing) ·
> Status: fix commitado `57653357` (push feito; deploy VPS pendente)

## Sintoma

Campanha bulk 10K (smoke emol N=60 contra prod `/api/v1/pietra/chat/completions`):
21/60 respostas FAIL com `hard_fail:'minimax'`. Transcripts mostram o upstream
MiniMax emitindo o tool call como **markup inline no content**:

```
Vou consultar a tabela…]<]minimax[>[<tool_call>
]<]minimax[>[<invoke name="cartorio_calcular_emolumento">]<]minimax[>[<act>procuracao]<]minimax[>[</act>]…
```

## Impacto triplo

1. **Internal vocab leak** — "minimax", "<invoke>", "<tool_call>" chegam crus ao
   cliente (viola AGENTS.md P0: nunca revelar modelo/infra).
2. **REGRA DE OURO morta** — o caller (Hermes gateway) só executa tools quando
   recebe `tool_calls` **estruturados**; com markup inline nenhuma tool roda e
   o cliente fica sem valor ou com promessa ("vou consultar…") sem entrega.
3. **Checker passa a falhar corretamente** — hard_fail_patterns detecta "minimax".

## Causa raiz

`_strip_think_tags` só cobria `<think>/<reasoning>`. Nada no pipeline tratava o
delimitador `]<]minimax[>[` nem markup de tool call inline (o thin-shell só
conhecia o campo estruturado `tool_calls`).

## Fix (57653357)

- `cartorio_agent._extract_inline_tool_calls(text)` → `(texto_limpo, tool_calls)`:
  - Markup completo → sintetiza tool_call estruturado (`finish_reason=tool_calls`,
    caller executa via MCP — REGRA DE OURO restaurada).
  - Markup truncado (max_tokens) → remove tudo a partir do delimitador; nunca
    sintetiza call quebrado.
  - Params: `<invoke name="p">v</invoke>` (aninhado) e tags soltas `<act>/<ato>…`.
- `pietra.py`: conversão inline→estruturado antes do branch de tool_calls.
- 8 regression tests em `tests/test_pietra_inline_tool_calls.py` (transcripts
  reais de prod como fixtures — falham se regredir).

## Regras permanentes

1. **Todo texto que sai de LLM para canal customer-facing passa por 3 strips**:
   think/reasoning, markup inline de tool call, identity guard. Novo provider?
   Testar com probe que provoca tool call (pergunta de preço) e grepar o content
   por `[a-z]*\[>\[<` e `<invoke`.
2. **Smoke de campanha pega o que suites não pegam**: suites mockam
   `_chat_completion`; só tráfego real contra prod expõe o markup do upstream.
   Rodar batch pequeno (N≥50) em prod ANTES de campanha grande.
3. **Truncamento de max_tokens gera markup quebrado** — parser de markup inline
   DEVE ter caminho de "incompleto → strip", nunca assumir fechamento.

## Infra da campanha 10K (mesma sessão)

- `scripts/imessage_10k_generator.py` — corpus 10.000 casos únicos (16 categorias
  da spec, seed 42, variação combinatorial; protege keywords de `expected` no typo).
- `scripts/imessage_bulk_http_runner.py` — bulk HTTP async multi-turn com
  checkpoint/resume (JSONL), rps limit, gates Seção 7. Modo híbrido: bulk HTTP
  + amostra live iMessage no `imessage_e2e_runner.py`.
- `artifacts/imessage/corpus_10k.jsonl` (commitado, reproduzível).

## Pendências

- [ ] Deploy VPS do commit 57653357 + re-probe emol (esperado: 0 hard_fail minimax,
      finish_reason=tool_calls nas perguntas de preço).
- [ ] Campanha full 10K híbrida pós-deploy.
- [ ] Avaliar se upstream suporta `tool_choice="required"` para forçar canal
      estruturado e reduzir emissão inline na fonte.
