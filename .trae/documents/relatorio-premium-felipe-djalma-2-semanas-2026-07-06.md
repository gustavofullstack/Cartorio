# Plano — Relatório Premium 2 Semanas (23/06 → 06/07/2026)

**Para:** Felipe Pizarro & Djalma Pizarro — 2º Serviço Notarial de Uberlândia
**De:** Gustavo Almeida + Equipe Cartório Bot
**Path de saída:** `/Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06/`
**Stack de render:** HTML5 autoral + CSS3 (Poppins, Fibonacci, glass mode) → Puppeteer headless Chromium → PDF A4 print-ready
**Versão do plano:** v1.0 (2026-07-06)

---

## 1. Sumário executivo

Este plano descreve a geração de um PDF premium (~8K-quality, white clean minimalista, glass mode, Poppins, Fibonacci spacing 8/13/21/34/55/89/144 px, full white background) que sintetiza o progresso do projeto Cartório Bot entre **23/06/2026 e 06/07/2026** para apresentação aos donos do 2º Serviço Notarial de Uberlândia. O fluxo é: (a) HTML/CSS/JS autoral single-page com 13 seções + ativos SVG inline; (b) Puppeteer headless renderiza em viewport 1920×1080, `printBackground: true`, `preferCSSPageSize: true`; (c) gera PDF/A4 vertical, fonts Poppins embutidas via `@font-face` self-host (sem CDN), tamanho-alvo 4–6 MB, 28–32 páginas.

---

## 2. Análise do estado atual (o que já temos vs o que falta gerar)

### 2.1 O que JÁ EXISTE no workspace (fontes validadas)

| Recurso | Caminho | Estado |
|---|---|---|
| Relatório anterior (v1, pandoc) | `docs/CLIENTES/Felipe_Djalma_STATUS_2026-06-30.{md,html,pdf}` | Estilo pandoc default, NÃO premium |
| Service Inventory (estado real 27 serviços) | `docs/SERVICE_INVENTORY.md` | Validado 2026-07-02 |
| Goals consolidados A-G | `GOALS.md` | 2026-07-03 |
| Progresso global + meta única | `.brain/memory/2026-07-03-loop-goals.md` | 60% Cartório |
| Diário 23/06 → 03/07 | `.brain/memory/2026-06-25.md`, `2026-06-26*.md`, `2026-06-29.md`, `2026-06-30.md`, `2026-07-01-*.md` (6 files), `2026-07-02.md`, `2026-07-03*.md` | Timeline completo |
| Auditoria 27 serviços pós-deploy | `.brain/memory/2026-07-02-auditoria-pos-deploy.md` | 10/11 OK |
| LGPD D26-D32 review | `docs/reviews/lgpd-review-d26-d32-2026-06-30.md` | LIVE |
| Pendências SUI | `.harness/SUI_CHECKLIST.md`, `GOALS.md` | 6 ações humanas |
| Docs oficiais | `docs/ARCHITECTURE.md`, `docs/LGPD.md`, `docs/ROADMAP.md`, `docs/SERVICE_INVENTORY.md`, `docs/SPRINT_REVIEW_2026-07-02.md` | Pronto para extração |
| Quick refs plataformas | `docs/architecture/`, `docs/platforms/{n8n,evolution-api,chatwoot,supabase,redis}/` | 7 vendors |
| Workflows N8N JSON | `infra/n8n-workflows/` | 35 WFs Turno 17 |

### 2.2 O que FALTA GERAR (delta)

| Item | Status | Ação no plano |
|---|---|---|
| HTML premium com Poppins + glass mode + Fibonacci | Não existe | Criar `index.html` + `styles.css` |
| 13 seções com texto final (não placeholder) | Não existe | Compilar a partir das fontes validadas |
| Ativos SVG inline (logo, ícones KPI, diagramas) | Não existe | Embutir em `assets/` |
| Puppeteer render script + Dockerfile | Não existe | Criar `render.mjs` + `package.json` |
| PDF A4 print-ready 8K-equivalente | Não existe | Output `Relatorio-Premium-2Semanas-Felipe-Djalma-2026-07-06.pdf` |

---

## 3. Mudanças propostas (passo-a-passo numerado, com arquivos específicos)

### 3.1 Estrutura de diretórios

Todos em `/Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06/`:

```
relatorio-2-semanas-felipe-djalma-2026-07-06/
├── index.html                      # Single-page HTML premium (13 sections, 28-32 páginas)
├── styles/
│   ├── main.css                    # Poppins + Fibonacci + glass mode + full white
│   ├── print.css                   # @page A4 + page-break controls
│   └── tokens.css                  # CSS custom properties (cores, spacing, type scale)
├── js/
│   ├── counters.js                 # Animated counters KPIs (IntersectionObserver)
│   └── charts.js                   # SVG charts inline (timeline + squad progress)
├── assets/
│   ├── fonts/
│   │   ├── Poppins-Regular.ttf
│   │   ├── Poppins-Medium.ttf
│   │   ├── Poppins-SemiBold.ttf
│   │   └── Poppins-Bold.ttf
│   └── svg/
│       ├── logo-cartorio.svg       # Brasão minimalista ou wordmark
│       ├── arquitetura-swarm.svg   # Diagrama 27 serviços (estilo glass)
│       └── kpi-icons.svg           # Sprite SVG
├── render.mjs                      # Puppeteer script (gerar PDF)
├── package.json                    # puppeteer ^23.0.0 + minimal deps
├── .nvmrc                          # node 20
└── README.md                       # Como regenerar
```

**Arquivo final entregue:** `Relatorio-Premium-2Semanas-Felipe-Djalma-2026-07-06.pdf` (mesmo diretório).

### 3.2 Passo-a-passo numerado

**PASSO 1 — Bootstrap do diretório e dependências**

```bash
mkdir -p /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06/{styles,js,assets/fonts,assets/svg}
cd /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06
npm init -y
npm install --save puppeteer@^23.0.0
echo "20" > .nvmrc
```

**PASSO 2 — Download self-host da Poppins** (MIT, Google Fonts)

Baixar de https://fonts.google.com/specimen/Poppins (weights 400/500/600/700) e salvar em `assets/fonts/`. Justificativa self-host: PDF precisa das fonts embutidas; CDN quebra em impressão offline.

**PASSO 3 — `tokens.css`** (sistema de design Fibonacci)

```css
:root{
  /* Cores — full white glass mode */
  --c-bg: #ffffff;
  --c-bg-soft: #fafafa;
  --c-fg: #0a0a0a;
  --c-fg-muted: #6b7280;
  --c-fg-subtle: #9ca3af;
  --c-line: rgba(10,10,10,0.06);
  --c-accent: #0f172a;          /* Navy Cartório */
  --c-accent-2: #1e3a8a;        /* Hover */
  --c-success: #047857;
  --c-warn: #b45309;
  --c-danger: #b91c1c;
  --c-glass: rgba(255,255,255,0.72);
  --c-glass-border: rgba(15,23,42,0.08);

  /* Type scale (rem) */
  --fs-xs: 0.75rem;   /* 12px */
  --fs-sm: 0.875rem;  /* 14px */
  --fs-base: 1rem;    /* 16px */
  --fs-md: 1.125rem;  /* 18px */
  --fs-lg: 1.5rem;    /* 24px */
  --fs-xl: 2rem;      /* 32px */
  --fs-2xl: 2.625rem; /* 42px */
  --fs-3xl: 3.5rem;   /* 56px */
  --fs-display: 4.625rem; /* 74px (capa) */

  /* Fibonacci spacing (px → rem base 16) */
  --s-1: 0.5rem;   /* 8 */
  --s-2: 0.8125rem; /* 13 */
  --s-3: 1.3125rem; /* 21 */
  --s-4: 2.125rem;  /* 34 */
  --s-5: 3.4375rem; /* 55 */
  --s-6: 5.5625rem; /* 89 */
  --s-7: 9rem;      /* 144 */

  /* Linear tokens */
  --radius-sm: 6px;
  --radius-md: 13px;
  --radius-lg: 21px;
  --shadow-glass: 0 1px 0 rgba(255,255,255,0.6) inset, 0 8px 32px rgba(15,23,42,0.04);
  --shadow-card: 0 1px 2px rgba(15,23,42,0.04), 0 8px 24px rgba(15,23,42,0.06);
}
```

**PASSO 4 — `main.css`** (Poppins + glass mode + full white)

Pontos críticos:

- `@font-face` para cada peso Poppins apontando para `assets/fonts/`.
- `html, body { background: var(--c-bg); color: var(--c-fg); font-family: 'Poppins', system-ui, sans-serif; font-weight: 400; line-height: 1.6; -webkit-font-smoothing: antialiased; }`
- Reset, container `max-width: 89rem; margin: 0 auto; padding: 0 var(--s-3);`
- Glass mode aplicado em `.card { background: var(--c-glass); backdrop-filter: blur(20px) saturate(180%); border: 1px solid var(--c-glass-border); border-radius: var(--radius-md); box-shadow: var(--shadow-glass); padding: var(--s-3); }`
- Hierarquia tipográfica: `h1` 74px / `h2` 42px / `h3` 24px / `body` 16px (line-height 1.7 para corpo).
- Componentes: `.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: var(--s-2); }`, `.timeline-rail`, `.badge`, `.status-pill` (cores por estado), `.table` (linear, borda inferior apenas), `.chart-svg` (SVG responsivo).
- Sem gradientes coloridos. Linear minimalista: somente navy + escalas de cinza. Glass mode através de opacidade + blur.

**PASSO 5 — `print.css`** (A4 + page-breaks)

```css
@page { size: A4 portrait; margin: 0; }
@page :first { margin: 0; }
@media print {
  html, body { background: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .page { width: 210mm; height: 297mm; page-break-after: always; padding: var(--s-3); box-sizing: border-box; }
  .page:last-child { page-break-after: auto; }
  .no-print { display: none !important; }
  .glass, .card { backdrop-filter: none !important; background: #ffffff !important; box-shadow: none !important; border: 1px solid var(--c-line) !important; }
  h2, h3 { page-break-after: avoid; }
  table, figure { page-break-inside: avoid; }
}
```

**PASSO 6 — `index.html`** — 13 seções em 28–32 páginas

Estrutura de cada `<section class="page">`:

| # | Section | Páginas | Conteúdo concreto (não placeholder) |
|---|---|---|---|
| 1 | Capa premium | 1 | Título: "2º Serviço Notarial de Uberlândia"; subtítulo "Relatório de Progresso — 23 jun → 06 jul 2026"; wordmark Cartório; "Para: Felipe Pizarro & Djalma Pizarro"; data 06/07/2026; selo glass "Production Ready ~ 87%" |
| 2 | Sumário executivo | 1 | 5 bullet: (a) Bot Telegram LIVE + WhatsApp conectado; (b) LGPD D26-D32 em produção; (c) 1.793 testes / coverage 87%; (d) 27 serviços Docker Swarm UP; (e) 11 provedores LLM fallback |
| 3 | Visão geral do projeto | 2 | Escopo (bot WhatsApp/Telegram/Web, compliance LGPD, audit chain, HITL); stack (FastAPI + SQLAlchemy 2.0 + Supabase + Redis 8 + n8n + Evolution API + Chatwoot + OpenClaw + LiteLLM); números-chave em KPI grid glass (1793 testes / 87% coverage / 27 serviços / 1006 audit entries / 11 provedores LLM / 0 erros mypy+ruff) |
| 4 | Linha do tempo 23/06 → 06/07 | 4 | Rail vertical com 14 marcos: 23/06 (handover inicial), 25/06 (Squad A 25/25 done + Sprint 3 docs), 26/06 (Turno 4 coverage 84→88%), 29/06 (LGPD D26-D32 LIVE), 30/06 (WhatsApp LIVE 94.54% bateria), 01/07 (N8N full restore T46), 02/07 (Auditoria 27 serviços + 26/27 healthchecks + Chatwoot bootstrap), 03/07 (Telegram anti-spam + 100 tasks loop), 06/07 (hoje: ciclo atual). Cada marco: data + título + 1 frase de impacto + evidência (commit hash ou teste count) |
| 5 | Squads completion | 2 | Tabela glass: Squad A (25/25 done — audit hardening) · B (Telegram LIVE) · C (docs ops) · D (LGPD policy 100%) · E (loop engineer 95%) · J (CI/CD + Sentry + OTel 100%) · BRAIN (8/8) · F (Playwright E2E) · G (fallback validado 50%) |
| 6 | LGPD compliance | 2 | Cards D26-D32 (7 endpoints LIVE): D26 dashboard KPIs / D27 consent granular / D28 anonimização / D29 portabilidade / D30 correção / D31 revogação / D32 transparência. Tabela:retenção 5 anos (ADR-019), audit chain SHA256+HMAC (968/1006 entries OK = 96.2%), soft delete 90d, DPA templates (7 vendors) |
| 7 | Arquitetura & infraestrutura | 3 | Diagrama SVG 27 serviços Swarm (reusar visual do `docs/SERVICE_INVENTORY.md`); tabelas por categoria (AI/LLM, WhatsApp Gateway, CRM/Chat, RAG, Observability, DB/Cache); stats VPS (4 CPU / 15Gi RAM / 193GB disco 32% usado) |
| 8 | Métricas & KPIs | 2 | Grid 12 KPIs: 1793 testes / 87% coverage / 0 mypy / 0 ruff / 27 serviços UP / 26/27 healthchecks / 968 audit OK / 11 provedores LLM / 7 endpoints LGPD / 100 paths OpenAPI / 24 tags / 5s latência média |
| 9 | Pendências / SUI / bloqueios | 2 | Tabela actionable: SUI1 (DNS Cloudflare token expirado) · SUI2 (WhatsApp QR scan Gustavo) · TODO-002 (typo crwal4ai) · TODO-005 (DBs dedicados) · 4 chaves upstream rejeitadas · vps_whoami loop · fallback chain 50% validado |
| 10 | Roadmap próximas sprints | 2 | Sprint 4 (07-20/07): WhatsApp produção + fallback chain 100% validado + DNS Cloudflare resolvido + 90% coverage gate. Sprint 5 (21/07-03/08): RAG com crawl4ai + Langfuse tracing + Argilla feedback + Chatwoot full integration. Sprint 6 (04-17/08): DPO dashboard v2 + multi-cartório support + piloto com 20 clientes |
| 11 | % Conclusão geral & plano para finalizar | 1 | Donut chart SVG (60% completo) + breakdown por squad + ação imediata: Gustavo gerar token Cloudflare + escanear QR WhatsApp (destrava 30% → 90%) |
| 12 | Custos estimados | 1 | VPS R$ 0 (já pago) / 11 provedores free R$ 0 / LiteLLM proxy R$ 0 / N8N R$ 0 / API IA escolha pós-go-live R$ 30-300/mês. Comparação: atendente extra ≈ R$ 2.500/mês. **TOTAL R$ 30-300/mês** |
| 13 | Anexo técnico + lições aprendidas | 3 | Top 10 lessons aprendidas (extraídas de `.harness/memory/MEMORY.md`): Lesson 51 (N8N env vs vars), Lesson 132 (test isolation cache Redis), Lesson 138 (DPA DeepSeek), Lesson 139/140 (loop engineer), Lesson 141 (multi-loop), Lesson 142 (SUI gate explícito), Lesson 143 (Cloudflare token), Lesson 145 (Telegram anti-spam), Lesson 146 (background_tasks DB session), Lesson 147 (LiteLLM STORE_MODEL_IN_DB). Commits relevantes: ~50 do período (último do git log `--since=2026-06-23`) |

**PASSO 7 — `js/counters.js`** (animar KPIs)

```js
const counters = document.querySelectorAll('[data-counter]');
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    const el = e.target;
    const target = parseFloat(el.dataset.counter);
    const dur = 1200;
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / dur);
      const v = Math.floor(target * (0.5 - Math.cos(Math.PI * t) / 2));
      el.textContent = v.toLocaleString('pt-BR');
      if (t < 1) requestAnimationFrame(step);
      else el.textContent = target.toLocaleString('pt-BR');
    };
    requestAnimationFrame(step);
    io.unobserve(el);
  });
}, { threshold: 0.4 });
counters.forEach((c) => io.observe(c));
```

**PASSO 8 — `render.mjs`** (Puppeteer headless → PDF)

```js
import puppeteer from 'puppeteer';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.join(__dirname, 'index.html');
const outPdf   = path.join(__dirname, 'Relatorio-Premium-2Semanas-Felipe-Djalma-2026-07-06.pdf');

const browser = await puppeteer.launch({
  headless: 'new',
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--font-render-hinting=none'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });
await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0', timeout: 60_000 });
await page.evaluate(() => document.fonts.ready);
await page.emulateMediaType('print');
await new Promise(r => setTimeout(r, 800));

await page.pdf({
  path: outPdf,
  format: 'A4',
  printBackground: true,
  preferCSSPageSize: true,
  displayHeaderFooter: false,
  margin: { top: 0, right: 0, bottom: 0, left: 0 },
});

await browser.close();
console.log('OK', outPdf);
```

**PASSO 9 — Geração final**

```bash
cd /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06
node render.mjs
```

Output esperado: `Relatorio-Premium-2Semanas-Felipe-Djalma-2026-07-06.pdf` (4-6 MB, 28-32 páginas).

**PASSO 10 — Validação automática (QA)**

```bash
ls -lh Relatorio-Premium-2Semanas-Felipe-Djalma-2026-07-06.pdf
mdls -name kMDItemNumberOfPages Relatorio-Premium-2Semanas-Felipe-Djalma-2026-07-06.pdf
open Relatorio-Premium-2Semanas-Felipe-Djalma-2026-07-06.pdf
```

Critérios PASS: 28 ≤ páginas ≤ 32 · 4 MB ≤ tamanho ≤ 6 MB · Capa exibe "Felipe Pizarro & Djalma Pizarro" · Poppins renderizada · Sem overflow · Tabelas íntegras · Diagramas SVG renderizados.

---

## 4. Decisões & Assumptions

| # | Decisão | Justificativa |
|---|---|---|
| D1 | HTML+CSS autoral (não PptxGenJS, não pandoc) | Poppins + Fibonacci + glass mode exigem controle pixel-perfect |
| D2 | Puppeteer headless (não WeasyPrint) | Chromium real → CSS3 moderno (`backdrop-filter`, SVG inline, custom properties) |
| D3 | Poppins self-host (não CDN) | PDF precisa de fonts embutidas; CDN quebra em visualização offline |
| D4 | A4 portrait (não Letter, não A3) | Padrão BR; A3 causaria PDF > 10 MB |
| D5 | `deviceScaleFactor: 2` + viewport 1920×1080 | Render retina; PDF 8K-equivalente (~150-200 DPI) |
| D6 | Encoding UTF-8 com `<meta charset="utf-8">` | Suporte completo a acentos pt-BR |
| D7 | `printBackground: true` + `-webkit-print-color-adjust: exact` | Glass mode + cores das badges aparecem no PDF |
| D8 | Números validados a partir de `.brain/memory/*.md`, `docs/SERVICE_INVENTORY.md`, `GOALS.md` | Toda estatística rastreável às fontes |
| D9 | Linguagem: português brasileiro formal mas acessível | Público Felipe/Djalma = donos do cartório, não técnicos |
| D10 | Sem emojis no PDF final | Apenas pictogramas SVG/ícones lineares |
| D11 | 13 seções, 28-32 páginas | Densidade ideal para relatório executivo + técnico |
| D12 | Estrutura single-page web app para PDF | Reusabilidade: HTML pode virar landing page institucional |
| D13 | Tempo de render alvo: < 30s | Puppeteer headless em macOS M-series rápido |
| D14 | Não commitar `node_modules/` ao git | `package.json` + `package-lock.json` versionados; `node_modules` gitignored |
| D15 | Sem CDN para assets | Puppeteer file:// + sem network = zero dependência externa |

---

## 5. Verificação — como o usuário valida que ficou bom

### 5.1 Checklist de QA visual

| # | Item | Como verificar | PASS criteria |
|---|---|---|---|
| 1 | PDF abre sem erro | `open Relatorio-...pdf` | Preview abre |
| 2 | Capa exibe destinatários | Página 1 | "Para: Felipe Pizarro & Djalma Pizarro" visível |
| 3 | Período correto | Página 1 | "23 jun → 06 jul 2026" |
| 4 | Poppins renderizada | `pdffonts` ou inspecionar visual | Font moderna (não serif fallback) |
| 5 | Glass mode aplicado | Cards KPI (página 3, 8) | Borda sutil + fundo branco semi-transparente |
| 6 | Fibonacci spacing | Inspecionar margens | Razões 8/13/21/34/55/89 |
| 7 | Full white background | Todas as páginas | Fundo branco puro |
| 8 | Linear minimalista | Inspecionar linhas/bordas | Apenas navy + escalas cinza |
| 9 | 13 seções presentes | Sumário vs páginas | Cada item tem página correspondente |
| 10 | Timeline 14 marcos | Seção 4 | Marcos visíveis |
| 11 | Diagramas SVG | Seção 7 | 27 serviços visíveis |
| 12 | Sem overflow | Todas páginas | Nenhum texto cortado |
| 13 | Números validados | Seções 3, 6, 8 | 1793 testes · 87% coverage · 27 serviços · 968 audit OK |
| 14 | Custos | Seção 12 | R$ 30-300/mês visível |
| 15 | Pendências SUI | Seção 9 | 7 itens |
| 16 | Anexo técnico | Seção 13 | 10 lessons + commits |
| 17 | Tamanho | `ls -lh` | 4-6 MB |
| 18 | Páginas | Preview / `mdls` | 28-32 |
| 19 | Encoding pt-BR | Procurar "ção", "ão" | Sem caracteres quebrados |
| 20 | Imprimibilidade | Re-Print to PDF | Não regride |

### 5.2 Critérios de sucesso

- Todos os 20 itens PASS.
- Gustavo confirma visualmente em até 5 minutos.
- PDF é entregável direto a Felipe/Djalma sem edição adicional.

### 5.3 Plano de contingência

- **Se Puppeteer falhar em ambiente sem Chromium**: usar `puppeteer-core` + `chrome-headless-shell` instalado via Homebrew; ou fallback para Playwright (`npx playwright install chromium`).
- **Se fonts Poppins não renderizarem**: verificar `await page.evaluate(() => document.fonts.ready)` antes do PDF.
- **Se páginas excederem 32**: comprimir seções 7 e 13 (mais densas).
- **Se SVG inline quebrar**: mover para `<img src="assets/svg/...">`.

---

## 6. Comando resumido (one-shot)

```bash
# 1. Setup
mkdir -p /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06/{styles,js,assets/fonts,assets/svg}
cd /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/relatorio-2-semanas-felipe-djalma-2026-07-06
npm init -y && npm install puppeteer@^23.0.0 && echo "20" > .nvmrc

# 2. Download fonts (manual: Poppins 400/500/600/700 OFL em fonts.google.com)
# Colocar em assets/fonts/

# 3. Criar arquivos do plano (steps 3-7: tokens.css, main.css, print.css, index.html, counters.js)

# 4. Render
node render.mjs

# 5. Validar
open Relatorio-Premium-2Semanas-Felipe-Djalma-2026-07-06.pdf
```

---

## 7. Anexo — Fontes de dados por seção (rastreabilidade)

| Seção PDF | Fonte primária | Fonte secundária |
|---|---|---|
| Capa + Sumário | `GOALS.md` (meta única) | `.brain/memory/2026-07-03-loop-goals.md` |
| Visão geral | `CLAUDE.md` (descrição stack) | `docs/ARCHITECTURE.md` |
| Timeline 14 marcos | `.brain/memory/2026-06-25.md` + `2026-06-29.md` + `2026-06-30.md` + `2026-07-01-*.md` + `2026-07-02.md` + `2026-07-03.md` | `docs/sessions/2026-06-30-session-summary-turno-40-42.md` |
| Squads | `SQUAD_INDEX.md` + `.harness/TASKS.md` (linhas 504-510) | `GOALS.md` (SQUAD STATUS) |
| LGPD D26-D32 | `docs/reviews/lgpd-review-d26-d32-2026-06-30.md` + `.brain/memory/2026-06-29.md` (12:45) | `docs/lgpd/policy/INDEX.md` + ADR-019 |
| Arquitetura 27 serviços | `docs/SERVICE_INVENTORY.md` (2026-07-02) | `docs/SERVICE_INVENTORY.md` Wave 7 |
| Métricas/KPIs | `.brain/memory/2026-07-03.md` (gates) + `2026-07-03-context.md` | `docs/SPRINT_REVIEW_2026-07-02.md` |
| Pendências SUI | `GOALS.md` (SUI table) + `.harness/SUI_CHECKLIST.md` + `.brain/memory/2026-07-02.md` | `.brain/memory/2026-07-02-auditoria-pos-deploy.md` |
| Roadmap | `docs/ROADMAP.md` (Fase 4) + `docs/ROADMAP_100TASK.md` | `GOALS.md` (NEXT CYCLE TARGETS) |
| Conclusão % | `GOALS.md` (60% Cartório) + `.brain/memory/2026-07-03-loop-goals.md` | `paperclip-board/board.md` |
| Custos | `docs/CLIENTES/Felipe_Djalma_STATUS_2026-06-30.md` (CUSTO MENSAL) | `GOALS.md` (SUI table) |
| Anexo técnico | `.harness/memory/MEMORY.md` (Lessons 51, 132, 138, 139-147) + `git log --since=2026-06-23` | `.brain/memory/*.md` |

---

**Modified by Gustavo Almeida** — Plano de implementação executável, sem mais perguntas.

## Próximos passos (handoff)

1. **Gustavo**: revisar este plano, validar 13 seções e ajustar prioridades se necessário.
2. **Executor (agent ou Gustavo)**: seguir passos 1-10 na ordem.
3. **QA**: validar contra checklist seção 5.
4. **Entrega**: enviar PDF para Felipe/Djalma por canal preferido (email/Telegram/WhatsApp business).