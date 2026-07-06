# Plano: PDF Executivo — Felipe & Djalma (22/06 → 06/07/2026)

> **Status**: Pronto para aprovação. Aguardando GO do Gustavo para executar.
> **Destinatários**: Felipe Pizarro e Djalma Pizarro (sócios-proprietários do 2º Serviço Notarial de Uberlândia).
> **Idioma**: Português brasileiro. **Tema**: white/clean minimalista, glass mode, linear, Poppins, Fibonacci spacing.

---

## 1. Resumo

Gerar um PDF executivo **A4 portrait, 28-32 páginas** (white background, ultra qualidade visual) reportando as **duas últimas semanas completas** do projeto chatbot-agent (22/06/2026 → 06/07/2026), endereçado a Felipe e Djalma. O PDF conterá: capa glass, sumário executivo com 5 KPIs gigantes, carta de abertura do Gustavo, linha do tempo de 14 dias, épicos construídos, métricas reais, arquitetura, infraestrutura & custos, bugs resolvidos + lessons, squads, pendências, plano de finalização, e anexos. **Zero números inventados** — todos extraídos de `evidence.json` gerado a partir de arquivos git-tracked (PROGRESS.md, GOALS.md, SQUAD_INDEX.md, MEMORY.md, STATUS.md, HANDOVER.md, lessons 109-140).

---

## 2. Análise do Estado Atual (evidence real já coletada)

| Fonte | Achado |
|---|---|
| `git log --since=2026-06-22 --until=2026-07-06` | **852 commits**, 502.742 inserções, 39.545 deleções, em **10 dias com commits** |
| `PROGRESS.md` cycles 1-18 | 5 batches do plano v22 (Blocos A-E + cobertura) validados: 1727 → 1759 → 1785 → 1793 → **1930+** testes passando |
| `SQUAD_INDEX.md` | 8 squads auditados: A 25/25, B 0/25, C 5/25, D 20/25, E 8/8, H 8/8, J 8/10, BRAIN 5/8 = **80/136 ≈ 59%** |
| `GOALS.md` | Goals A-G: A 100%, B 100%, C 95%, D 30%, E 95%, F 80%, G 50% → **média ponderada ≈ 85%** |
| `STATUS.md` + `HANDOVER.md` | Bot Telegram 100% funcional via LiteLLM Proxy, 8 testes E2E validados (`sent=True`), latência 9-15s, fallback chain validado 3x |
| `MEMORY.md` | **135+ lessons** salvas (Lesson 109-140+); principais: 109, 110, 111, 113, 120, 121, 127, 128, 132, 137, 138, 139, 140 |
| Loop cycles (cron 4h + 30min launchd) | 5 sub-agents do Harness (analyze/test/fix/document/memory) rodando autonomamente |
| Incidentes críticos (02/07) | Redis crash 19:20 (recovery 4min), LiteLLM 422 19:24 (fallback opencode_free_1 em 2.04s), Traefik restart 19:39 (auto-recuperou 19s) |
| Stack LLM | 7 provedores via LiteLLM Proxy (multi-provedor com redundância, apresentado como "stack multi-provedor") |
| Quality gates | ruff 0 errors, mypy 0 errors, pytest 1930+ pass, coverage 87% (gate 90% — WARNING honesto no PDF) |
| LGPD | 100% (DPA DeepSeek + 175 tests + ripd + retenção 5y + soft delete) |

---

## 3. Decisões de Design (propostas — aguardando GO)

| Aspecto | Decisão | Justificativa |
|---|---|---|
| Paleta | Branco puro `#FFFFFF` + slate-900 `#0F172A` + blue-600 `#2563EB` + neutros | Tema "Modern Minimalist" do `theme-factory` + custom glass |
| Fonte | **Poppins** Regular/Medium/SemiBold/Bold (TTF embedded) | Requisito do usuário |
| Fallback fonte | Inter → DejaVu Sans | Contingência tripla |
| Spacing | Fibonacci 8/13/21/34/55/89 px | Requisito do usuário |
| Glass mode | 2 camadas: fill translúcido (alpha 0.55) + borda 0.5pt slate-300 + sombra simulada | reportlab 4.x suporta alpha |
| Diagramas | matplotlib @ 192 DPI com Poppins | 8 gráficos |
| Ícones | 12 técnicos + 4 status = 16 SVG/PNG | Render via cairosvg → PNG @2x |
| Página | A4 portrait, margens 0.65-0.75in | Padrão executivo |
| Animações | Descritas como "motion design" (estático, mas com fases numeradas em diagramas) | PDF não suporta animações nativas |
| Glossário "free" | Reescrever como "stack multi-provedor com redundância" | Requisito do usuário |

---

## 4. Estrutura do PDF (28-32 páginas)

| # | Seção | Páginas | Conteúdo principal |
|---|---|---|---|
| 1 | **Capa** | 1 | Glass card centrado: título + subtítulo + destinatários + data + logo |
| 2 | **Sumário Executivo** | 1 | TL;DR 4-5 linhas + 5 KPIs gigantes (1930+ testes, 852 commits, 502.742 linhas, 59% squads, 85% global) |
| 3 | **Carta de Abertura** | 1 | Texto humano do Gustavo aos sócios |
| 4 | **Linha do Tempo 14 dias** | 2 | 22/06 → 06/07/2026 com marcos macro agrupados por semana (W1 + W2) |
| 5 | **O Que Foi Construído** | 4 | Por épico: Bot Telegram, Stack Multi-Provedor, LGPD 100%, Audit Chain, Squads, Loop Engineer, Observabilidade |
| 6 | **Métricas & Números Reais** | 2 | Tabela consolidada (pytest, cobertura, latência por provider, INSERTs/DELETEs) + gráfico squads |
| 7 | **Arquitetura Atual** | 1-2 | Diagrama C4 estático + fluxo LiteLLM fallback |
| 8 | **Infraestrutura & Custos** | 1-2 | VPS, apps, serviços, consumo de tokens (proxy estimado), comparação R$/mês vs atendente humano |
| 9 | **Bugs Resolvidos & Lições** | 2 | Tabela de 16 lessons principais + 3 incidentes críticos (Redis/LiteLLM/Traefik) |
| 10 | **Squads & Tasks** | 1 | 8 squads em grid 2×4 com mini progress bars |
| 11 | **Pendências & Bloqueios** | 1 | 5 SUI do Gustavo + % restante destacado |
| 12 | **Plano para Finalizar** | 1 | Roadmap P0/P1/P2 (sequência de dependência, sem datas) |
| 13 | **Anexos** | 4-5 | Glossário 30+ termos cartorários, MCPs, evidência de testes, log de ciclos, CHANGELOG dos relatórios |

---

## 5. Arquivos a criar/modificar (workspace do usuário)

### 5.1 Pasta de build (intermediária) — `~/.trae/work/.../pdf-cartorio/`
```
pdf-cartorio/
├── build_pdf.py                     # entrypoint
├── themes/glass_white.py            # paleta + helpers cards
├── themes/icones.py                 # 16 ícones SVG/PNG
├── charts/                          # 8 scripts matplotlib
├── data/evidence.json               # dados estruturados (gerado por SA-4)
├── assets/fonts/                    # Poppins TTF (4 pesos)
├── assets/icons/                    # 16 SVGs + PNGs @2x
└── out/                             # PDF provisório
```

### 5.2 Entregáveis finais (workspace do usuário)
```
/Users/gustavoalmeida/projetos/Cartorio/
├── docs/CLIENTES/
│   ├── Felipe_Djalma_STATUS_2026-07-06.md       # espelho markdown
│   ├── Felipe_Djalma_STATUS_2026-07-06.pdf       # ← PDF final (entregável principal)
│   ├── CHANGELOG-RELATORIOS-CLIENTES.md          # log de versões
│   ├── BUILD-RELATORIO-EXEC.md                   # manual de regeneração
│   └── assets/{fonts,icons,charts}/              # assets do PDF
└── .brain/
    └── executive-report-felipe-djalma-2026-07-06.pdf  # cópia paralela
```

> **Não sobrescrever** o `Felipe_Djalma_STATUS_2026-06-30.md` (existente).

---

## 6. Bibliotecas Python

| Lib | Versão | Função |
|---|---|---|
| `reportlab` | `>=4.2.5,<5` | Compositor PDF |
| `pypdf` | `>=5.0.0,<6` | Validação final |
| `pdfplumber` | `>=0.11.4,<0.12` | Sanity check de texto extraído |
| `matplotlib` | `>=3.9.0,<4` | 8 gráficos @2x |
| `Pillow` | `>=10.4.0,<11` | Composição / compressão |
| `requests` | `>=2.32.3,<3` | Download Poppins TTF |
| `cairocairo` | `>=1.26.0,<2` | SVG → PNG (ícones) |
| `qpdf` CLI | system | Validação `--check` |

Comando: `cd /Users/gustavoalmeida/projetos/Cartorio/backend && uv sync --extra pdf` (após adicionar `[project.optional-dependencies] pdf = [...]` em `pyproject.toml`).

---

## 7. Estratégia de Subagents (YOLO mode, paralelização)

| ID | Nome | Escopo | Entrega |
|---|---|---|---|
| SA-1 | `font-fetcher` | Baixar Poppins TTF (4 pesos); converter WOFF→TTF; fallback Inter/DejaVu | `assets/fonts/*.ttf` |
| SA-2A | `charts-A` | Gráficos 1+2+8 (timeline, commits/dia, insertions/deletions) | `out/charts/{01,02,08}.png` |
| SA-2B | `charts-B` | Gráficos 3+4+6 (testes/cycle, latência/provider, goals) | `out/charts/{03,04,06}.png` |
| SA-2C | `charts-C` | Gráficos 5+7 (squads, tokens) | `out/charts/{05,07}.png` |
| SA-3 | `icons-render` | Gerar 16 SVGs + converter para PNG @2x | `assets/icons/{*.svg,_png/*.png}` |
| SA-4 | `evidence-collector` | Parsear repo → `data/evidence.json` (gateia SA-5) | `data/evidence.json` validado |
| SA-5 | `pdf-builder` | Compor PDF via `build_pdf()` | `out/executive-report-2026-07-06.pdf` |
| SA-6 | `pdf-validator` | Rodar `pdfinfo` / `pdftotext` / `qpdf --check` / preview | `validation-report.md` |
| SA-7 | `commit-cp` | Branch `feat/relatorio-felipe-djalma-2026-07-06` + commit (push GATED) | commit pronto |

**Regra cartorio-lgpd**: nenhum SA toca `backend/app/services/audit.py` ou `pii.py`. Mudanças apenas em `docs/CLIENTES/`, `.brain/executive-report-…`, e pasta intermediária.

---

## 8. Verificação (Quality Gates)

| Gate | Comando | Critério |
|---|---|---|
| Tamanho | `ls -lh docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf` | < 30 MB |
| Metadados | `pdfinfo` | A4 (595x842), Producer=ReportLab, language=pt-BR |
| Integridade | `qpdf --check` | exit 0, "No errors found" |
| Texto extraível | `pdftotext` (head) | Capa + sumário aparecem como texto |
| Programático | `pypdf.PdfReader` | 25 ≤ pages ≤ 40, language="pt-BR" |
| Visual | Preview / Adobe Acrobat | Glass cards legíveis, 8 gráficos com Poppins, sem cortes |

---

## 9. Plano de Contingência

| Falha | Solução |
|---|---|
| Download Poppins falhar | Tentar Inter (GitHub mirror) → DejaVu Sans (built-in) |
| cairosvg ausente | Render manual via `reportlab.graphics.shapes.Path` ou emoji Unicode |
| matplotlib não achar Poppins | Fallback `DejaVu Sans`; log warning |
| TTF corrompido | Pular para próximo fallback; build não bloqueia |
| PDF > 30MB | Comprimir PNG (Pillow `optimize=True`, q=85); reduzir DPI dos charts |
| Subagent inventar número | Bloquear SA-5 até diff manual contra `STATUS.md` + `GOALS.md` |

---

## 10. Conformidade AGENTS.md

| Regra | Aplicação |
|---|---|
| Conventional Commits + termina com `Modified by Gustavo Almeida` | Mensagem: `docs(clientes): relatorio executivo Felipe & Djalma (22/06-06/07/2026) — Modified by Gustavo Almeida` |
| Branch from `master` | `feat/relatorio-felipe-djalma-2026-07-06` |
| Cobertura ≥ 90% / ruff 0 / mypy 0 | PDF generator fica em `docs/CLIENTES/`, não impacta gate |
| Sem `.env` / chaves reais | PII explicitamente mascarado no PDF (ex: `chat_id=66***225505`) |
| Mudança em `audit`/`pii` exige cartorio-lgpd | Plano **NÃO** toca esses arquivos |
| Workflow obrigatório 8 fases | Plano segue: analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória |

---

## 11. Pontos que Precisam de GO do Gustavo

1. **Visual**: aprovar paleta glass-white + Fibonacci spacing.
2. **Carta de Abertura** (seção 3): aprovar texto humano.
3. **Coverage 87% vs gate 90%**: destacar como "WARNING honesto" no PDF (gate atual está em WARNING, não FAIL — explicar).
4. **Lista SUI**: confirmar os 5 itens de "Pendências & Bloqueios".
5. **Custos & comparação com atendente humano**: confirmar valores R$/mês.
6. **Publicação dupla** (`docs/CLIENTES/` + `.brain/`): manter as duas cópias (padrão do projeto).
7. **Tom da carta**: revisar tom editorial (respeito + transparência + convite à decisão).

---

## 12. Resumo em 5 linhas

PDF executivo A4 (28-32p) com tema glass-white minimalista, Poppins embedded, 8 gráficos matplotlib @2x, 12+ ícones SVG, 13 seções (capa → sumário → carta → timeline → épicos → métricas → arquitetura → custos → bugs/lessons → squads → pendências → plano → anexos). Dados 100% extraídos de `evidence.json` gerado a partir de arquivos git-tracked (PROGRESS, GOALS, SQUAD_INDEX, MEMORY). Geração paralelizada em 7 subagents (1 font + 3 charts + 1 icons + 1 evidence + 1 build + 1 validate + 1 commit), com contingência tripla de fontes (Poppins → Inter → DejaVu), gates de validação (pdfinfo/pdftotext/qpdf/pypdf, < 30MB), e conformidade total com AGENTS.md (branch `feat/relatorio-felipe-djalma-2026-07-06`, push GATED, sem tocar `audit.py`/`pii.py`).

---

**Pronto para aprovação.** Após GO do Gustavo, execução em modo YOLO com os 7 subagents listados, ~20-40 minutos de build total.
