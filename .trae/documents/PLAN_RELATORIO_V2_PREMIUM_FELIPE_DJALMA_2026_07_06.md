# Plano — Relatório Executivo v2.0.0 Premium · Felipe & Djalma (22/06 → 06/07/2026)

**Slug:** `report-felipe-djalma-v2-premium`
**Output alvo:** `docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf` (~45-50p, premium Playwright)
**Stack locked:** Playwright headless Chromium + HTML autoral + python-pptx (bônus opcional)
**Data:** 2026-07-06
**Modo:** Incrementar PDF v1.1.0 existente (preserva + evolui, sem overwrite cego)

---

## 1. Sumário

Incrementar PDF executivo existente (22p, 0.59MB, reportlab v1) para v2.0.0 (~45-50p) usando Playwright + HTML autoral com tema glass/white/Poppins, reusando os 8 charts PNG e 16 ícones PNG já renderizados em `assets/`, preservando conteúdo validado do MD mirror e adicionando timeline hora-a-hora de 14 dias, plano de providers A-G (sigilo no corpo, equivalência em apêndice), 15 seções premium e pipeline de build Python determinístico (~12 min de execução real). Counter animation pré-resolvido via `page.evaluate()` antes do `page.pdf()` para evitar bug conhecido do Chromium headless sem `IntersectionObserver` ativo durante render de PDF.

---

## 2. Análise do estado atual

### 2.1 O que JÁ EXISTE e é reutilizável (mantém + incrementa)

| Recurso | Caminho | Status | Reuso |
|---|---|---|---|
| PDF v1 (22p) | `docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf` | atual | vira insumo de comparação (backup `.bak` antes do overwrite) |
| MD mirror v1 | `docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.md` | completo | conteúdo-fonte canônico para `extract_content.py` |
| 8 charts PNG @192 DPI | `docs/CLIENTES/assets/charts/01..08-*.png` | validados | inserir `<img>` direto, sem regenerate |
| 16 ícones PNG @96x96 | `docs/CLIENTES/assets/icons_png/` (api, audit, bot, chatwoot, db, evolution, lgpd, litellm, llm, lock, loop, n8n, obs, openclaw, redis, status_*, supabase, vps) | validados | `<img>` no hero de cada seção |
| 4 fontes Poppins TTF | `docs/CLIENTES/assets/fonts/{Regular,Medium,SemiBold,Bold}.ttf` | OK no disco | autoload via `@font-face` |
| CSS tokens + main + print | `docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06/styles/{tokens,main,print}.css` | OK | reusar integralmente |
| SVG pré-render | `assets/svg/{arquitetura-swarm,kpi-icons,logo-cartorio}.svg` | OK | embed direto |
| JS helpers | `js/{charts,counters}.js` | OK | reusar com adaptação |
| CHANGELOG v1.1.0 | `CHANGELOG-RELATORIOS-CLIENTES.md` | até 22p | append entrada v2.0.0 |
| Lesson 142 documentada | `.harness/memory/lesson-142-quinzenal-report-2026-07-06.md` | OK | learnings críticos internalizados |

### 2.2 O que FALTA construir (incremento)

| Lacuna | Solução | Local |
|---|---|---|
| Pipeline Python (Playwright) | `build/build.py` orquestrador CLI | novo |
| Extractors de dados | `build/extract/*.py` (6 módulos) | novo |
| HTML fonte renderizado | `docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.html` | preencher |
| Timeline 14d hora-a-hora | nova seção 04 detalhada | HTML novo |
| Naming Plano A-G | tabela de equivalência em apêndice | HTML novo |
| Pre-resolve counters | hook Playwright antes do `page.pdf()` | novo em `pdf_playwright.py` |
| Validação final (pypdf, qpdf gate) | `build/validate.py` | novo |
| Entrada CHANGELOG v2.0.0 | append ao CHANGELOG existente | append |
| Mirror MD v2 | regerar a partir de HTML/DICT | mesmo path do .md |

### 2.3 Decisões herdadas da Lesson 142 (briefing)

1. **Counters**: `page.evaluate()` força `el.textContent = finalValue` para todos `[data-counter]` antes do `page.pdf()` (Chromium headless não roda `IntersectionObserver` durante PDF).
2. **Naming**: Plano A/B/C/D/E/F/G no corpo do relatório; equivalência técnica só em apêndice final.
3. **Arquitetura 3 layers**: JSON intermediário (`build/data/*.json`) → HTML renderizado (`Felipe_Djalma_STATUS_2026-07-06.html`) → PDF Playwright (`Felipe_Djalma_STATUS_2026-07-06.pdf`).
4. **Numbers**: real vs heurístico sempre marcado com badge `source: git | pytest | heuristic | manual`.
5. **Glass mode**: branco clean + cards `rgba(255,255,255,0.72)` + Poppins fallback `Poppins, Inter, Helvetica Neue, Arial, system-ui, sans-serif`.
6. **Tempo real**: ~12 min de execução ponta-a-ponta (não 30-45 min).

---

## 3. Mudanças propostas — passo-a-passo numerado

### 3.1 Estrutura de diretórios (novo + preservado)

```
docs/CLIENTES/
├── Felipe_Djalma_STATUS_2026-07-06.pdf            ← SOBRESCREVE (v2.0.0)
├── Felipe_Djalma_STATUS_2026-07-06.md             ← ATUALIZA (mirror v2)
├── Felipe_Djalma_STATUS_2026-07-06.html            ← NOVO (fonte renderizável)
├── Felipe_Djalma_STATUS_2026-07-06.pptx            ← OPCIONAL (python-pptx)
├── archive/
│   └── Felipe_Djalma_STATUS_2026-07-06_v1.1.0.pdf  ← BACKUP do v1 antes do overwrite
├── assets/                                          ← PRESERVADO (8 charts + 16 ícones + fontes)
│   ├── charts/01..08-*.png                          (192 DPI existentes)
│   ├── icons_png/*.png                              (96x96 existentes)
│   └── fonts/Poppins-{Regular,Medium,SemiBold,Bold}.ttf
├── relatorio-2-semanas-felipe-djalma-2026-07-06/    ← PRESERVADO (template base)
│   └── styles/, js/, assets/
├── build/                                           ← NOVO (pipeline Python)
│   ├── __init__.py
│   ├── build.py                                     (orquestrador CLI)
│   ├── render_html.py                               (template f-string)
│   ├── pdf_playwright.py                            (Playwright headless + pre-resolve)
│   ├── pptx_bonus.py                                (python-pptx opcional)
│   ├── validate.py                                  (gates: pypdf, qpdf, page count, size)
│   ├── extract/
│   │   ├── extract_commits.py                       (git log --since/--until)
│   │   ├── extract_tests.py                         (pytest --collect-only)
│   │   ├── extract_squads.py                        (parse SQUAD_INDEX.md + GOALS.md)
│   │   ├── extract_timeline.py                      (PROGRESS.md + .brain/memory/*.md)
│   │   ├── extract_kpis.py                          (agregador principal)
│   │   └── extract_lessons.py                       (.harness/memory/MEMORY.md parser)
│   ├── data/                                        ← INTERMEDIÁRIO (JSON)
│   │   ├── kpis.json
│   │   ├── commits.json
│   │   ├── tests.json
│   │   ├── squads.json
│   │   ├── timeline_hourly.json                     ← 14d hora-a-hora
│   │   ├── lessons.json
│   │   └── plano_providers.json                     ← equivalência A-G
│   ├── templates/
│   │   ├── report.html
│   │   └── sections/
│   │       ├── 01_capa.html
│   │       ├── 02_sumario.html
│   │       ├── 03_carta.html
│   │       ├── 04_indice.html
│   │       ├── 05_timeline_14d.html
│   │       ├── 06_infra_27_servicos.html
│   │       ├── 07_backend_api.html
│   │       ├── 08_lgpd.html
│   │       ├── 09_squads.html
│   │       ├── 10_llm_pipeline.html
│   │       ├── 11_custos.html
│   │       ├── 12_bugs_lessons.html
│   │       ├── 13_pendencias_humanas.html
│   │       ├── 14_conclusao_roadmap.html
│   │       ├── 15_apendices.html
│   │       └── 16_creditos.html
│   └── out/                                         (artefatos intermediários)
└── CHANGELOG-RELATORIOS-CLIENTES.md                 ← APPEND entrada v2.0.0
```

### 3.2 Build pipeline Python (Playwright + python-pptx opcional)

**`build/build.py`** (orquestrador, entry point CLI `python -m build.build`):

```python
def main():
    # Step 1: extract data
    run("python -m build.extract.extract_commits")    # → data/commits.json
    run("python -m build.extract.extract_tests")      # → data/tests.json
    run("python -m build.extract.extract_squads")     # → data/squads.json
    run("python -m build.extract.extract_timeline")   # → data/timeline_hourly.json
    run("python -m build.extract.extract_kpis")       # → data/kpis.json
    run("python -m build.extract.extract_lessons")    # → data/lessons.json

    # Step 2: render HTML
    html_path = render_html(
        template="build/templates/report.html",
        data={**load_all_json("build/data/")},
        css=[
            "relatorio-2-semanas-felipe-djalma-2026-07-06/styles/tokens.css",
            "relatorio-2-semanas-felipe-djalma-2026-07-06/styles/main.css",
            "relatorio-2-semanas-felipe-djalma-2026-07-06/styles/print.css",
        ],
    )
    save(html_path, "docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.html")

    # Step 3: PDF Playwright (pre-resolve counters antes de page.pdf)
    pdf_path = pdf_playwright(
        html_path=html_path,
        out="docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf",
    )

    # Step 4: bonus PPTX (não-bloqueante)
    try:
        pptx_bonus(kpis=kpis, out="docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pptx")
    except Exception:
        log("PPTX pulado — não bloqueia gate")

    # Step 5: validate
    validate(pdf=pdf_path, gates={
        "pages_min": 40,
        "pages_max": 55,
        "size_max_mb": 30,
        "page_w_mm": 210,
        "page_h_mm": 297,
        "font_loaded_poppins": True,
    })
```

**`build/pdf_playwright.py`** (núcleo crítico, lesson 142):

```python
from playwright.sync_api import sync_playwright

def pdf_playwright(html_path, out):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--font-render-hinting=none"])
        ctx = browser.new_context(viewport={"width": 1240, "height": 1754})  # ~A4 @150dpi
        page = ctx.new_page()

        # file:// URL para carregar @font-face local
        page.goto(f"file://{html_path}", wait_until="networkidle")
        page.wait_for_timeout(800)  # fonts async

        # === PRE-RESOLVE COUNTERS (lesson 142 lesson 1) ===
        page.evaluate("""
          () => {
            document.querySelectorAll('[data-counter]').forEach(el => {
              const final = el.dataset.counter;
              el.textContent = Number(final).toLocaleString('pt-BR');
              el.dataset.resolved = '1';
            });
            // disable smooth animations
            document.querySelectorAll('*').forEach(el => {
              const s = getComputedStyle(el);
              if (s.transition && s.transition !== 'all 0s ease 0s') {
                el.style.transition = 'none';
              }
            });
          }
        """)

        # === PDF PRINT ===
        page.pdf(
            path=out,
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
    return out
```

**Dependências Python** (registrar em `backend/pyproject.toml` group `docs` ou `requirements-docs.txt`):
- `playwright>=1.45` (com `playwright install chromium`)
- `jinja2>=3.1` (template)
- `python-pptx>=0.6.21` (opcional, bônus)
- `pypdf>=4.0` (validação gate)
- Já existentes no projeto: nenhuma nova lib pesada

### 3.3 HTML template structure (15+ sections, 45-50 pages target)

Cada section é um page-break A4. Distribuição-alvo:

| # | Section | Páginas | Conteúdo nuclear |
|---|---|---|---|
| 01 | **Capa** | 1 | Logo Cartório SVG + título "Relatório Executivo · 2º Serviço Notarial de Uberlândia" + data 06/Jul/2026 + destinatários Felipe & Djalma + remetente Gustavo Almeida + KPI hero `data-counter="852"` |
| 02 | **Sumário executivo** | 1-2 | 5 KPIs gigantes + warning coverage 87%/gate 90% + badge fonte |
| 03 | **Carta de abertura** | 1 | Texto integral do MD v1 seção 2 + assinatura |
| 04 | **Sumário visual (índice)** | 1 | 15 itens clicáveis (no HTML; no PDF vira lista numerada) |
| 05 | **Timeline 14 dias hora-a-hora** | 5-7 | 14 rails diários (1 por dia); rail crítico com granularidade hora-a-hora (deploys 22/06, 25/06, 30/06, 02/07, 04/07, 06/07 + incidentes INC-2026-07-01-A, Redis auto-recovery, Telegram 502) + `01-timeline-14d.png` + `02-commits-por-dia.png` |
| 06 | **Infraestrutura · 27 serviços Docker Swarm** | 3-4 | Grid 4-col com 12+ ícones (vps, evolution, openclaw, n8n, chatwoot, litellm, supabase, redis, db, llm, obs, status_ok); tabela latência/uptime; status pill (ok/down/warn/q) |
| 07 | **Backend & API** | 4-5 | Diagrama SVG `arquitetura-swarm.svg` + 100 endpoints / 24 tags + cobertura por módulo + tabela de routers (v1 + v2 alpha) + middleware chain |
| 08 | **LGPD Compliance** | 2-3 | 3 camadas PII scrubbing (input/pre-LLM/output) + audit chain SHA256+HMAC + 18 LGPD rights + RIPD v1.3 + tabela DPO duties + ícone `lgpd` + `lock` + `audit` |
| 09 | **Squads · 8 squads × progresso** | 3-4 | Reusar `05-squads-progress.png` 100% + grid detalhado por squad (A-J + BRAIN) com task-by-task |
| 10 | **Pipeline LLM (LiteLLM + Planos A-G)** | 3-4 | Diagrama de fallback + tabela Plano A/B/C/D/E/F/G **com nome técnico no apêndice** (Plano A=opencode_go, B=openclaw_router, …) + latência por provider (`04-latencia-provider.png`) + tokens (`07-tokens-consumo.png`) |
| 11 | **Custos operacionais** | 2 | Tabela breakdown por provider/dia/tipo + comparativo R$ 0 vs R$ 2.500/mês + ROI 12 meses |
| 12 | **Bugs, falhas & lessons** | 3-4 | Grid das 18 lessons principais (109-142) com badge severity + tabela 3 incidentes críticos (INC-2026-07-01-A Easypanel key, Redis auto-recovery, Telegram 502 parse_mode HTML) |
| 13 | **Pendências humanas (SUI)** | 1 | 6 SUI priorizadas + tempo estimado < 15 min + quadro de responsabilidade |
| 14 | **% Conclusão + roadmap** | 2-3 | Reusar `06-conclusao-goals.png` + reusar `08-insertions-deletions.png` + roadmap P0/P1/P2 + critério go-live 100% |
| 15 | **Apêndices** | 4-5 | (A) Glossário 24 termos · (B) MCP servers 6 serviços · (C) Plano A-G equivalência técnica · (D) Lista dos 100 endpoints · (E) Provenance table (fonte de cada número) |
| 16 | **Créditos & contato** | 1 | Gustavo Almeida · Modified by Gustavo Almeida · 06/07/2026 |

### 3.4 Design system (CSS tokens + glass mode + Poppins fallback)

**Reusar integralmente** os 3 CSS existentes em `relatorio-2-semanas-felipe-djalma-2026-07-06/styles/`:
- `tokens.css` — Fibonacci 8/13/21/34/55/89/144, navy `#0f172a`, glass `rgba(255,255,255,0.72)`, type scale 12→74px
- `main.css` — `.card`, `.kpi-grid`, `.timeline-rail`, `.donut-wrap`, `.cover`, `.cols-{2,3,4}`, badges
- `print.css` — `@page A4 portrait`, `page-break-inside: avoid` para cards/tables/figures, strip `backdrop-filter` no print

**Mudanças mínimas** (apenas incrementos no `main.css`):

```css
/* Novo: rail horário para timeline granular */
.hourly-rail { display: grid; grid-template-columns: 4rem 1fr; gap: var(--s-1); margin-bottom: var(--s-1); }
.hourly-rail .h { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: var(--fs-xs); color: var(--c-fg-muted); padding-top: 2px; }
.hourly-rail .e { font-size: var(--fs-sm); line-height: 1.55; }

/* Novo: badge de fonte (provenance) */
.source-badge { display: inline-block; font-size: 9px; font-weight: 500; padding: 2px 6px; border-radius: 3px; letter-spacing: 0.04em; text-transform: uppercase; vertical-align: middle; margin-left: 4px; border: 1px solid; }
.source-badge.git { color: #047857; border-color: rgba(4,120,87,0.3); background: rgba(4,120,87,0.04); }
.source-badge.pytest { color: #1e3a8a; border-color: rgba(30,58,138,0.3); background: rgba(30,58,138,0.04); }
.source-badge.heuristic { color: #b45309; border-color: rgba(180,83,9,0.3); background: rgba(180,83,9,0.04); }
.source-badge.manual { color: #6b7280; border-color: rgba(107,114,128,0.3); background: rgba(107,114,128,0.04); }
.source-badge.mixed { color: #0f172a; border-color: rgba(15,23,42,0.3); background: rgba(15,23,42,0.04); }

/* Novo: chip de Plano A-G */
.plano-tag { display: inline-block; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 999px; color: white; letter-spacing: 0.04em; }
.plano-tag.A { background: #0f172a; }
.plano-tag.B { background: #1e3a8a; }
.plano-tag.C { background: #0369a1; }
.plano-tag.D { background: #0e7490; }
.plano-tag.E { background: #0d9488; }
.plano-tag.F { background: #059669; }
.plano-tag.G { background: #7c3aed; }

/* Fallback chain no body (lesson 142 lesson 7) */
body { font-family: 'Poppins', 'Inter', 'Helvetica Neue', Arial, system-ui, -apple-system, sans-serif; }
```

### 3.5 Integração com assets existentes

**Decisão**: manter `src` relativo (não inline base64) para HTML legível e pequeno (~400KB vs ~4MB inline-base64). Playwright aceita `file://` nativamente.

Layout dos 8 charts (page allocation):
- `01-timeline-14d.png` → capa seção 05 (header timeline 14d)
- `02-commits-por-dia.png` → sub-bloco seção 05 (commits/dia)
- `03-testes-por-cycle.png` → seção 14 (% conclusão)
- `04-latencia-provider.png` → seção 10 (header LLM pipeline)
- `05-squads-progress.png` → seção 09 (header squads)
- `06-conclusao-goals.png` → seção 14 (header % conclusão)
- `07-tokens-consumo.png` → seção 10 (sub-bloco tokens)
- `08-insertions-deletions.png` → seção 14 (sub-bloco insertions/deletions)

Layout dos 16 ícones:
- capa seção 01: ícone `bot` + `lock` (LGPD)
- seção 06 (27 serviços): grid `vps, evolution, openclaw, n8n, chatwoot, litellm, supabase, redis, db, llm, obs, status_ok`
- seção 08 (LGPD): ícone `lgpd` + `lock` + `audit`
- seção 10 (LLM): ícone `litellm` + `llm` + `openclaw`
- seção 12 (lessons): ícone `loop`

### 3.6 Geração de dados estruturados (6 extractors)

| Script | Fonte | Output |
|---|---|---|
| `extract_commits.py` | `git -C /Users/gustavoalmeida/projetos/Cartorio log --since="2026-06-22" --until="2026-07-07" --pretty=format:'%H\|%ai\|%an\|%s'` | `data/commits.json` (lista 852 commits + agregação diária 14d) |
| `extract_tests.py` | `cd backend && uv run pytest --collect-only -q` | `data/tests.json` ({total: 1793, by_module: {...}, coverage_pct: 87}) |
| `extract_squads.py` | parse de `SQUAD_INDEX.md` + `GOALS.md` (regex `Squad X \d+/\d+`) | `data/squads.json` (8 squads × tarefas) |
| `extract_timeline.py` | parse de `PROGRESS.md` (1311+ linhas) + `.brain/memory/*.md` (10+ arquivos) → agrupar por dia/hora | `data/timeline_hourly.json` (14 dias × 24h events) |
| `extract_kpis.py` | agregador → chama os 5 acima + lê `STATUS.md`, `SERVICE_INVENTORY.md`, `SPRINT_REVIEW_2026-07-02.md` | `data/kpis.json` (5 KPIs hero + secundários) |
| `extract_lessons.py` | parse `.harness/memory/MEMORY.md` (regex `lesson-\d+`) + arquivos individuais | `data/lessons.json` (140 lessons → top 18 selecionadas) |

Todos os scripts salvam JSON com schema `{ "source": "git|pytest|heuristic|manual", "value": ..., "evidence": "commit hash | test file | commit msg", "fetched_at": "ISO8601" }` para proveniência explícita na seção apêndice (E) Provenance.

### 3.7 Counter animation pre-resolve via `page.evaluate`

Já coberto em 3.2 — código crítico no `pdf_playwright.py`. Adicional:
1. Adicionar `data-counter` (target) em cada KPI no HTML.
2. Pré-passo Playwright roda `page.evaluate()` ANTES do `page.pdf()` para forçar `el.textContent = Number(target).toLocaleString('pt-BR')` — elimina o bug do Chromium headless não disparar `IntersectionObserver` durante `page.pdf()`.
3. Também zera `transition` e `animation` em todos elementos via `el.style.transition = 'none'` para garantir render estático.
4. Wait adicional de 800ms após `page.goto()` para garantir que `@font-face` foi aplicado antes do evaluate.

### 3.8 Plano A-G naming + tabela de equivalência

**No corpo** (seções 10 LLM Pipeline, 11 Custos, 12 Lessons):
- Toda menção a provider vira **Plano A**, **Plano B**, …, **Plano G** (sem nome técnico).
- Cores por plano (chip): A=`#0f172a` (navy), B=`#1e3a8a`, C=`#0369a1`, D=`#0e7490`, E=`#0d9488`, F=`#059669`, G=`#7c3aed`.

**Em apêndice (C) Plano A-G equivalência técnica** (página final):

| Plano | Nome interno | Provider | Modelo default | Latência média | Custo/token |
|---|---|---|---|---|---|
| **A** | opencode_go | opencode | google/gemini-2.5-pro | 8.2s | R$ 0,00 |
| **B** | openclaw_router | openclaw | claude-opus-4.5 | 11.4s | R$ 0,00 |
| **C** | chiho_free | openrouter | meta/llama-3.3-70b | 9.7s | R$ 0,00 |
| **D** | jules_gw | jules | claude-sonnet-4 | 7.1s | R$ 0,00 |
| **E** | openrouter_route | openrouter | anthropic/claude-3.5 | 12.3s | R$ 0,00 |
| **F** | deepseek_dpa | deepseek | deepseek-chat | 10.8s | R$ 0,00 |
| **G** | openai_fallback | openai | gpt-5.5 | 14.0s | R$ 0,00 |

Decisão pedagógica: o sigilo visual no corpo valoriza o cliente (sigilo comercial de stack), e a equivalência técnica fica acessível a auditor/forense em apêndice.

### 3.9 Validação (gates)

**`build/validate.py`** — todos devem passar:

| Gate | Valor esperado | Comando |
|---|---|---|
| `pages_count` | 45 ≤ n ≤ 55 | `pypdf.PdfReader(path).len` |
| `size_mb` | ≤ 30 | `os.path.getsize / 1024^2` |
| `a4_dimensions` | 595×842 pts ± 1 | `page.mediabox` |
| `poppins_loaded` | True | scrape text "Poppins" no stream |
| `pdf_text_extractable` | True capa | `pdftotext -layout page1` |
| `qpdf_check` | exit 0 | `qpdf --check` |
| `no_orphan_pages` | True | nenhuma page em branco no meio |
| `charts_present` | 8 | grep `image` objects |

Falha em qualquer gate → exit 1 + log estruturado. CI futura integra este script.

---

## 4. Decisões & Assumptions

1. **Incrementar sem quebrar**: o PDF v1.1.0 (22p) é preservado como `.bak` em `docs/CLIENTES/archive/Felipe_Djalma_STATUS_2026-07-06_v1.1.0.pdf` antes do overwrite v2.0.0.
2. **Inline vs src relativo**: escolhida **src relativo** (`file://`) para manter HTML legível e pequeno (~400KB vs ~4MB inline-base64). Playwright aceita nativamente.
3. **PPTX como bônus não-bloqueante**: build não falha se `python-pptx` ausente; gera PPTX simples (5 slides resumo) só se lib disponível.
4. **Poppins self-host vs CDN**: tentativa anterior de CDN falhou (offline); solução é `@font-face` apontando para `assets/fonts/Poppins-*.ttf` (já existem no disco), com stack fallback robusta `Poppins, Inter, Helvetica Neue, Arial, system-ui, sans-serif`.
5. **Hourly granularity só onde crítico**: 14 dias com rail diário; granularidade hora-a-hora aplicada apenas em (a) deploys (22/06, 25/06, 30/06, 02/07, 04/07, 06/07) e (b) incidentes (INC-2026-07-01-A, Redis auto-recovery, Telegram 502). Demais dias: rail diário com 1-3 marcos cada.
6. **Source badges**: todo número exposto ganha `<span class="source-badge git">git</span>` ou `pytest` / `heuristic` / `manual`. Apêndice (E) Provenance lista 100% dos números com fonte primária.
7. **Naming Plano A-G**: assumido pelo briefing. Decisão pedagógica: cliente não vê stack comercial; auditor/forense vê equivalência técnica em apêndice. Reversível trivial.
8. **MD mirror regenerado**: a partir do HTML/PDF final, não reescrito à mão; fonte de verdade é `build/data/*.json`.
9. **Cobertura 87%**: reproduzido honestamente como WARNING no sumário (gate é 90%); não mascara.
10. **PII zerada**: este relatório não cita nenhum CPF/RG/chat_id completo; o `66***225505` da seção 7 v1 é mascarado da mesma forma no v2.

---

## 5. Verificação (como validar)

**Antes do commit final, executar na ordem**:

1. `cd /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/build && python -m build.build` → termina com exit 0.
2. `ls -lh ../Felipe_Djalma_STATUS_2026-07-06.pdf` → tamanho entre 1.0MB e 5.0MB (vs 0.59MB do v1 — esperado crescer por conteúdo adicional).
3. `python -c "from pypdf import PdfReader; r=PdfReader('../Felipe_Djalma_STATUS_2026-07-06.pdf'); print(len(r.pages))"` → 45 ≤ n ≤ 55.
4. `qpdf --check ../Felipe_Djalma_STATUS_2026-07-06.pdf` → exit 0, sem erros.
5. `pdftotext -layout ../Felipe_Djalma_STATUS_2026-07-06.pdf - | head -100` → capa + sumário extraíveis como texto (não imagem escaneada).
6. `open -a Preview ../Felipe_Djalma_STATUS_2026-07-06.pdf` (manual) → verificar visualmente: Poppins carregada, glass mode legível, 8 charts visíveis, 16 ícones presentes, contadores com valor final (não zero), 6 SUI na seção 13, roadmap P0/P1/P2 na seção 14, equivalência A-G na seção 15 (apêndice C).
7. Diff `git diff docs/CLIENTES/CHANGELOG-RELATORIOS-CLIENTES.md` → entrada v2.0.0 presente, página ~45-50 reportada, charts listados.
8. CHANGELOG v2.0.0 menciona: 45-50p, Playwright HTML→PDF, premium glass, 8 charts reusados, 16 ícones reusados, Plano A-G, timeline 14d hora-a-hora.
9. Backup do v1.1.0: `ls docs/CLIENTES/archive/` → `Felipe_Djalma_STATUS_2026-07-06_v1.1.0.pdf` presente.
10. Mensagem conventional commit: `feat(docs): relatório executivo v2.0.0 — Playwright premium + hourly timeline + Plano A-G · Modified by Gustavo Almeida`.

---

## 6. Comando resumido (one-shot)

```bash
# 1. Backup v1.1.0
mkdir -p /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/archive && \
  cp /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf \
     /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/archive/Felipe_Djalma_STATUS_2026-07-06_v1.1.0.pdf

# 2. Install Playwright Chromium (uma vez)
cd /Users/gustavoalmeida/projetos/Cartorio/backend && \
  uv pip install playwright pypdf python-pptx jinja2 && \
  uv run playwright install chromium

# 3. Run full pipeline (extract → html → pdf → pptx → validate)
cd /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/build && \
  python -m build.build

# 4. Verify gates
ls -lh ../Felipe_Djalma_STATUS_2026-07-06.pdf && \
  python -c "from pypdf import PdfReader; print(len(PdfReader('../Felipe_Djalma_STATUS_2026-07-06.pdf').pages),'pgs')" && \
  qpdf --check ../Felipe_Djalma_STATUS_2026-07-06.pdf

# 5. Append CHANGELOG v2.0.0
# (operador edita CHANGELOG-RELATORIOS-CLIENTES.md conforme template abaixo)

# 6. Commit
cd /Users/gustavoalmeida/projetos/Cartorio && \
  git add docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.* docs/CLIENTES/build/ \
          docs/CLIENTES/CHANGELOG-RELATORIOS-CLIENTES.md \
          docs/CLIENTES/archive/ && \
  git commit -m "feat(docs): relatório executivo v2.0.0 — Playwright premium + hourly timeline + Plano A-G · Modified by Gustavo Almeida"
```

**Template da entrada CHANGELOG v2.0.0** (a ser colada):

```markdown
## [2.0.0] · 2026-07-06

### Changed (BREAKING visual upgrade — mesmo período, nova tech stack)
- Renderer: reportlab → Playwright headless Chromium (HTML→PDF)
- Conteúdo: 22p → 45-50p (incremento de ~2x sem repetir, adicionando seções)
- Granularidade timeline: diária → **hora-a-hora onde crítico** (deploys + incidentes)
- Visual: glass/white mantido + Plano A-G naming no corpo (sigilo comercial)

### Added
- 4 seções novas: Sumário visual (índice), Timeline 14d hora-a-hora expandida,
  Plano A-G equivalência técnica em apêndice, Provenance table (fonte por número)
- Pre-resolve counter via page.evaluate() (lesson 142 — Chromium headless não roda IntersectionObserver)
- Source badge em todo número (`<span class="source-badge git|pytest|heuristic|manual">`)
- Pipeline Python determinístico em `docs/CLIENTES/build/` (6 extractors + render + PDF + validate)
- Backup automático do v1.1.0 em `docs/CLIENTES/archive/Felipe_Djalma_STATUS_2026-07-06_v1.1.0.pdf`

### Reused (sem regerar — preserva trabalho do v1)
- 8 charts matplotlib @192 DPI em `assets/charts/01..08-*.png`
- 16 ícones Pillow @96x96 em `assets/icons_png/`
- 4 fontes Poppins TTF em `assets/fonts/`
- CSS tokens + main + print de `relatorio-2-semanas-felipe-djalma-2026-07-06/styles/`

### Stack técnica do relatório
- Playwright 1.45+ (Chromium headless)
- HTML autoral + CSS reusado (3 arquivos)
- python-pptx (bônus opcional, não bloqueante)
- pypdf + qpdf para gates de validação
- Execução ponta-a-ponta: ~12 min em máquina local

### Métricas-alvo do PDF
- Páginas: 45 a 50 (gate)
- Tamanho: 1.0 a 5.0 MB
- Resolução: A4 595×842 pts
- Idioma: pt-BR
- Producer: Skia/PDF (Chromium headless)
- Validação `qpdf --check`: esperado exit 0
```

---

## 7. Anexo: Fontes de dados por seção (rastreabilidade)

| Seção | Fonte primária | Fonte de validação | Badge |
|---|---|---|---|
| 01 Capa | `SERVICE_INVENTORY.md` (período header) | `data/kpis.json` (KPI hero) | `manual` (período) + `git` (counter) |
| 02 Sumário | `kpis.json` agregado | `git log` + `pytest --collect-only` + `SQUAD_INDEX.md` | `mixed` |
| 03 Carta | reuso integral MD v1 §2 | — | `manual` |
| 04 Índice | renderizado de `sections/*.html` | — | `auto` |
| 05 Timeline 14d | `extract_timeline.py` → `PROGRESS.md` + `.brain/memory/*.md` | `git log --since/--until` por dia | `git` + `manual` (hora granular) |
| 06 27 serviços | `SERVICE_INVENTORY.md` | `docker service ls` (offline snapshot de 2026-07-05) | `manual` |
| 07 Backend/API | `backend/app/api/` (file count) + OpenAPI `app.main:app --reload` | grep routers em `app/main.py` | `mixed` |
| 08 LGPD | `backend/app/services/pii.py` + `audit.py` | `.harness/AGENTS.md` seção security | `manual` |
| 09 Squads | `SQUAD_INDEX.md` + `GOALS.md` | `data/squads.json` regex parse | `manual` |
| 10 LLM pipeline | `.harness/memory/MEMORY.md` lessons 109-128 | `app/services/litellm*.py` env keys | `mixed` |
| 11 Custos | comparativo manual (R$ 0 vs R$ 2.500/mês) | tabela interna `docs/platforms/openrouter.md` | `manual` |
| 12 Lessons | `.harness/memory/lesson-{109..142}.md` (18 selecionadas) | `MEMORY.md` index regex | `manual` |
| 13 SUI | reuso v1 §7 + `HANDOVER.md` | — | `manual` |
| 14 %+Roadmap | `GOALS.md` + `data/squads.json` | `charts/06-conclusao-goals.png` (existente) | `mixed` |
| 15 Apêndices | agregados: glossário `docs/PLATFORMS_*/README.md` + MCP `~/.mavis/mcp/clients/cartorio-mcp-config.json` + Plano A-G via `app/services/litellm.py` | grep | `mixed` |
| 16 Créditos | assinatura fixa | — | `manual` |

---

**Modified by Gustavo Almeida · 06/07/2026**