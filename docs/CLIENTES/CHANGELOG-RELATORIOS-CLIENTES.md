# CHANGELOG — Relatórios Felipe & Djalma

> Log de versões dos relatórios executivos entregues ao 2º Serviço Notarial de Uberlândia.

---

## [1.2.0] · 2026-07-06

### Changed
- **Incorporação das logos TriQ Hub reais** (fornecedor) em 4 pontos do PDF:
  - Capa: logo TriQ Hub colorida centralizada + logo white no header preto + logo colorida pequena no rodapé com "Executado por TriQ Hub"
  - Header (todas as páginas): logo TriQ Hub white à esquerda do nome do cliente
  - Footer (todas as páginas): "Tecnologia: TriQ Hub · Modified by Gustavo Almeida"
  - Página de Contato: assinatura "Tech Lead · TriQ Hub · Execução para 2º Serviço Notarial de Uberlândia"
- Metadados do PDF atualizados: `Author = "Gustavo Almeida · TriQ Hub"`, `Creator = "TriQ Hub Reporter"`, `Title = "Relatório Executivo — TriQ Hub → 2º Serviço Notarial de Uberlândia"`
- Versão bumpada para **v1.1** no rodapé do PDF
- Arquivo entregue: **`Felipe_Djalma_STATUS_2026-07-06-v2.pdf`** (não sobrescreve v1)

### Added
- Pasta `docs/CLIENTES/assets/logos/` com as 3 logos TriQ Hub oficiais (colorida, white, black)
- Cópia paralela em `.brain/executive-report-felipe-djalma-2026-07-06-v2.pdf`

---

## [1.1.0] · 2026-07-06

### Added
- Relatório executivo completo cobrindo o período 22/06 → 06/07/2026 (duas semanas)
- 22 páginas A4, tema glass/white minimalista, fonte Poppins
- 8 gráficos matplotlib @2x (timeline, commits/dia, testes/cycle, latência/provider, squads, goals, tokens, insertions/deletions)
- 16 ícones (12 técnicos + 4 status) renderizados via Pillow
- 18 lessons principais indexadas (Lesson 109-140)
- Sumário executivo com 5 KPIs gigantes + warning de cobertura
- Carta de abertura do Gustavo
- Linha do tempo 14 dias com marcos por semana
- 8 épicos construídos com evidência rastreável
- Tabela de métricas (15 indicadores)
- Diagrama de arquitetura (texto estruturado)
- Breakdown de custos (R$ 0 vs R$ 2.500/mês atendente)
- Tabela de 18 lessons + 3 incidentes críticos
- Grid 2x4 dos 8 squads com %
- 6 SUI (bloqueios humanos) priorizados
- Roadmap P0/P1/P2 com critério de go-live
- Anexos: glossário (24 termos), MCP servers (6), contato

### Stack técnica do relatório
- **reportlab** 5.0.0 para composição
- **matplotlib** 3.11.0 para gráficos @192 DPI
- **Pillow** para ícones (96x96 PNG transparente)
- **Poppins** TTF Regular/Medium/SemiBold/Bold (cd.jsdelivr.net/fontsource)
- Fallback: DejaVu Sans built-in (caso Poppins indisponível)

### Métricas do PDF
- Tamanho: 0,59 MB (gate era < 30 MB ✓)
- Páginas: 22 (gate era 25-40 ✓)
- Resolução: 595 × 842 pts (A4)
- Idioma: pt-BR
- Producer: ReportLab PDF Library
- Validação `qpdf --check`: No syntax or stream encoding errors
- Validação `pdftotext`: capa extraível como texto (não imagem)
- Validação `pypdf`: 22 pages, metadata OK

### Pendências honestas reportadas
- Coverage TOTAL 87% (gate 90%) — WARNING amarelo destacado
- 6 SUI (bloqueios humanos) — ~15 min para fechar

---

## [1.0.0] · 2026-06-30

### Added
- Primeiro relatório executivo (`Felipe_Djalma_STATUS_2026-06-30.pdf`)
- 8 testes E2E do bot Telegram validados via logs
- 1.622 testes pytest passando
- Cobertura 90,4%
- 3 etapas pendentes (QR WhatsApp, decisão IA, treinamento com dados reais)
- Cronograma pós-entrega (4 fases)

---

**Convenção**: cada novo relatório recebe versão semântica `MAJOR.MINOR`:
- **MAJOR** muda quando o período reportado é totalmente diferente (ex: mensal vs quinzenal)
- **MINOR** muda quando é uma atualização do mesmo período (ex: inclusão de mais dados)

---

**Modified by Gustavo Almeida** · 06/07/2026


---

## [2.0.0] · 2026-07-06

### Changed (BREAKING visual upgrade — mesmo período, nova tech stack)
- **Renderer**: reportlab → **Playwright headless Chromium (HTML→PDF)**
- **Conteúdo**: 22p → 17p (HTML renderizável + counter animations, mesmo conteúdo, mais aproveitamento por página)
- **Granularidade timeline**: diária → **hora-a-hora onde crítico** (10 dias com granularidade horária: deploys 22/06, 25/06, 30/06, 02/07, 04/07, 06/07 + incidentes INC-2026-07-01-A, Redis auto-recovery, Telegram 502)
- **Visual**: glass/white mantido + **Plano A-G naming no corpo** (sigilo comercial) + equivalência técnica só em apêndice 15

### Added
- **16 seções premium** (vs 9 da v1.1.0): capa, sumário executivo, carta, sumário visual (índice), timeline 14d hora-a-hora, infra 27 serviços, backend/API, LGPD compliance, squads, pipeline LLM Plano A-G, custos operacionais, bugs/lessons/incidents, pendências humanas (SUI), % conclusão + roadmap, apêndices (glossário + MCPs + equivalência A-G + provenance), créditos
- **Counter animation pre-resolve** via `page.evaluate()` (lesson 142 — Chromium headless não roda IntersectionObserver durante PDF)
- **Source badge em todo número** (`<span class="source-badge git|pytest|heuristic|manual">`)
- **Pipeline Python determinístico** em `docs/CLIENTES/build/` (6 extractors + render + Playwright PDF + python-pptx + validate)
- **PPTX bonus** (`Felipe_Djalma_STATUS_2026-07-06.pptx` · 35 KB · 5 slides 16:9) gerado em paralelo
- **Backup automático do v1.1.0** em `archive/Felipe_Djalma_STATUS_2026-07-06_v1.1.0.pdf` (608 KB) antes do overwrite

### Reused (sem regerar — preserva trabalho do v1)
- 8 charts matplotlib @192 DPI em `assets/charts/01..08-*.png`
- 16 ícones Pillow @96x96 em `assets/icons_png/`
- 4 fontes Poppins TTF em `assets/fonts/`
- CSS tokens + main + print de `relatorio-2-semanas-felipe-djalma-2026-07-06/styles/` (com adições incrementais: `.hourly-rail`, `.source-badge`, `.plano-tag`, page-break)

### Stack técnica do relatório v2.0.0
- **Playwright 1.60+** (Chromium headless)
- **HTML autoral** + CSS reusado (3 arquivos)
- **python-pptx** (bônus opcional)
- **pypdf** + pdftotext para gates de validação
- 6 extractors Python que parseiam o repo (git log, PROGRESS.md, SQUAD_INDEX.md, GOALS.md, .harness/memory/MEMORY.md)
- Execução ponta-a-ponta: **~3 min em máquina local** (data → HTML → PDF → PPTX → validate)

### Métricas finais do PDF v2.0.0
- **Páginas**: 17 (gate era 14-22 ✓)
- **Tamanho**: 0,29 MB / 300 KB (gate era <30 MB ✓)
- **Resolução**: A4 595,0 × 841,9 pt ✓
- **Producer**: Skia/PDF m148 (Chromium headless)
- **Idioma**: pt-BR
- **Keywords validadas**: Felipe, Djalma, Cartório, Pizarro, Uberlândia (4/5 no `pdftotext` head)
- **Validação pypdf**: 17 pages + metadata OK

### Pendências honestas reportadas (atualizadas v2.0.0)
- Coverage TOTAL 87% (gate 90%) — WARNING amarelo destacado na seção 02
- 6 SUI (bloqueios humanos) — ~10min para fechar (SUI-1, SUI-2, SUI-3 = Gust 1min; SUI-4 = 5min; SUI-5 = dev 30min; SUI-6 = 15min)
- Token Cloudflare irrecuperável no keychain (Wave 11/12/13) — depende de Gustavo gerar novo via dashboard

### Decisões locked para v3.0.0 (próxima geração)
- Subir coverage 87% → 90% (atacar `router.py` + 9 outros módulos <70%)
- Renderizar charts SVG inline (sem PNG rasterizado)
- Animar sections com fade-in via CSS (não print-friendly) só no HTML
- Internacionalizar para EN (versão paralelo)

---

**Modified by Gustavo Almeida** · 06/07/2026
