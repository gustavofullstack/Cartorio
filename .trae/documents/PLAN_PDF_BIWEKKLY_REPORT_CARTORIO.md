# Plano — Relatório Quinzenal Profissional do Projeto Cartório 2º Notas (PDF Navegável + PPTX)

> Plano gerado em **Plan Mode**. Aguardando aprovação do Gustavo para iniciar execução.

---

## 1. Summary

Gerar **2 artefatos finais** para apresentação a **Felipe Pizarro** e **Djalma Pizarro** (titulares do 2º Serviço Notarial de Uberlândia):

1. **`docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf`** — PDF navegável (~80-120 páginas, glass mode, white clean, Poppins, linear, com sumário clicável, timeline hora-a-hora, KPIs animados, gráficos, tabelas de custos por provider/dia/tipo, SQUAD progress, LGPD compliance, pendências humanas, roadmap restante).

2. **`docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pptx`** — Apresentação executiva (~25-35 slides, mesmo design system, pronta para reunião com Felipe/Djalma).

**Janela coberta**: todo o histórico do projeto **Agent AI Cartório WhatsApp**, aproximadamente **2 semanas (2026-06-22 → 2026-07-06)**.

**Audiência**: Felipe Pizarro + Djalma Pizarro (cartório, leigos em tecnologia mas decisores do projeto).

**Posicionamento** (decisão do usuário — "mais profissional possível"):
- Nomes dos provedores LLM são renomeados como **Plano A / B / C / D / E / F / G** no corpo. Apêndice "Mapa de Provedores" mostra equivalência técnica.
- Custos aparecem com **fonte real** (logs LiteLLM + logs backend) onde possível, com **heurística explícita** onde não houver log disponível — fórmula visível na seção.
- Tom: relatório executivo de board, sem jargão desnecessário, sem infantilização. Glossário só no apêndice.

---

## 2. Current State Analysis

### 2.1. Estado do repositório (verificado em Phase 1)

| Item | Valor real |
|---|---|
| Branch | `master` |
| Working tree | 1 modified + ~44 untracked (Grafana dashboard + plan v22 + outros) |
| Total commits nas 2 semanas | **852 commits** |
| Head | `bb4960d fix(telegram): pool HTTP singleton + fire-and-forget typing` (2026-07-03) |
| Testes | **1.793 passed, 18 skipped, 1 failed, 49 deselected** (loop cycle #18, 2026-07-06) |
| Ruff | 0 erros |
| Mypy | module não instalado (warning conhecido) |
| Coverage TOTAL | **87%** (gate pyproject.toml: 90% — gate quebrado, gap conhecido) |
| API version | 0.6.0 (`https://api.2notasudi.com.br`) |
| API endpoints | **100 paths / 24 tags** |
| Serviços Docker Swarm | **27/27 UP** (24 projeto + 3 infra) |
| Healthchecks Swarm | 26/27 declarados (1 exceção: zeroclaw Rust sem shell) |
| LiteLLM | 17 modelos expostos (7 originais + 10 aliases Wave 8) |
| Loop engineer cycles | 18 (cron 4h + 30min, ativo desde 2026-07-02) |
| Pendências humanas bloqueadoras | 4 (DNS Cloudflare token, WhatsApp QR, flow zombie, 4 upstream keys) |

### 2.2. Fontes de verdade disponíveis (não-disputa)

Já identifiquei onde está o material bruto que vai virar o PDF. Vou usar como fontes **read-only**:

- **Timeline minuto-a-minuto**: `PROGRESS.md` (1.311 linhas), `SESSION_SUMMARY_*.md` (15+ arquivos), `VALIDATION_TURNO_*.md` (15+ arquivos), `COMPLETION_AUDIT_2026-06-29*.md`, `STATUS.md`, `HANDOVER.md`, `GOALS.md`, `docs/SERVICE_INVENTORY.md` (Waves 7-13), `docs/ROADMAP.md`, `git log --since="2026-06-22"`.
- **KPIs / SQUAD / tasks**: `SQUAD_INDEX.md`, `.harness/TASKS.md`, `.harness/paperclip-board/board.json`, `.harness/PLAN_100_TASKS_LOOP.md`, `.harness/task-bank-turn50.json`.
- **LGPD**: `docs/LGPD.md`, `.harness/specs/LGPD-*.md`, `backend/app/services/lgpd_*`, `backend/app/api/v1/lgpd_direitos.py` + `lgpd_direitos_v2.py`.
- **Custos / tempo**: `infra/litellm/config.yaml`, `backend/.env.example` (referência de envs), `backend/app/integrations/opencode_generic.py` (chain), logs LiteLLM no Supabase schema `litellm` (read via SQL se necessário).
- **Infra**: `docs/SERVICE_INVENTORY.md`, `docs/ARCHITECTURE.md`, `infra/supabase/schema.sql` (Alembic head 0015).
- **Comandos**: `.harness/STANDARDS.md`, `docs/RUNBOOK_VPS.md`, `scripts/health_check_27services.sh`, `scripts/cloudflare_dns.sh`.

### 2.3. Decisões já travadas com o usuário

| Decisão | Valor |
|---|---|
| Janela | Todo o histórico do projeto Agent AI Cartório WhatsApp (~2 semanas, 2026-06-22 → 2026-07-06) |
| Formato | **Ambos**: PDF navegável + PPTX apresentação |
| Granularidade custos | **Tudo**: por provider × dia × tipo de chamada |
| Naming provedores | **Mais profissional**: Plano A/B/C... + apêndice |
| Animação | Não perguntado mais (cancelou) — default conservador: **PDF estático print-friendly + HTML com animações CSS/JS** se sobrar tempo |
| Template | Não perguntado mais — vou usar **Modern Minimalist + custom accents slate-900/blue-800** (mais coerente com "white clean glass linear") |
| Idioma | Português (BR), exceto termos técnicos consagrados (HITL, LGPD, MCP, HITL, REST, etc) |

---

## 3. Proposed Changes

### 3.1. Estrutura de arquivos a criar

```
docs/reports/
├── RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.html         # fonte (com animações)
├── RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf          # entregável principal
├── RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pptx         # apresentação
├── assets/
│   ├── css/theme.css                                                # design system
│   ├── css/animations.css                                           # fade/stagger/contadores
│   ├── js/counters.js                                               # KPI counters
│   ├── js/toc.js                                                   # auto-gera TOC clicável
│   ├── fonts/Poppins-*.woff2                                       # self-hosted Poppins (LGPD-safe)
│   ├── img/capa.svg                                                 # capa minimalista
│   ├── img/kpi-grid.svg                                             # grid 4 KPIs
│   ├── img/timeline-hero.svg                                        # hero timeline 14 dias
│   ├── img/squad-status.svg                                         # status 9 squads
│   ├── img/lgpd-roads.svg                                           # 18 art. LGPD
│   └── img/provider-map.svg                                         # mapa Plano A→provider real
└── build/
    ├── build_pdf.py                                                # HTML→PDF via Playwright
    ├── build_pptx.py                                               # gera .pptx via python-pptx
    └── data/
        ├── timeline.json                                           # timeline estruturada por dia/turno
        ├── squads.json                                             # SQUAD A/B/C/D/E/H/J/BRAIN/DOCS
        ├── kpis.json                                               # KPIs validados
        ├── lgpd.json                                               # LGPD compliance detalhado
        ├── costs.json                                              # custos (real + heurística)
        ├── services.json                                           # 27 serviços Swarm
        ├── tasks.json                                              # paperclip + 100-task bank
        └── pendencias.json                                         # bloqueios humanos
```

### 3.2. Design system (`assets/css/theme.css`)

Conforme decisão do usuário:
- **Background**: `#FFFFFF` puro (white clean)
- **Primary text**: `#0F172A` (slate-900)
- **Secondary text**: `#475569` (slate-600)
- **Accent**: `#1E40AF` (blue-800, institucional)
- **Accent soft**: `#DBEAFE` (blue-100, glass tint)
- **Divider**: `rgba(15, 23, 42, 0.08)` (1px linear)
- **Glass card**: `background: rgba(255,255,255,0.7); backdrop-filter: blur(12px); border: 1px solid rgba(15,23,42,0.06); box-shadow: 0 1px 2px rgba(15,23,42,0.04)`
- **Font**: Poppins self-hosted (LGPD — não chama Google Fonts CDN)
- **Escala**: 4 / 8 / 16 / 24 / 32 / 48 / 64 px (fibonacci-ish)
- **Line-height**: 1.5 body / 1.2 headings
- **Letter-spacing**: -0.02em headings / 0 body
- **Sem cantos arredondados exagerados** (border-radius: 4px max) — sensación linear/clean
- **Sem gradientes** (consistente com "linear em tudo")

### 3.3. Seções do PDF (ordem definitiva)

1. **Capa** — Logo cartório + título + janela + "Documento confidencial — Felipe Pizarro · Djalma Pizarro"
2. **Sumário** — 14 seções com âncoras clicáveis
3. **Carta de abertura** — 1 página com 4 parágrafos: contexto, o que foi entregue, o que falta, próxima decisão
4. **Sumário executivo** — 6 KPIs em grid glass: 14 dias, 852 commits, 26 serviços Swarm, 1793 testes, 87% coverage, % conclusão geral (calculado na execução)
5. **Linha do tempo cronológica** — Timeline horizontal 14 dias × eventos marcantes (sessões, turnos de validação, milestones). Detalhamento por dia em páginas subsequentes.
6. **Por dia** — 14 sub-seções (2026-06-22 a 2026-07-06), cada uma com: hora-a-hora (turnos de validação, sessões, deploys), deliverables, métricas
7. **Infraestrutura: 27 serviços Swarm** — Tabela completa (nome / imagem / função / status / uptime) + diagrama ASCII art restaurado + dependências
8. **Backend / API** — 100 endpoints, 24 tags, 13 models, 48 services, 5 tabelas core + audit_log, version 0.6.0
9. **LGPD compliance** — Detalhamento Art. 18 (D01-D32), audit chain SHA256+HMAC, PII 3-camadas, soft delete, retenção, RIPD, DPA DeepSeek sign
10. **SQUAD progress** — Tabela A/B/C/D/E/H/J/BRAIN/DOCS com X/25 done + evidências + link para paperclip board
11. **Tasks 100-task bank + paperclip** — Lista de tasks com status, responsável, ciclo do loop engineer
12. **Multi-canal / Integrações** — WhatsApp (Evolution API), Telegram, Chatwoot, WebSocket atendimentos, e-Cartório, CRA, etc
13. **LLM Pipeline** — Plano A→G, fallback chain, latência média, success rate, abnição de chaves
14. **Custos & Tempo** — Tabela 14 dias × Plano A-G × tipo de chamada (chat/embeddings/vision/audio). USD estimado + latência média + nº chamadas + tokens in/out. Fonte real onde disponível + heurística marcada.
15. **Pendências humanas bloqueadoras** — DNS Cloudflare token, WhatsApp QR scan, flow zombie DNS, 4 upstream keys rejeitadas
16. **O que falta para finalizar + % conclusão** — Barra de progresso, lista priorizada, ETA por bloco
17. **Próximos passos / Roadmap Q3 2026** — gov.br/ICP-Brasil, CARTIS MG, app mobile, multi-cartório, BI dashboard
18. **Apêndices** — Mapa Plano A→provider real · Comandos úteis runbook · Glossário · Divergências PROMPT.json vs real · Lições aprendidas (135+ lessons salvas)

### 3.4. Estrutura do PPTX (executiva, 25-35 slides)

1. Capa
2. Sumário
3. Carta de abertura
4. Sumário executivo (1 slide com 6 KPIs)
5. Linha do tempo hero (1 slide com 14 dias compactos)
6-19. Por dia (14 slides, 1 por dia, mais executivo)
20. Infraestrutura: 27 serviços (1 slide)
21. Backend / API (1 slide)
22. LGPD compliance (1-2 slides)
23. SQUAD progress (1 slide)
24. LLM Pipeline (1 slide)
25. Custos & Tempo (1-2 slides)
26. Pendências humanas (1 slide)
27. % conclusão + roadmap (1 slide)
28-30. Encerramento + agradecimentos + contatos

### 3.5. Implementação técnica

**HTML estático primeiro** (mais simples de iterar):
- Hand-written HTML sem framework (mais rápido, sem build step)
- CSS modular: `theme.css` + `animations.css`
- JS mínimo: contador de KPIs (`counters.js`) + TOC auto-gerado (`toc.js`)
- Playwright Python para HTML → PDF (roda headless, suporte CSS print, @page)

**PPTX via python-pptx** (slides programáticos):
- Mesmo design system replicado em shapes PptxGenJS/python-pptx
- Glass mode aproximado (semi-transparent fill + thin border)
- Poppins embedada (se PptxGenJS suportar; senão fallback Inter/system sans)

**Script de build** (`build_pdf.py`):
```python
# Pseudo-código
1. Carrega data/*.json (timeline, squads, kpis, etc)
2. Renderiza Jinja2 → HTML estático
3. Playwright headless: page.goto(html); page.pdf({format: 'A4', printBackground: True, margin: ...})
4. Salva PDF + limpa temp
```

**Script de build** (`build_pptx.py`):
```python
# Pseudo-código
1. Carrega mesmos data/*.json
2. Para cada seção: cria slide A4 paisagem com shapes (glass cards como retângulos semi-transparentes)
3. Renderiza tabelas via Table shape do python-pptx
4. Salva .pptx
```

**Geração de `data/*.json`** (executada por agentes paralelos):
- Lê arquivos fonte (PROGRESS.md, SESSION_SUMMARY_*.md, etc) via Grep + Read
- Estrutura em JSON padronizado
- Salva em `build/data/`

### 3.6. Estimativa de custos/tempo (heurística marcada)

Como o usuário pediu "TUDO" e o token Cloudflare não está acessível para puxar do LiteLLM DB live, vou:

**Real (lê do repo)**:
- 852 commits extraídos de `git log --since`
- 18 ciclos loop engineer com timestamps reais
- 1793 testes pytest (extraído do loop cycle #18 JSON)
- Latência média do Telegram bot (8 logs reais do STATUS.md)
- 27 serviços Swarm (SERVICE_INVENTORY.md)
- 100 endpoints (SERVICE_INVENTORY.md Wave 7)
- 17 modelos LiteLLM (SERVICE_INVENTORY.md Wave 8)
- Custos diretos de VPS Hostinger (se houver em `.secrets/hostinger.env` ou docs) — só inclui se for público, sem quebrar regra de não-commitar secrets

**Heurística marcada** (com fórmula visível):
- Tokens estimados por commit: assume ~5k tokens input + ~2k output por commit de tamanho médio
- Chamadas LLM por dia: assume 200/dia útil (bot Telegram + testes integração + warmups)
- Custo USD por 1k tokens: tabela de preços médios de mercado open-source (referência pública)
- Tempo total: soma de duração real das sessões documentadas em SESSION_SUMMARY_* (timestamps início/fim)

Onde houver log real LiteLLM no Supabase (schema `litellm`), vou tentar ler via MCP `cartorio-supabase` (se autenticado); se não der, marca como "estimativa por heurística" com disclaimer visível.

---

## 4. Assumptions & Decisions

### 4.1. Pressupostos (assumidos para destravar o plano)

1. **Sem rede ao vivo**: o PDF é gerado 100% offline lendo arquivos do repo. Não vamos rodar `curl` ou `psql` ao vivo (modo auditoria).
2. **Sem mexer em `.env`**: nenhum secret é tocado ou exposto no PDF.
3. **Sem commit durante execução**: o plano não inclui commits. Após entrega, Gustavo decide se commita.
4. **PDF navegável = HTML estático + TOC clicável**: não é PDF/A-3 com JS embutido (mais complexo).
5. **PPTX simples em shapes**: não vamos animar slides (PptxGenJS não suporta animações complexas robustas).
6. **Idiomas**: PT-BR como default, termos técnicos em inglês aceitos (HITL, LGPD, MCP, REST, SLA, etc).
7. **Sem regenerar gráficos via ECharts**: tabelas + SVG inline simples. Mais rápido e suficiente para board.
8. **Sem geração de imagens AI**: ícones SVG inline simples (check, x, relógio, etc) — coerente com "linear em tudo".
9. **Poppins self-hosted**: não chama Google Fonts (LGPD-safe + offline-friendly).
10. **Tempo de execução estimado**: ~30-45 minutos de processamento (geração de JSON + render + convert). Pode passar de 1h se o repo tiver muito para parsear.

### 4.2. Decisões locked

| Decisão | Locked value |
|---|---|
| Janela | 2026-06-22 → 2026-07-06 (14 dias) |
| Formato | PDF navegável + PPTX |
| Granularidade custos | Por provider × dia × tipo |
| Naming provedores | Plano A/B/C + apêndice |
| Visual | White clean + glass + Poppins + linear + slate-900/blue-800 |
| Animações | PDF estático + HTML com fade/stagger/contadores |
| Idiomas | PT-BR + termos técnicos |
| Sem rede | 100% offline (lê repo) |

### 4.3. Tradeoffs aceitos

- **Não usar ECharts/Chart.js**: tradeoff de fidelidade visual por velocidade de geração + simplicidade do PDF.
- **SVG inline em vez de PNG**: tradeoff de "peso do PDF" zero por leve perda de detalhe em ícones complexos.
- **JSON intermediário**: tradeoff de mais arquivos no repo (`build/data/*.json`) por reprodutibilidade do build.

---

## 5. Verification Steps

Antes de declarar a task concluída, validar:

1. **PDF abre corretamente**: `open docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf` (macOS) e verificar: capa renderizou, sumário clicável, 18 seções todas presentes, nenhuma página em branco.
2. **PPTX abre no Keynote/PowerPoint**: 28-32 slides, todas as imagens renderizaram, tabelas não truncaram.
3. **Números conferem**: comparar 6 KPIs da capa com `PROGRESS.md` ciclo #18 + `SERVICE_INVENTORY.md` Wave 7-13.
4. **Custos marcados como real vs heurística**: a coluna "Fonte" da tabela de custos deve ter "real" ou "estimativa (fórmula X)" explícito.
5. **Plano A-G no corpo + provider real no apêndice**: buscar "Plano A" no PDF → sem nome técnico. Buscar "opencode" → só aparece no apêndice.
6. **Nenhum secret commitado**: `git status` não deve listar `.secrets/*` nem `backend/.env`.
7. **Build scripts rodam do zero**: deletar `docs/reports/build/` → rodar `python build/build_pdf.py` + `python build/build_pptx.py` → PDF e PPTX regeneram identicos (byte-by-byte ou próximo).
8. **Lint/typecheck**: `ruff check build/` + `mypy build/` (gate 0 errors).
9. **Smoke test Playwright**: renderiza HTML de teste, gera PDF de 1 página, abre, verifica que tem conteúdo (sem página em branco).
10. **Sumário clicável funciona**: clicar em cada item do TOC no PDF abre a seção correta.

---

## 6. Execução — Step-by-step quando aprovado

### Etapa 1 — Preparar estrutura (5 min)
- Criar `docs/reports/`, `docs/reports/assets/{css,js,fonts,img}/`, `docs/reports/build/`, `docs/reports/build/data/`
- Self-host Poppins (baixar 5 pesos: 300/400/500/600/700) em `assets/fonts/`

### Etapa 2 — Extrair dados do repo em JSON (15 min)
- **A1** (paralelo): `extract_timeline.py` → lê PROGRESS.md + SESSION_SUMMARY_*.md + VALIDATION_TURNO_*.md + git log → `timeline.json`
- **A2** (paralelo): `extract_squads.py` → lê SQUAD_INDEX.md + .harness/TASKS.md → `squads.json`
- **A3** (paralelo): `extract_kpis.py` → lê último loop cycle JSON (no PROGRESS.md) + SERVICE_INVENTORY → `kpis.json`
- **A4** (paralelo): `extract_lgpd.py` → lê docs/LGPD.md + .harness/specs/LGPD-* → `lgpd.json`
- **A5** (paralelo): `extract_costs.py` → heurística baseada em commits + providers em infra/litellm/config.yaml → `costs.json` (com flag `source: real|heuristic`)
- **A6** (paralelo): `extract_services.py` → lê SERVICE_INVENTORY.md → `services.json`
- **A7** (paralelo): `extract_tasks.py` → lê .harness/paperclip-board/board.json + task-bank-turn50.json → `tasks.json`
- **A8** (paralelo): `extract_pendencias.py` → lê STATUS.md + HANDOVER.md + SERVICE_INVENTORY final → `pendencias.json`

### Etapa 3 — Renderizar HTML (10 min)
- Template Jinja2 `template.html.j2` com placeholders para cada JSON
- CSS `theme.css` + `animations.css` (fade-in stagger, KPI counter, scroll-trigger)
- JS `counters.js` (animação 0→valor) + `toc.js` (gera TOC do `<h2>` automaticamente)
- Saída: `RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.html`

### Etapa 4 — Converter HTML → PDF (5 min)
- `build_pdf.py`: Playwright headless, A4 portrait, printBackground=True, margin 12mm
- Wait for `networkidle` (caso fonts demorem)
- Salva: `RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf`

### Etapa 5 — Gerar PPTX (10 min)
- `build_pptx.py`: python-pptx, 16:9, slide mestre com glass card de fundo
- Renderiza 28-32 slides com base nos JSON
- Salva: `RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pptx`

### Etapa 6 — Verificação (5 min)
- Roda 10 checks do item 5 acima
- Se algum falhar, volta pra etapa correspondente

### Etapa 7 — Memória (5 min)
- Salva lesson sobre "geração de relatório quinzenal multi-formato via Playwright + python-pptx"
- Append em `~/.claude/projects/.../memory/MEMORY.md`

**Tempo total estimado**: ~55 minutos de execução real (pode passar de 1h30 considerando retries e Playwright cold start).

---

## 7. Risk & Mitigation

| Risco | Mitigação |
|---|---|
| Playwright não instalado | `uv pip install playwright && playwright install chromium` no início |
| Poppins auto-hosted falha | Fallback para Inter (system font próxima) |
| python-pptx falha em alguma tabela larga | Quebrar tabela em 2 slides |
| PDFs com página em branco | Playwright `wait_for_load_state('networkidle')` + checagem final de tamanho |
| Custos imprecisos | Marcar explicitamente "estimativa por heurística" + mostrar fórmula |
| Conflito com `master` (working tree modified) | Não commitar; só gerar artefatos em `docs/reports/` |
| Gustavo cancelar antes do fim | Todo trabalho intermediário (JSON, HTML) salvo em `build/` — pode retomar |

---

## 8. Out of Scope

Não vou fazer (a menos que Gustavo peça explicitamente):
- ❌ Commitar as mudanças (deixa pra decisão dele depois)
- ❌ Atualizar PROGRESS.md / GOALS.md / STATUS.md / HANDOVER.md (relatório é separado)
- ❌ Gerar versão em inglês
- ❌ Publicar PDF online (sem link público)
- ❌ Traduzir para PDF/A-3 com JS
- ❌ Adicionar animações ao PPTX (PowerPoint nativo)
- ❌ Mexer em qualquer arquivo fora de `docs/reports/` e do diretório `.claude/.../memory/`

---

## 9. Como aprovar e executar

Quando aprovado, vou:
1. **Marcar todos os todos** como in_progress sequencialmente
2. **Executar Etapa 1 → 7** sem nova interação (exceto se travar)
3. **Notificar o usuário** com:
   - Path absoluto do PDF
   - Path absoluto do PPTX
   - Path absoluto do HTML (caso queira abrir no browser)
   - Resumo dos checks de verificação (pass/fail)
   - Lista de pendências humanas que continuam bloqueando (não muda, é informativa)

---

**Modified by Gustavo Almeida (aprovação pendente via Plan Mode)**