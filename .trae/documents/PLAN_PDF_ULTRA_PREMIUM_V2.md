# Plano — Relatório Quinzenal Ultra-Premium v2 (PDF + PPTX expandidos)

> Plano gerado em **Plan Mode**. Aguardando aprovação do Gustavo para iniciar execução.

---

## 1. Summary

Expandir os artefatos já entregues (`docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.{pdf,pptx,html}` — v1) para uma **versão 2 ultra-premium** que adicione 4 apêndices extras, 4 gráficos SVG inline, capa redesenhada com monograma TriqHub customizado e Poppins self-hosted real (TTF já disponível em `docs/CLIENTES/.../assets/fonts/`).

**Entregas v2** (sobrescreve v1):

1. **`docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf`** — versão expandida (~80-100 páginas)
2. **`docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pptx`** — apresentação executiva expandida (~18-22 slides)
3. **`docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.html`** — fonte HTML (~200 KB, anima no browser)

**Audiência**: Felipe Pizarro + Djalma Pizarro (titulares 2º Serviço Notarial Uberlândia).

**Janela**: 2026-06-22 → 2026-07-06 (15 dias inteiros, 852 commits).

---

## 2. Current State Analysis

### 2.1. Estado verificado em Phase 1

| Item | Valor real |
|---|---|
| v1 PDF | 657 KB, 45 páginas (em `docs/reports/`) |
| v1 PPTX | 50 KB, 11 slides |
| v1 HTML | 116 KB, 2487 linhas |
| Plan v1 | `.trae/documents/PLAN_PDF_BIWEKKLY_REPORT_CARTORIO.md` |
| Lesson 142 | `.harness/memory/lesson-142-quinzenal-report-2026-07-06.md` (salva) |
| Working tree | v1 entregue + estado `master` preservado |
| Material auxiliar existente | `docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06/` (Poppins TTF + 3 SVGs) |
| TriqHub logo | **Não existe arquivo `triqhub.svg`** no filesystem. Usuário descreveu: "triângulo vetorizado para cima tipo um q" |

### 2.2. Decisões locked com o usuário

| Decisão | Valor |
|---|---|
| Escopo da v2 | Expandir para ultra-premium (volume) |
| Apêndices extras | Lessons (8) + Coding Plans (custos tokens) + Divergências + Runbook |
| Gráficos SVG | Heatmap dia×hora + Donut cobertura + Stack squads + Stack tokens/dia |
| Capa | Monograma TriqHub customizado (triângulo com "q" para cima, vetorizado) — **criar SVG inline** já que não existe arquivo |
| Poppins | Self-hosted real via TTF (já tem `Poppins-Regular.ttf`, `-Medium.ttf`, `-SemiBold.ttf`, `-Bold.ttf` em `docs/CLIENTES/.../assets/fonts/`) |
| Idioma | PT-BR + termos técnicos |

---

## 3. Proposed Changes

### 3.1. Novos arquivos a criar

```
docs/reports/
├── RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf          # v2 (sobrescreve)
├── RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pptx         # v2 (sobrescreve)
├── RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.html         # v2 (sobrescreve)
└── assets/
    ├── fonts/
    │   ├── Poppins-Regular.ttf       # COPIADO de docs/CLIENTES/.../fonts/
    │   ├── Poppins-Medium.ttf        # COPIADO
    │   ├── Poppins-SemiBold.ttf      # COPIADO
    │   └── Poppins-Bold.ttf          # COPIADO
    └── img/
        ├── logo-triqhub.svg          # NOVO — monograma vetorizado (triângulo + "q")
        ├── heatmap-commits.svg       # NOVO — 14 dias × 24h, intensidade por nº commits
        ├── donut-cobertura.svg       # NOVO — top 10 módulos < cobertura
        ├── stack-squads.svg          # NOVO — 9 squads horizontal bar
        └── stack-tokens-dia.svg      # NOVO — 14 dias × 7 planos, área empilhada
```

### 3.2. Atualização dos scripts de build

**`docs/reports/build/extract.py`** — adicionar:
- `extract_lessons()` → lê `.harness/memory/MEMORY.md` + lições específicas de `lesson-*.md` → `lessons.json` (8 lições selecionadas)
- `extract_coding_plans()` → tabela de custos por coding plan (MINIMAX/CODEX/KIMI/GEMINI/ZED/OPENCODE-GO/TRAE/ZCODE/APIs-FREE) → `coding_plans.json`
- `extract_divergencias()` → divergências PROMPT.json vs real (24 serviços imaginários → 27 reais) → `divergencias.json`
- `extract_runbook()` → runbook de comandos essenciais → `runbook.json`
- `extract_heatmap()` → commits por dia×hora do git log → `heatmap.json`
- `extract_cobertura()` → cobertura por módulo (10 piores) → `cobertura.json`
- `extract_squads_chart()` → 9 squads com cores para gráfico → (já existe em squads.json, só adicionar palette)
- `extract_tokens_day()` → tokens por dia × plano → `tokens_day.json`

**`docs/reports/build/render.py`** — adicionar:
- `render_capa_v2()` — redesenhada com monograma TriqHub + tipografia maior
- `render_heatmap_commits()` — SVG inline 14×24 com cor por intensidade
- `render_donut_cobertura()` — SVG inline circular
- `render_stack_squads()` — SVG inline horizontal bars
- `render_stack_tokens_dia()` — SVG inline stacked area
- `render_apendice_lessons()` — 8 lições em tabela
- `render_apendice_coding_plans()` — tabela custos tokens
- `render_apendice_divergencias()` — divergências PROMPT.json vs real
- `render_apendice_runbook()` — comandos copy-paste

**`docs/reports/build/build_pptx.py`** — adicionar:
- `slide_capa_v2()` — monograma TriqHub centralizado
- `slide_heatmap_commits()` — imagem PNG do heatmap (convertido via Playwright) ou shape nativo
- `slide_donut_cobertura()` — imagem PNG
- `slide_stack_squads()` — imagem PNG
- `slide_coding_plans()` — tabela completa
- `slide_lessons()` — tabela 8 lições
- `slide_divergencias()` — tabela divergências
- `slide_runbook()` — code blocks

### 3.3. Monograma TriqHub (decisão do usuário)

Descrição do usuário: **"triângulo vetorizado para cima tipo um q"**. Vou criar SVG inline minimalista:

```svg
<svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
  <!-- Triângulo apontando para cima (a "ponta do q") -->
  <path d="M 40 8 L 72 64 L 8 64 Z" 
        fill="none" stroke="#0F172A" stroke-width="3" stroke-linejoin="round"/>
  <!-- Cauda do "q" (linha curva à direita, descendo) -->
  <path d="M 56 56 Q 64 64 60 72" 
        fill="none" stroke="#0F172A" stroke-width="3" stroke-linecap="round"/>
  <!-- Ponto interno (símbolo do "q") -->
  <circle cx="40" cy="48" r="3" fill="#1E40AF"/>
</svg>
```

**Nota de transparência**: se Gustavo tiver o SVG original em outro local, posso substituir; mas como não foi encontrado no filesystem, esta é a melhor interpretação da descrição.

### 3.4. Detalhamento dos 4 gráficos SVG

**Heatmap commits (14 dias × 24h)**:
- 14 colunas (datas) × 24 linhas (horas)
- Cada célula: rect 18×18px, gap 2px
- Cor baseada em intensidade: `#F8FAFC` (vazio) → `#DBEAFE` → `#93C5FD` → `#3B82F6` → `#1E40AF` (mais commits)
- Tooltip on hover (não printa em PDF, mas funciona no HTML)

**Donut cobertura (10 piores módulos)**:
- Círculo com 10 fatias, raio 60px
- Labels externas com % e nome do módulo
- Cores: gradient de `#B91C1C` (mais crítico) → `#F59E0B` → `#10B981`

**Stack horizontal de squads (9 squads)**:
- 9 barras horizontais, cada uma dividida em done (cor) + pending (cinza)
- Squad name à esquerda, % à direita
- Cores: A `#1E40AF`, B `#94A3B8`, C `#0F172A`, D `#047857`, E `#B45309`, H `#7C3AED`, J `#0891B2`, BRAIN `#DB2777`, DOCS `#475569`

**Stack tokens/dia (14 dias × 7 planos)**:
- Eixo X: datas (15 dias)
- Eixo Y: tokens (millions)
- 7 áreas empilhadas, cada uma com cor do plano (A=azul, B=ciano, C=verde, D=âmbar, E=vermelho, F=violeta, G=cinza)

### 3.5. Detalhamento dos 4 apêndices extras

**Apêndice C — Lessons (8 mais importantes)**:
| # | Lesson | Tópico | Causa-raiz | Fix |
|---|---|---|---|---|
| 110 | Pydantic literal vs intent D0.2 hardened | LGPD | Validação regex literal vs semântica | Adicionar validate_cpf_cnpj |
| 116 | OpenClaw context 1M confirmado | LLM | Test confirmou contexto 1M | Aplicar Plano A como padrão |
| 120 | 3 bugs combinados (rate-limit/UA/session) | Telegram | Concorrência + Cloudflare + background | Plano A + UA Mozilla + logging.basicConfig |
| 126 | crwal4ai VXLAN swarm issue | Infra | bind OK mas VXLAN não encaminha | Recriar com `--network host` |
| 130 | Token Cloudflare expirado (2026-05-05) | DNS | Refresh endpoint 404 | Gerar novo via UI |
| 138 | fakeredis + pytest-asyncio missing | Tests | Dependências não declaradas | Adicionar ao pyproject.toml |
| 140 | Loop engineer auto-reactivação YOLO | Orquestração | Cron 4h + 30min funciona | Mantido em produção |
| 142 | Relatório quinzenal multi-formato | Reporting | counters.js não roda no PDF print | page.evaluate() antes de page.pdf() |

**Apêndice D — Coding Plans (custos tokens)**:
| Plano | Chamadas (15d) | Tokens in (M) | Tokens out (M) | USD estimado | Observação |
|---|---|---|---|---|---|
| MINIMAX CODING PLAN | ~50 | 0.12 | 0.04 | $0.00 | Plano primário IA local |
| CODEX CODING PLAN | ~30 | 0.08 | 0.02 | $0.00 | Plano secundário |
| KIMI CODING PLAN | ~20 | 0.05 | 0.02 | $0.00 | Plano terciário |
| GEMINI CODING PLAN | ~25 | 0.06 | 0.02 | $0.00 | Plano multimodal |
| ZED CODING PLAN | ~15 | 0.04 | 0.01 | $0.00 | Plano editor local |
| OPENCODE-GO CODING PLAN | ~180 | 0.43 | 0.14 | $0.00 | Plano IA orquestrador |
| TRAE CODING PLAN | ~120 | 0.29 | 0.09 | $0.00 | Plano IDE TRAE |
| ZCODE CODING PLAN | ~80 | 0.19 | 0.06 | $0.00 | Plano Mavis |
| APIs CODING PLAN | ~200 | 0.48 | 0.15 | $0.00 | Plano APIs externas |
| **TOTAL** | **~720** | **1.74M** | **0.55M** | **$0.00** | — |

**Apêndice E — Divergências**:
Tabela com ~12 linhas mostrando afirmações do PROMPT.json vs realidade verificada. Já existe no SERVICE_INVENTORY.md Waves 7-13.

**Apêndice F — Runbook**:
Blocos de comandos copy-paste: health check 27 serviços, restart LiteLLM, restart Redis, validar pipeline, validar Telegram bot, etc.

### 3.6. Detalhamento das alterações no CSS

`assets/css/theme.css` — adicionar:
- `@font-face` para os 4 pesos Poppins TTF
- Estilos `.heatmap-cell`, `.donut-slice`, `.squad-bar`
- Ajustes para `.capa-v2` (monograma, tipografia maior)

### 3.7. Estimativa de execução

- Copy Poppins TTF: ~5s
- Criar 5 SVGs (logo + 4 gráficos): ~10 min (geração inline em Python via geometria)
- Atualizar extract.py com 8 novos extractors: ~15 min
- Atualizar render.py com 8 novos renderers: ~20 min
- Atualizar build_pptx.py com 7 novos slides: ~10 min
- Build + verificação: ~5 min
- **Total: ~60 min**

---

## 4. Assumptions & Decisions

### 4.1. Pressupostos

1. **TriqHub logo não existe como arquivo** — vou criar SVG inline baseado na descrição ("triângulo para cima tipo q"). Se Gustavo tiver o original, ele substitui depois.
2. **Poppins TTF já está disponível** em `docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06/assets/fonts/`. Vou copiar para `docs/reports/assets/fonts/` e converter para woff2 via fonttools (ou usar TTF direto).
3. **TTF > WOFF2 no PDF**: Playwright/Chromium aceita TTF nativamente. WOFF2 seria melhor para web, mas TTF funciona para o PDF.
4. **SVG inline nos gráficos**: renderizados em Python como string, embedded no HTML. Print-friendly via Playwright.
5. **Sem mexer em secrets**: nenhum `.env` ou `.secrets/*` será tocado.

### 4.2. Decisões locked

| Decisão | Locked value |
|---|---|
| Escopo v2 | Expandir (volume) |
| Apêndices | Lessons + Coding Plans + Divergências + Runbook |
| Gráficos | Heatmap + Donut + Stack squads + Stack tokens |
| Capa | Redesenhada com monograma TriqHub (SVG inline criado) |
| Poppins | Self-hosted TTF (4 pesos) |
| Idioma | PT-BR + termos técnicos |

### 4.3. Tradeoffs aceitos

- **TriqHub logo criado do zero** (não oficial) — risco de divergir da original. Mitigação: Gustavo substitui depois.
- **SVGs gerados em Python puro** — sem matplotlib/plotly. Mais simples, suficiente para o nível de detalhe pedido.
- **5 slides extras no PPTX** (de 11 para 16-18) — mantém a duração da reunião executiva viável.

---

## 5. Verification Steps

1. ✓ PDF abre com ~80-100 páginas (vs 45 v1)
2. ✓ PPTX abre com 16-22 slides (vs 11 v1)
3. ✓ HTML tem 5 SVGs novos inline (logo, heatmap, donut, stack squads, stack tokens)
4. ✓ Capa tem monograma TriqHub visível
5. ✓ Poppins real self-hosted (não fallback Helvetica)
6. ✓ 4 apêndices extras (C/D/E/F) presentes
7. ✓ Heatmap renderiza 14×24 = 336 células
8. ✓ Donut tem 10 fatias com labels
9. ✓ Stack squads tem 9 barras
10. ✓ Stack tokens tem 7 áreas × 15 dias
11. ✓ Tabela Coding Plans tem 9 linhas + total
12. ✓ Tabela Lessons tem 8 linhas
13. ✓ Divergências tem 12+ linhas
14. ✓ Runbook tem 6+ blocos copy-paste
15. ✓ Plano A-G no corpo + provider real só no apêndice (mantido)
16. ✓ py_compile exit=0 em todos os scripts

---

## 6. Execução — Step-by-step quando aprovado

### Etapa 1 — Preparar assets (5 min)
- Copiar 4 Poppins TTF de `docs/CLIENTES/.../assets/fonts/` para `docs/reports/assets/fonts/`
- Criar `assets/img/logo-triqhub.svg` (SVG inline criado)

### Etapa 2 — Criar gráficos SVG (10 min)
- `build/svg_heatmap.py` → gera `heatmap-commits.svg` (14×24)
- `build/svg_donut.py` → gera `donut-cobertura.svg` (10 fatias)
- `build/svg_stack_squads.py` → gera `stack-squads.svg` (9 barras)
- `build/svg_stack_tokens.py` → gera `stack-tokens-dia.svg` (7×15)

### Etapa 3 — Expandir extract.py (15 min)
- 8 novos extractors: lessons, coding_plans, divergencias, runbook, heatmap, cobertura, squads_chart, tokens_day

### Etapa 4 — Expandir render.py (20 min)
- 1 capa nova + 4 gráficos inline (lê SVG gerado) + 4 apêndices

### Etapa 5 — Expandir build_pptx.py (10 min)
- 1 capa nova + 4 gráficos (lê SVG) + 4 slides extras (coding plans, lessons, divergências, runbook)

### Etapa 6 — Build + verificação (5 min)
- `python3 extract.py && render.py && build_pdf.py && build_pptx.py`
- 16 checks automatizados

### Etapa 7 — Memória (5 min)
- Atualizar Lesson 142 com "v2 expansion" (adicionar link + delta)

**Tempo total estimado**: ~70 min de execução real.

---

## 7. Risk & Mitigation

| Risco | Mitigação |
|---|---|
| TriqHub logo diverge do original | Criar versão "neutra" que Gustavo aceita ou substitui |
| Poppins TTF não funciona no Playwright | Fallback para Inter system + manter TTF para PPTX |
| SVG inline muito grande | Limitar a ~50KB cada |
| Heatmap difícil de ler em PDF | Usar grid com label do dia embaixo + número de commits por célula |
| Coding Plans tabela com dados inventados | Marcar explicitamente "estimativa por heurística" + fórmula |
| Sprint WORKFLOWS já existe `triqhub-deep.md` | Verificar se tem logo embutida lá |

---

## 8. Out of Scope

Não vou fazer:
- ❌ Commitar as mudanças (decisão do Gustavo depois)
- ❌ Atualizar PROGRESS.md / GOALS.md / STATUS.md
- ❌ Gerar versão em inglês
- ❌ Publicar online
- ❌ Substituir logo TriqHub se Gustavo achar a original
- ❌ Adicionar animações ao PPTX
- ❌ Mexer em arquivos fora de `docs/reports/`

---

## 9. Como aprovar e executar

Quando aprovado:
1. Marcar todos os todos como in_progress sequencialmente
2. Executar Etapas 1-7 sem nova interação (exceto se travar)
3. Notificar com paths absolutos + 16 checks (pass/fail) + lista de mudanças vs v1

---

**Modified by Gustavo Almeida (aprovação pendente via Plan Mode)**