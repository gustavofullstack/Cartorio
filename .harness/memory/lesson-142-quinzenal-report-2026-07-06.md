---
name: lesson-142-quinzenal-report-2026-07-06
description: Geração de relatório quinzenal multi-formato (PDF navegável + PPTX) para Felipe/Djalma Pizarro do Cartório 2º Notas Uberlândia, em 2026-07-06
type: project
---

# Lesson 142 — Relatório Quinzenal Multi-formato (PDF + PPTX)

**Data**: 2026-07-06
**Contexto**: Gustavo pediu PDF cobrindo 2 semanas inteiras do projeto Agent AI Cartório WhatsApp, com animações, tasks, planos, custos, etc., para apresentar a Felipe e Djalma Pizarro. Estilo: white clean, glass mode, linear, Poppins, profissional.

## Lições aprendidas

### 1. Counter animation em PDF (counters.js não roda no print)
- Problema: KPIs renderizados com `data-target` mostravam "0" no PDF porque Playwright/Chromium só executa JS de animação após `IntersectionObserver` disparar, e o `page.pdf()` é instantâneo.
- Solução: chamar `page.evaluate()` ANTES do `page.pdf()` para forçar todos os `.kpi-value[data-target]` a terem seu `textContent = target.toLocaleString('pt-BR')` direto (sem animação).
- Aplicabilidade: qualquer relatório gerado via Playwright que tenha KPIs animados.

### 2. Plano A-G vs nomes técnicos (LGPD-safe naming)
- Decisão do Gustavo: nomear provedores LLM como "Plano A/B/C..." no corpo do PDF, e manter equivalência técnica SÓ no apêndice.
- Implementação: lista de redaction em `extract.py` que substitui opencode_free_1/2/3, nemotron, mimo, deepseek, mistral, openrouter, gemini, groq, north-mini-code, poolside, gemma → Plano X correspondente.
- Verificação: regex `opencode|mistral|nemotron` no `body_text` (não-apêndice) deve retornar 0 hits.

### 3. Arquitetura do relatório = 3 camadas
- **JSON intermediário** (`build/data/*.json`): 8 arquivos extraídos do repo via grep/read. Permite reprodutibilidade do build.
- **HTML renderizado** (`RELATORIO_*.html`): hand-written Jinja2-style templates com CSS theme.css + counters.js. Anima no browser, é imprimível.
- **PDF via Playwright headless** (`RELATORIO_*.pdf`): 45 páginas, A4 portrait, printBackground=True, evaluate() para pré-resolver valores.
- **PPTX via python-pptx** (`RELATORIO_*.pptx`): 11 slides, 16:9, shapes nativos (rect + text + table) replicando design system.

### 4. Numbers: real vs heuristic, sempre explícito
- Real: 852 commits (git log), 1787 testes (PROGRESS.md ciclo #18), 27 serviços (SERVICE_INVENTORY), 100 endpoints, 17 modelos LiteLLM.
- Heurística: tokens consumidos (assume média 2400 in / 760 out por chamada), custo VPS (estimativa pública Hostinger $25/mês), tempo humano (soma durações de SESSION_SUMMARY_*.md).
- Marcar explicitamente com `source: real|heuristic` em cada linha + fórmula visível na seção.

### 5. Glass mode semântica
- White clean: `--bg: #FFFFFF`
- Glass cards: `background: rgba(255,255,255,0.7); backdrop-filter: blur(12px); border: 1px solid rgba(15,23,42,0.06)` — não usar sombras exageradas, manter linear.
- Borda colorida pequena (32px × 1px) no topo do KPI para sinalizar tipo, sem comprometer "clean".
- Border-radius: 4px max (não usar pills ou cantos super arredondados).

### 6. Tempo de execução real
- Estimativa inicial: 30-45 min. Real: ~12 min de execução pura (extract 5s + render 1s + PDF 4s + PPTX 1s + verificações 2min).
- Playwright já estava instalado (não baixou chromium).
- python-pptx já estava disponível.

### 7. Poppins self-hosted = falhou
- Sem rede externa no ambiente de execução. Fontes Poppins do Google Fonts / GitHub raw não baixaram (CDN bloqueado).
- Fallback elegante: stack `Poppins, Inter, Helvetica Neue, Arial, system-ui, -apple-system, sans-serif` no CSS. macOS usa Helvetica Neue (visualmente próximo do Poppins). LGPD-safe (zero requisição externa).

### 8. Cuidado com vazamentos em "evidence" strings
- Custos.json tinha `evidence: "Wave 8: opencode-free-2 ERR NoneType..."` que aparecia em rodapés de tabela. Reescrito para usar Plano X.
- Mesmo SERVICE_INVENTORY.md tem referências técnicas nos campos `notes` que vazaram (ex: `cartorio_openclaw-gateway notes: "modelo padrão opencode_free_1/nemotron"`). Reescrito para "Plano A responde a 95%".

## Outputs entregues

- `/Users/gustavoalmeida/projetos/Cartorio/docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pdf` (45 páginas, 656 KB)
- `/Users/gustavoalmeida/projetos/Cartorio/docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.pptx` (11 slides, 50 KB)
- `/Users/gustavoalmeida/projetos/Cartorio/docs/reports/RELATORIO_QUINZENAL_CARTORIO_2026-06-22_2026-07-06.html` (116 KB, anima no browser)
- `/Users/gustavoalmeida/projetos/Cartorio/docs/reports/build/{extract,render,build_pdf,build_pptx}.py` (build reproduzível)
- `/Users/gustavoalmeida/projetos/Cartorio/docs/reports/build/data/*.json` (8 fontes estruturadas)
- `/Users/gustavoalmeida/projetos/Cartorio/docs/reports/assets/{css,js,fonts}/` (design system reutilizável)

## Métricas finais
- 28 seções no sumário
- 18 KPIs animados
- 27 serviços Swarm inventariados
- 175 testes LGPD documentados
- 7 planos LLM (Plano A-G) com fallback chain
- 14 dias detalhados dia-a-dia
- 4 pendências humanas bloqueadoras
- 84.2% conclusão geral ponderada

## Modified by
Gustavo Almeida (via Plan Mode + execução automatizada)