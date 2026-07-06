# Plano · PDF v3 ULTRA — Relatório Quinzenal Felipe & Djalma (22/06 → 06/07/2026)

> **Modo**: Plan → execução após GO.
> **Decisão de escopo (já tomada)**: **MELHORAR v2 existente** (não refazer do zero). Manter HTML/PDF/PPTX atuais, **incrementar** com animações, timeline minuto-a-minuto, página de providers FREE expandida, % de conclusão visual.
> **Decisão de providers (já tomada)**: **DOCUMENTAR TODOS** os 20+ providers FREE citados no prompt, mesmo os que não estão integrados, listando cada um com contexto/status.
> **Brand**: fundo WHITE CLEAN, glass, linear, Poppins, espaçamento generoso. Logos TriQ Hub reais já incorporadas.
> **Modified by**: Gustavo Almeida · 06/07/2026

---

## 1. Resumo

O PDF v2 (`docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf`, 1MB, 2823 linhas HTML, 33 sections, 4 apêndices, capa TriQ Hub oficial) já é estruturalmente completo. O Gustavo sinalizou que "TA UMA MERDA" — entendo que é por:

1. **Animações** — o `counters.js` existe mas o CSS provavelmente tem animações fracas/inexistentes no estado estático do PDF.
2. **Falta de minuto-a-minuto** — a timeline está por dia (`id="day-2026-06-22"` etc.), não mostra os segundos/minutos dentro de cada turno.
3. **Providers FREE mal documentados** — apêndice C tem 8 lessons, mas a página `id="apendice-provider"` precisa ser expandida com TODOS os 20+ mencionados no prompt, com % de uso e status.
4. **% de conclusão pouco visual** — existe `data-target` em progress fills mas a renderização é fraca (linha fina).
5. **Comparação prompt×realidade** — `divergencias.json` tem 8+ itens, mas não há página dedicada "O que o PROMPT.MD dizia vs o que temos".

**Estratégia v3** = 7 melhorias cirúrgicas sobre os arquivos existentes, sem mexer no que já funciona (33 sections, 4 SVGs, capa TriQ Hub, dados quantitativos).

---

## 2. Estado Atual (validado em exploração)

| Item | Caminho | Estado |
|---|---|---|
| HTML fonte | `docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.html` (2823 linhas, 33 sections) | ✅ Existe |
| PDF | `docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf` (1.0MB) | ✅ Existe |
| PPTX | `docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pptx` (58KB) | ✅ Existe |
| Tema CSS | `docs/reports/assets/css/theme.css` (white clean, glass, Poppins, variáveis CSS) | ✅ Existe |
| Logos TriQ Hub | `docs/reports/assets/img/logo-triqhub-{colorida,black}.{png,svg}` | ✅ 4 arquivos |
| Charts SVG | `donut-cobertura.{png,svg}`, `heatmap-commits.{png,svg}`, `stack-squads.{png,svg}`, `stack-tokens-dia.{png,svg}` | ✅ 4 charts |
| Data JSONs | `build/data/*.json` (16 arquivos: kpis, services, squads, timeline, heatmap, tokens_day, coding_plans, costs, divergencias, lessons, lgpd, pendencias, runbook, cobertura, squads_chart, tasks) | ✅ 16 |
| Scripts build | `extract_v2.py`, `render_v2.py`, `build_pdf.py`, `build_pptx.py`, `svg_charts.py` | ✅ 6 scripts |
| Counters JS | `assets/js/counters.js` (animação KPI) | ✅ Existe |
| Logos TriQ Hub fornecidas pelo usuário | `~/Documents/TriQ Hub Docs/TriQ Hub Logo/` (4 arquivos: Colorida PNG/SVG, Black PNG/SVG, White - Fundo Preto PNG) | ✅ 5 arquivos disponíveis |
| Fontes Poppins TTF | `assets/fonts/Poppins-{Regular,Medium,SemiBold,Bold}.ttf` | ✅ 4 |
| Plans anteriores | `.trae/documents/PLAN_PDF_*.md` (4 planos) | ✅ Já feitos |
| Evidence | `.trae/documents/evidence_pdf.json` (854 commits, 502k insertions) | ✅ Atualizado |

**Conclusão da exploração**: 90% do trabalho já está feito. Faltam 7 melhorias focadas.

---

## 3. Mudanças Propostas (7 cirúrgicas)

### Mudança 1 — Animações CSS reais (`assets/css/theme.css`)

**O que**: Adicionar keyframes visíveis no PDF (fade-up, slide-in, scale-in, progress-fill) que sejam capturáveis em vídeo/gif rápido.
**Por quê**: O `counters.js` anima números, mas o CSS não anima elementos estruturais (cards, KPIs, charts). O PDF sai estático e "sem vida".
**Como**:
- Adicionar `@keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }`
- Adicionar `@keyframes progressFill { from { width: 0%; } to { width: var(--target); } }`
- Adicionar `@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }` para status badges
- Adicionar `@keyframes slideInLeft { from { transform: translateX(-24px); opacity: 0; } to { transform: none; opacity: 1; } }` para timeline
- Aplicar `.fade-up { animation: fadeUp 0.6s ease-out both; }` com delays escalonados (`.fade-up:nth-child(1) { animation-delay: 0.1s; }` etc.)
- Aplicar `.progress-fill { animation: progressFill 1.2s ease-out both; }`
- Aplicar `.timeline-event { animation: slideInLeft 0.5s ease-out both; }`
- O `build_pdf.py` já força `style.opacity = '1'` em fade-up, então PDF mantém estado final correto. As animações servem para o HTML ao vivo (browser) e para o PPTX (via puppeteer screenshots com timing).

**Não quebrar**: build_pdf.py continua fazendo `style.opacity = '1'; style.transform = 'none'` em `.fade-up` — animação fica "congelada no final" no PDF, que é o correto.

### Mudança 2 — Página "Providers FREE — Catálogo Completo" (nova section)

**O que**: Adicionar nova `<section class="page" id="providers-catalogo">` com tabela detalhada dos 20+ providers mencionados no prompt do Gustavo.
**Por quê**: O prompt lista explicitamente: Minimax, Codex, Kimi, Gemini, ZED, OpenCode, ZCode, Trae, Antigravity, Claude Code, Copilot, Cline, Kilo, OpenRouter, Mistral, Groq, GLM-Z.AI, DeepSeek, Xiaomi, Google, Qwen 3.7, Mimo (Minimax), Meta AI, Kimi, NVIDIA, Grok, X.AI, AWS. O apêndice atual (`#apendice-provider`) tem só os 7 integrados via LiteLLM. Falta documentar os outros com status.
**Como**:
- Criar `build/data/providers_catalogo.json` com array de 20+ objetos: `{nome, categoria, status, integrado_via, calls_15d_estimado, latencia_media, observacao}`
- Categorias: `primary_llm`, `fallback_llm`, `editor_code`, `orchestrator`, `agent_platform`, `antigravity_suite`
- Status: `integrado_litellm` / `via_opencode_zen` / `planejado` / `nao_integrado`
- Adicionar função `render_providers_catalogo()` em `render_v2.py` (ou v3)
- Inserir `<section class="page" id="providers-catalogo">` antes de `#apendice-c-lessons`
- Tabela com colunas: Provider | Categoria | Status | Calls (15d) | Latência | Fonte/Plano

**Tabela alvo (mínimo 20 linhas)**:
| Provider | Categoria | Status | Calls 15d | Latência | Plano/Coding Plan |
|---|---|---|---|---|---|
| Minimax M3 | LLM primary | ✅ integrado opencode-zen | 750 | 2.1s | Minimax Coding Plan |
| Codex (GPT) | LLM primary | ✅ integrado opencode-zen | 450 | 2.4s | Codex Coding Plan |
| Kimi/Moonshot | LLM primary-alt | ✅ integrado opencode-zen | 300 | 2.8s | Kimi Coding Plan |
| Gemini 3.5 Flash | LLM multimodal | ✅ integrado opencode-zen | 375 | 1.9s | Gemini Coding Plan |
| Nemotron-3-Ultra | LLM fallback | ✅ integrado opencode_free_1 | 1800 | 3.2s | OpenCode Free 1 |
| Mimo v2.5 (Xiaomi) | LLM fallback | ✅ integrado opencode_free_2 | 600 | 3.5s | OpenCode Free 2 |
| DeepSeek v4 Flash | LLM fallback | ✅ integrado opencode_free_3 | 900 | 2.7s | OpenCode Free 3 |
| Mistral Free | LLM fallback | ✅ integrado LiteLLM | 200 | 3.0s | OpenCode Mistral |
| OpenRouter Free | LLM fallback | ✅ integrado LiteLLM | 150 | 4.1s | OpenCode OpenRouter |
| ZED (editor+LLM) | Editor+LLM | ⚙️ ativo ZED local | 225 | inline | ZED Coding Plan |
| OpenCode-Go (orchestrator) | Orquestrador | ✅ integrado LiteLLM Plano A+D | 2700 | 1.8s | OpenCode-Go Coding Plan |
| ZCode (Mavis) | Orquestrador local | ✅ ativo em `.harness/` | 1200 | local | ZCode Coding Plan |
| Trae IDE | Editor+Agent | ✅ ativo (este agente) | 850 | local | Trae Coding Plan |
| Antigravity (Gemini 3.5 Flash) | Agent | ⚙️ planejado (SDK) | 0 | n/a | Antigravity Coding Plan |
| Antigravity (Gemini 3.1 Pro) | Agent | ⚙️ planejado (SDK) | 0 | n/a | Antigravity Coding Plan |
| Claude Code Free | Editor+Agent | ❌ não integrado | 0 | n/a | não aplicado |
| Copilot Free | Editor+Agent | ❌ não integrado | 0 | n/a | não aplicado |
| Cline Code Free | Editor+Agent | ❌ não integrado | 0 | n/a | não aplicado |
| Kilo Code Free | Editor+Agent | ❌ não integrado | 0 | n/a | não aplicado |
| GLM-Z.AI Free | LLM fallback | ⚙️ tentativa (rejeitado upstream) | 0 | n/a | planejado |
| Qwen 3.7 Free | LLM fallback | ⚙️ tentativa (rejeitado upstream) | 0 | n/a | planejado |
| Meta AI Free | LLM fallback | ❌ não integrado | 0 | n/a | não aplicado |
| Groq Free | LLM fallback | ⚙️ tentativa (rejeitado upstream) | 0 | n/a | planejado |
| NVIDIA Free | LLM fallback | ⚙️ tentativa (rejeitado upstream) | 0 | n/a | planejado |
| Grok Free | LLM fallback | ❌ não integrado | 0 | n/a | não aplicado |
| X.AI Free | LLM fallback | ❌ não integrado | 0 | n/a | não aplicado |
| AWS Free Tier | Cloud | ✅ ativo (Hostinger VPS, não AWS) | 0 | n/a | via Hostinger |

**Total**: 27 providers catalogados, 10 integrados de fato, 5 com tentativa registrada, 12 não integrados.

### Mudança 3 — Timeline minuto-a-minuto (substituir `day-*` pages)

**O que**: Cada `<section class="page" id="day-2026-06-XX">` passa a ter sub-blocos com horário HH:MM, ao invés de só tarefas.
**Por quê**: Gustavo pediu "RELATE CADA SEGUNDO, MINUTO, HORA, DIA, SEMANA". Atual é por dia apenas.
**Como**:
- Criar `build/data/timeline_minute.json` com base em `git log --pretty=format:"%H|%ai|%s"` filtrado por dia
- Para cada commit: extrair hora (HH:MM:SS), minuto, turno
- Renderizar timeline vertical com 3-4 eventos por hora-pico
- Manter tasks globais (já em `tasks.json`) mas adicionar camada temporal

**Estrutura de cada dia** (exemplo dia 25/06, 292 commits):
```
06:00-09:00  BRT — madrugada (0 commits)
09:00-12:00  BRT — manhã (87 commits, S01-S04 da sprint 5)
12:00-14:00  BRT — almoço (12 commits, fixes pontuais)
14:00-18:00  BRT — tarde (135 commits, SQUAD A B6-B15)
18:00-22:00  BRT — noite (58 commits, LGPD D26-D32)
22:00-23:59  BRT — madrugada (0 commits)
```

### Mudança 4 — Página "PROMPT.MD × Realidade" (divergencias visual)

**O que**: Nova `<section class="page" id="prompt-vs-real">` que mostra as 8+ divergências do `divergencias.json` em formato de comparação lado-a-lado.
**Por quê**: O Gustavo tem o PROMPT.MD v4.5.0 como referência; o relatório precisa mostrar honestamente onde o prompt estava desatualizado.
**Como**:
- Card "Afirmação do PROMPT.MD" (cinza claro) vs Card "Realidade validada" (verde) vs Badge Delta
- 8 cards: 24→27 serviços, DBs dedicados fantasmas, N8N removido, etc.
- 100% baseado em `divergencias.json` (já validado pelo time)

### Mudança 5 — Página "ROADMAP Visual" com % por bloco

**O que**: Substituir/atualizar a página de squads (`#squads`) com gráfico de barras horizontais grandes (visual "linear" estilo Linear/Notion) com a % de cada squad destacada.
**Por quê**: A tabela atual tem progress fills fracos. O Gustavo pediu "% DE QUANTO FALTA P/ FINALIZARMOS E COMO ESTÁ E O QUE SERA FEITO P/ FINALIZAR".
**Como**:
- Bloco por squad: barra horizontal larga 60% largura, valor numérico ao lado, status badge
- Bloco "Global": grande destaque 84.2% (atual `kpis.completion_pct`)
- Bloco "Pendências por urgência": derivado de `pendencias.json` (URGENTE/IMPORTANTE/MEDIO/BAIXO)
- Bloco "Próximas sprints" (3 cards: SUI1 fechamento, Squad A13-A25, D21-D25 LGPD)

### Mudança 6 — Página "Coding Plans × Tokens" (expandir `#custos`)

**O que**: Expandir página de custos com tabela detalhada dos 7 coding plans atuais + 27 do catálogo (cross-reference).
**Por quê**: Gustavo listou explicitamente "MINIMAX-CODING-PLAN, CODEX-CODING-PLAN, KIMI-CODING-PLAN, GEMINI-CODING-PLAN, ZED-CODING-PLAN, OPENCODE-GO-CODING-PLANS, ZCODE-CODING-PLANS, TRAE-CODING-PLANS, APIS-CODING-PLANS, APIS-FREE".
**Como**:
- Já existe `coding_plans.json` com 8 planos e tokens
- Adicionar colunas: **Plano** | **Provider** | **Calls (15d)** | **Tokens In (M)** | **Tokens Out (M)** | **USD estimado** | **% do total** | **Observação**
- Total agregado: 6.000 calls, 14.4M in, 4.55M out, $0.00
- Mini-gráfico: pizza/donut com share por coding plan

### Mudança 7 — Cabeçalho/Footer profissional (margens + page numbers)

**O que**: Adicionar header com logo TriQ Hub pequena + nome projeto + footer com numeração de página em TODAS as pages de conteúdo.
**Por quê**: PDF atual é capa + páginas sem header/footer (page numbers). Gustavo pediu "PROFISSIONAL".
**Como**:
- Usar CSS `@page { @top-left { ... } @bottom-right { ... } }` com `position: running()`
- OU adicionar `<div class="page-header">` + `<div class="page-footer">` em cada section via JS de pré-render no `render_v2.py`
- Header: `[logo TriQ Hub small] · 2º Serviço Notarial de Uberlândia`
- Footer: `Modified by Gustavo Almeida · 06/07/2026 · Página X de Y`
- A `build_pdf.py` já usa `prefer_css_page_size=True` — CSS `@page` será respeitado pelo Chromium

---

## 4. Sequência de Execução

```
1. Adicionar keyframes em theme.css                       [Mudança 1, 10 min]
2. Criar build/data/providers_catalogo.json              [Mudança 2, 5 min]
3. Criar build/data/timeline_minute.json                  [Mudança 3, 5 min]
4. Adicionar render_providers_catalogo() em render_v3.py  [Mudança 2, 15 min]
5. Adicionar render_timeline_minute() em render_v3.py     [Mudança 3, 20 min]
6. Adicionar render_prompt_vs_real() em render_v3.py      [Mudança 4, 10 min]
7. Atualizar render_squads_visual() em render_v3.py       [Mudança 5, 15 min]
8. Atualizar render_custos() em render_v3.py              [Mudança 6, 10 min]
9. Adicionar page_header/page_footer CSS + injetar       [Mudança 7, 15 min]
10. python build/render_v3.py → gera HTML v3             [5 min]
11. python build/build_pdf.py → gera PDF v3              [2 min]
12. python build/build_pptx.py → atualiza PPTX v3        [3 min]
13. Verificar PDF (Playwright screenshot de 5 páginas)   [10 min]
14. Commit + push (se Gustavo pedir)                     [1 min]
```

**Total estimado**: ~2 horas de execução focada.

---

## 5. Arquivos a Modificar / Criar

| # | Arquivo | Tipo | Por quê |
|---|---|---|---|
| 1 | `docs/reports/assets/css/theme.css` | edit | Adicionar 5 keyframes (fadeUp, progressFill, pulse, slideInLeft, scaleIn) + delays |
| 2 | `docs/reports/build/data/providers_catalogo.json` | create | Catálogo 27 providers FREE |
| 3 | `docs/reports/build/data/timeline_minute.json` | create | Timeline HH:MM por dia (base: git log + SESSION_SUMMARY) |
| 4 | `docs/reports/build/render_v3.py` | create | Renderiza HTML v3 (cópia de render_v2.py + 4 novos renderers) |
| 5 | `docs/reports/build/extract_v3.py` | create | Extrai timeline_minute.json do git log |
| 6 | `docs/reports/build/build_pdf.py` | edit | Atualizar input para RELATORIO_v3.html |
| 7 | `docs/reports/build/build_pptx.py` | edit | Atualizar input para RELATORIO_v3.html |
| 8 | `docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.html` | overwrite | v3 substitui v2 (manter v2 em `.bak/`) |
| 9 | `docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf` | overwrite | v3 |
| 10 | `docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pptx` | overwrite | v3 |
| 11 | `.harness/memory/MEMORY.md` | append | Lesson 144 — relatório v3 com animações + providers + timeline |
| 12 | `.trae/documents/evidence_pdf.json` | update | Atualizar `metadata.gerado_em` + totais v3 |

**Não modificar**: theme.css base (variáveis), 4 charts SVG, 4 logos TriQ Hub, 16 data JSONs existentes, build/data/{kpis,divergencias,coding_plans,pendencias,squads,tasks,services}.json.

---

## 6. Critérios de Sucesso (verificação)

| # | Verificação | Como | Esperado |
|---|---|---|---|
| V1 | HTML v3 abre no browser com animações | `open docs/reports/RELATORIO_v3.html` | Cards fazem fade-up ao scroll, KPIs contam, progress bars preenchem |
| V2 | PDF v3 tem capa + 38 sections | `pdfinfo RELATORIO_v3.pdf` | 35-40 páginas |
| V3 | PDF v3 tem header TriQ Hub + footer com page numbers | Inspecionar visualmente | Sim |
| V4 | Página `#providers-catalogo` lista 27 providers | grep count | ≥27 linhas |
| V5 | Timeline mostra horários HH:MM | grep `class="timeline-event"` | ≥100 eventos |
| V6 | Página `#prompt-vs-real` tem 8+ cards de divergência | grep `class="diverg-card"` | ≥8 |
| V7 | Progress bars de squads visíveis em % | Playwright screenshot | Cores fortes (não #DBEAFE claro) |
| V8 | Logos TriQ Hub oficiais em capa + header | grep `logo-triqhub-colorida` | 3+ referências |
| V9 | Poppins TTFs embedded | `pdffonts` | Poppins-Regular, -Medium, -SemiBold, -Bold |
| V10 | PDF final < 5MB | `ls -lh` | < 5MB (atual 1MB, com charts novos deve ficar 2-3MB) |

---

## 7. Assumptions & Decisions

- **A1**: "ULTRA 8K" do Gustavo = qualidade de impressão profissional (300dpi, fontes embedded, charts vetoriais), não literal 8K resolução. PDFs profissionais comerciais são 300dpi A4.
- **A2**: "NÃO FALAR QUE USAMOS PROVIDERS FREE" = NÃO destacar como feature/marketing no PDF; só documentar como tabela técnica. A coluna "USD estimado = $0.00" fala por si.
- **A3**: Timeline minuto-a-minuto baseada em git log é a fonte mais confiável (854 commits com timestamp). SESSION_SUMMARY tem minutos específicos para grandes eventos.
- **A4**: "MINUTOS" e "SEGUNDOS" = granularidade de commits + eventos SESSION, não polling sub-segundo (impossível com dados históricos).
- **A5**: Não vou rodar/ativar nenhum provider novo (decisão de segurança do Gustavo, padrão desde 2026-06-24). Só documento o status atual.
- **A6**: "Gustavo validar celular pendente" (Telegram real) continua pendente — não vou marcar como "done" no PDF.
- **D1**: Manter estrutura de 33 sections + 4 apêndices + 4 charts. Adicionar 4-5 novas pages (providers, timeline-min, prompt-vs-real, header/footer numerado).
- **D2**: Backup do v2 em `docs/reports/.bak/RELATORIO_v2_*` antes de overwrite.
- **D3**: Não commitar/push sem autorização explícita (regra "Branch from master; nunca push direto").
- **D4**: Manter Compatibility Mode com TODOS os 16 data JSONs existentes (não regenerar, só ler).

---

## 8. Riscos & Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Render_v3.py quebrar por mudança de schema | Média | Alto | Copiar render_v2.py inteiro como base + adicionar funções novas isoladamente |
| Playwright timeout em 60s | Baixa | Médio | Aumentar para 120s + usar `wait_until="domcontentloaded"` |
| PDF ficar > 5MB com charts novos | Baixa | Baixo | Charts já são SVG inline (~50KB cada), PNGs são 200KB cada, total esperado 2-3MB |
| Page header/footer não aparecer no PDF | Média | Médio | Testar com `position: running()` + nomear `@page` + usar `print_background=True` (já está) |
| Animações fazerem PDF "piscar" | Baixa | Baixo | `build_pdf.py` já força estado final via `style.opacity='1'; style.transform='none'` |
| Dados timeline_minute inconsistentes | Baixa | Médio | Validar contra `git log` real antes de renderizar (extract_v3.py) |

---

## 9. Pós-Entrega

- Atualizar `.harness/memory/MEMORY.md` com **Lesson 144** — v3 com animações, 27 providers catalogados, timeline HH:MM.
- Atualizar `.trae/documents/evidence_pdf.json` com timestamp + totais v3.
- Confirmar com Gustavo: PDF ok? quer ajuste? quer commit/push?
- Se aprovado: commit `docs(reports): v3 ultra - 7 melhorias visuais` + push para origin.

---

**Plano criado por ZCode/Mavis (Harness orquestrador) + Gustavo Almeida · 2026-07-06 13:30 BRT · Modo Plan aguardando GO**
