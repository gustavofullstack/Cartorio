# Plano — Corrigir 10+ páginas quebradas do PDF v2

> Plano gerado em Plan Mode. Aguardando aprovação do Gustavo.

---

## 1. Summary

O PDF atual (`RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf`, 53 páginas) tem **10+ problemas concretos** que Gustavo identificou ao abrir página por página. Este plano corrige **cirúrgicamente** as páginas quebradas sem reconstruir o relatório do zero.

**Estratégia**: refazer só as páginas quebradas, charts como PNG (não SVG inline), font Poppins TTF embedded com fallback robusto.

---

## 2. Current State Analysis

### 2.1. Problemas identificados (via inspeção página-por-página do PDF)

| # | Página | Problema | Causa raiz |
|---|---|---|---|
| 1 | P1 (capa) | Eyebrow com gradient text não renderizou | CSS `-webkit-text-fill-color: transparent` não funciona em todos renderers |
| 2 | P3 | Mostra "21 LGPD" direto (pula 4-20) | chart-block svg causa page-break errado |
| 3 | P4/P5/P8 | "SEÇÃO 01" / "SEÇÃO 02" sozinhas (sem KPIs/charts) | Conteúdo foi empurrado para próxima página pelo chart |
| 4 | P32 | "SEÇÃO 18" sozinha (sem tabela de 27 serviços) | Tabela quebrou em 2 páginas (P33/P34) por falta de `page-break-inside: avoid` |
| 5 | P36 | "R a t e  l i m i t i n g" com espaços | Font fallback falhou (chrome quebrou ligatures) |
| 6 | P43 | "A c e ssa r  whatsapp..." com espaços | Mesmo problema de font fallback |
| 7 | P47 | "APÊNDICE C" sozinha (sem tabela de lessons) | Page-break mal posicionado |
| 8 | P52 | Comando bash com `\n` literal aparecendo | SVG do runbook empurrou texto inline |
| 9 | P9-P30 | 22 páginas de timeline dia-a-dia com só 1 commit cada | SVG gigante empurrou conteúdo pra fora |
| 10 | Geral | Charts SVG sem aspect-ratio fixo quebram layout | `<svg>` sem `width:100%; height:auto;` + `page-break-after: avoid` |

### 2.2. Decisões locked com Gustavo

| Decisão | Valor |
|---|---|
| Estratégia | **Refazer só as páginas quebradas** (não rebuild total) |
| Charts | **PNG via Playwright screenshot** (não SVG inline) |
| Font | **Hardcoded com Poppins TTF + fallback robusto** |

---

## 3. Proposed Changes

### 3.1. Novo arquivo: `docs/reports/build/charts_to_png.py`

Converte os 4 SVGs já gerados em PNGs de alta resolução:

```python
# Pseudocódigo
from playwright.sync_api import sync_playwright
for chart_name in ["heatmap-commits", "donut-cobertura", "stack-squads", "stack-tokens-dia"]:
    svg_path = IMG / f"{chart_name}.svg"
    png_path = IMG / f"{chart_name}.png"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 800})
        page.goto(f"file://{svg_path}")
        page.screenshot(path=str(png_path), full_page=True)
        browser.close()
```

Output: 4 PNGs em `assets/img/` (~30-80 KB cada).

### 3.2. Modificação em `assets/css/theme.css`

**Adicionar @font-face data-URI inline** (Poppins TTF) + **fallback robusto** + **page-break rules**:

```css
@font-face {
  font-family: 'Poppins';
  src: url(data:font/ttf;base64,<BASE64_TTF>) format('truetype');
  font-weight: 400; font-style: normal;
}
/* (Repetir para 500/600/700) */

* { font-family: 'Poppins', 'Inter', 'Helvetica Neue', Arial, system-ui, sans-serif !important; }

.chart-block, .kpi-grid, .glass, table, .timeline-events, .runbook-item,
.toc-item, .section-title, .kpi, .capa {
  page-break-inside: avoid !important;
  page-break-after: auto;
}

.chart-svg-wrap { display: block !important; }
.chart-svg-wrap img, .chart-svg-wrap svg {
  max-width: 100% !important;
  height: auto !important;
  display: block !important;
}
```

**Bônus**: o `font-family: !important` em `*` mata o problema de font fallback globalmente.

### 3.3. Modificação em `assets/css/theme.css` v2 additions

Mover/adicionar regras `.capa-v2`:
- Eyebrow com `background: linear-gradient(...); -webkit-background-clip: text;` + fallback `color: #1E40AF;` se gradient falhar
- Garantir que `<svg>` da capa tem `width: 240px; height: auto; display: block;`

### 3.4. Modificação em `render_v2.py`

Trocar a função `render_charts_section` para usar **PNG ao invés de SVG inline**:

```python
# Antes:
<div class="chart-svg-wrap">{heatmap_svg}</div>

# Depois:
<div class="chart-svg-wrap"><img src="assets/img/heatmap-commits.png" alt="Heatmap de Commits" /></div>
```

E ajustar o `render_apendice_runbook` para `<pre>` ter `white-space: pre-wrap;` (quebrar comando bash em múltiplas linhas visualmente sem perder semântica).

### 3.5. Rebuild script

```bash
# Gerar PNGs
python3 docs/reports/build/charts_to_png.py

# Re-renderizar HTML
python3 docs/reports/build/render_v2.py

# Re-gerar PDF
python3 docs/reports/build/build_pdf.py

# Re-gerar PPTX (mantém igual)
python3 docs/reports/build/build_pptx_v2.py

# Verificar
python3 docs/reports/build/verify_v2.py
```

### 3.6. Estimativa de tempo

- charts_to_png.py: ~3 min
- theme.css @font-face + page-break: ~5 min
- render_v2.py ajustes: ~3 min
- Render + PDF + PPTX + verify: ~5 min
- **Total: ~16 min**

---

## 4. Assumptions & Decisions

### 4.1. Pressupostos

1. Playwright já está instalado (validado em rodadas anteriores).
2. SVGs estão bem-formados (gerados por `svg_charts.py` que produz SVG válido).
3. PNG conversion será 2x DPI (factor=2) para garantir nitidez no PDF.
4. Font base64 TTF inline (~400KB total para 4 pesos) aumenta HTML de 204KB para ~600KB. Aceitável.

### 4.2. Decisões locked

| Decisão | Locked value |
|---|---|
| Charts | PNG (não SVG inline) |
| Font | Hardcoded + TTF data-URI inline + fallback 'Inter'/'Helvetica' |
| CSS | page-break-inside: avoid em todos blocos críticos |
| Rebuild | Apenas páginas quebradas, não total |

### 4.3. Tradeoffs aceitos

- **HTML maior** (~600KB vs 204KB) — aceitável para download local
- **PNG ao invés de SVG** — perde vetorização mas ganha confiabilidade de render
- **Base64 inline** — torna HTML não-cacheable mas elimina dependência de TTF externo

---

## 5. Verification Steps

Após execução, validar que **NENHUMA das 10 quebras originais persiste**:

1. ✓ Capa tem eyebrow visível (gradient text OU cor sólida #1E40AF)
2. ✓ Sumário mostra todas as 32 seções em ordem
3. ✓ Páginas 4-5-8 (SEÇÃO 01/02) têm KPIs e charts visíveis
4. ✓ Páginas 32-34 (Infra) mostram tabela completa de 27 serviços em 1 página
5. ✓ Páginas 35-37 (Backend) têm conteúdo completo, sem texto espaçado
6. ✓ Páginas 47-51 (Apêndices C/D/E/F) têm tabelas visíveis
7. ✓ Nenhuma página tem texto com "R a t e  l i m i t i n g" (font fallback)
8. ✓ Heatmap/donut/stack charts visíveis como imagens (não quebrando página)
9. ✓ Comando bash em P52 renderiza com quebras de linha visuais
10. ✓ 19/19 checks de `verify_v2.py` passam

---

## 6. Execução — Step-by-step quando aprovado

### Etapa 1 — charts_to_png.py (3 min)
- Novo script que converte 4 SVGs em PNG via Playwright
- Output: `assets/img/{chart_name}.png`

### Etapa 2 — theme.css @font-face + page-break (5 min)
- Adicionar @font-face data-URI inline com Poppins TTF (4 pesos)
- Adicionar `* { font-family: 'Poppins', 'Inter', 'Helvetica Neue', Arial, sans-serif !important; }`
- Adicionar `.chart-block, .kpi-grid, .glass, table { page-break-inside: avoid; }`

### Etapa 3 — render_v2.py ajustes (3 min)
- `render_charts_section`: trocar SVG inline por `<img src="assets/img/X.png">`
- `render_apendice_runbook`: garantir que `<pre>` tem `white-space: pre-wrap`

### Etapa 4 — Re-build chain (5 min)
- `python3 charts_to_png.py && render_v2.py && build_pdf.py && build_pptx_v2.py && verify_v2.py`

### Etapa 5 — Inspeção página-por-página do novo PDF (3 min)
- Rodar `pypdf` em loop, validar first-line de cada uma das 53 páginas
- Confirmar que **nenhuma** das 10 quebras originais persiste

---

## 7. Risk & Mitigation

| Risco | Mitigação |
|---|---|
| Base64 inline quebrar parsing HTML | Testar tamanho final; se >1MB, mover TTF para arquivo separado |
| Chart PNG ficar borrado no PDF | Usar `device_scale_factor=2` no Playwright screenshot |
| Page-break-inside: avoid criar página vazia | Fallback `page-break-after: auto` para redistribuir |
| `font-family: !important` quebrar elementos específicos | Testar render; ajustar via specificity se necessário |

---

## 8. Out of Scope

Não vou fazer:
- ❌ Commitar mudanças
- ❌ Atualizar PROGRESS/GOALS/STATUS
- ❌ Gerar versão em inglês
- ❌ Publicar online
- ❌ Mudar paleta de cores (gradiente TriQ Hub mantido)

---

**Modified by Gustavo Almeida (aprovação pendente via Plan Mode)**