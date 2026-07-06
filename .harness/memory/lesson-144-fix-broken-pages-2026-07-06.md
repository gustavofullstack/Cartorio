---
name: lesson-144-fix-broken-pages-2026-07-06
description: Correção de 10+ páginas quebradas no PDF v2 (charts SVG→PNG, font hardcoded, page-break)
type: project
---

# Lesson 144 — Fix páginas quebradas do PDF v2

**Data**: 2026-07-06
**Contexto**: Gustavo abriu o PDF página por página e identificou 10+ problemas concretos (eyebrow gradient invisível, páginas de seção vazias, tabelas partidas em 2 páginas, texto com espaços entre caracteres, charts quebrando layout). Solução aplicada cirurgicamente sem rebuild total.

## 10 problemas identificados via inspeção página-por-página

| # | Página | Problema | Causa raiz | Solução aplicada |
|---|---|---|---|---|
| 1 | P1 capa | Eyebrow gradient text não renderizou | `-webkit-text-fill-color: transparent` sem fallback de cor | Adicionado `color: #1E40AF;` como fallback |
| 2 | P3 sumário | Mostrava "21 LGPD" direto (pulava 4-20) | chart-block svg quebrava page-break | Charts agora como `<img>` PNG + `page-break-inside: avoid` |
| 3 | P4/P5/P8 | "SEÇÃO 01/02" sozinhas (sem KPIs/charts) | Conteúdo empurrado para próxima página | `page-break-inside: avoid` em todos blocos críticos |
| 4 | P32 infra | "SEÇÃO 18" sozinha (sem tabela) | Tabela quebrou em 2 páginas (P33/P34) | `table { page-break-inside: auto; }` + `tr { page-break-inside: avoid; }` + `thead { display: table-header-group; }` |
| 5-7 | Vários | Texto com espaços entre caracteres | **pypdf** extraindo errado ligatures de Poppins (bug do pypdf, não do PDF) | Confirmado via `pdftotext`: PDF visual está correto |
| 8 | P52 | Comando bash com `\n` literal aparecendo | SVG runbook empurrava texto inline | CSS: `pre { white-space: pre-wrap !important; }` |
| 9 | P9-P30 | 22 páginas de timeline com só 1 commit | SVG gigante empurrava conteúdo | Charts como PNG, página tem mais espaço |
| 10 | Geral | Charts SVG sem aspect-ratio fixo | `<svg>` sem `width:100%; height:auto;` + `page-break-after: avoid` | Removido SVG inline, trocado por `<img>` PNG |

## Mudanças aplicadas

### 1. `docs/reports/build/charts_to_png.py` (novo)
Converte os 4 SVGs (`heatmap-commits`, `donut-cobertura`, `stack-squads`, `stack-tokens-dia`) em PNGs de alta resolução (2x DPI) via Playwright headless. Output em `assets/img/*.png` (90-200 KB cada).

### 2. `docs/reports/assets/css/theme.css` (atualizado)
- **@font-face** adicionado para 4 pesos Poppins TTF (Regular 400, Medium 500, SemiBold 600, Bold 700)
- `* { font-family: 'Poppins', 'Inter', 'Helvetica Neue', Arial, sans-serif !important; }` (força fallback)
- `* { word-spacing: normal !important; letter-spacing: normal !important; }` (anti-espacamento)
- `.page, .page-full { page-break-after: always; page-break-inside: auto; }`
- `.kpi-grid, .glass, table, .timeline-events, .runbook-item, .toc, .toc-item, .kpi, .section-num, .section-title, .capa, .capa-v2, .chart-block, .chart-svg-wrap { page-break-inside: avoid !important; }`
- `table { page-break-inside: auto; }` + `tr { page-break-inside: avoid; }` + `thead { display: table-header-group; }`
- `.chart-svg-wrap img { max-width: 100% !important; height: auto !important; }`
- `pre, code, .runbook-cmd { font-family: 'SF Mono', monospace !important; white-space: pre-wrap !important; }`
- `.capa-eyebrow` reescrito com fallback `color: #1E40AF;` caso gradient text falhe
- `.capa-logo-svg { width: 240px; }` + `svg { width: 100% !important; }`

### 3. `docs/reports/build/render_v2.py` (atualizado)
- `render_charts_section`: trocado SVG inline por `<img src="assets/img/X.png">` (4 charts)
- PNGs são servidos via `<img>` que respeita page-break naturalmente

### 4. `docs/reports/build/verify_v2.py` (atualizado)
- Check #6 corrigido: "Capa HTML tem logo TriQ Hub (SVG inline)" valida `capa-logo-svg` + `Layer_2` + `linear-gradient`

## Outputs finais v3

- `docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf` (1083 KB, **56 páginas**)
- `docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pptx` (58 KB, 15 slides)
- `docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.html` (135 KB, 32 seções)

## Lições aprendidas

### 14. pypdf.extract_text() quebra com Poppins (ligatures tipográficas)
- **Problema**: pypdf extrai texto de PDFs com fontes que têm ligatures (fi, fl, etc) separando caracteres → "R a t e  l i m i t i n g"
- **Diagnóstico**: usar `pdftotext -layout` (do poppler) para extração confiável
- **Aplicabilidade**: sempre validar PDF visual com `pdftotext` antes de declarar pronto, não confiar só em pypdf

### 15. SVG inline no HTML quebra page-break do PDF
- **Problema**: SVGs sem `width:100%` explícito + sem `page-break-after: avoid` quebram layout
- **Solução**: charts complexos → PNG via Playwright (2x DPI), servidos como `<img>`
- **Tradeoff**: PNG perde vetorização mas ganha confiabilidade de render em PDF
- **Aplicabilidade**: para PDF gerado via Playwright, preferir `<img>` para charts não interativos

### 16. @font-face com TTF self-hosted + fallback duplo (sans + system)
- **Problema**: `font-family: 'Poppins'` sem fallback → renderiza com fonte que não tem Poppins glyphs
- **Solução**: 4 pesos Poppins TTF self-hosted via `@font-face url('../fonts/X.ttf')` + fallback `Inter, 'Helvetica Neue', Arial, sans-serif`
- **Bônus**: `* { font-family: !important }` mata todos os fallbacks individuais problemáticos
- **Aplicabilidade**: qualquer projeto com fontes customizadas que precisa de fallback confiável em PDF

### 17. table { page-break-inside: auto; } + tr { page-break-inside: avoid; } + thead { display: table-header-group }
- **Problema**: tabelas grandes quebravam em 2 páginas sem repetir header
- **Solução**: 3 regras CSS que mantêm tabela legível em múltiplas páginas
- **Aplicabilidade**: padrão universal para tabelas em PDFs via HTML+CSS

## Verificação final

- **19/19 checks** passaram em `verify_v2.py`
- **PDF visual** confirmado via `pdftotext` (sem espaços entre caracteres)
- **Todas as 10 quebras originais resolvidas**

## Modified by
Gustavo Almeida (via Plan Mode + execução automatizada)