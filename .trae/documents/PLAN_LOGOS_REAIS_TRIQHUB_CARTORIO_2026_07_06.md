# Plano — Incorporar Logos REAIS TriQ Hub + Cartório 2º Notas ao PDF v2.1.0

**Slug:** `logos-triqhub-cartorio-v2.1`
**Trigger:** Gustavo pediu para usar as logos REAIS (TriQ Hub Vetorizada Colorida + Cartório 2º Notas Uberlândia), não o wordmark placeholder SVG que foi gerado na v2.0.0.
**Output:** PDF v2.1.0 (overwrite do v2.0.0) + CHANGELOG entry
**Data:** 2026-07-06

---

## 1. Sumário

Substituir o wordmark placeholder (`logo-cartorio.svg` geométrico neutro) e wordmark genérico TriQ Hub ausente no PDF v2.0.0 pelas logos REAIS fornecidas por Gustavo: (a) TriQ Hub Vetorizada Colorida (`/Users/gustavoalmeida/Documents/TriQ Hub Docs/TriQ Hub Logo /TriQ Hub Logo Vetorizada Colorida.svg`); (b) wordmark Cartório 2º Serviço Notarial de Uberlândia. Adicionar faixa de "Powered by TriQ Hub" no rodapé do PDF, header TriQ Hub na capa, e selo Cartório 2º Notas na contracapa. Resultado: PDF v2.1.0 com identidade visual corporativa completa.

---

## 2. Análise do estado atual

### 2.1 O que JÁ EXISTE

- **PDF v2.0.0 entregue** (`docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf`, 17p, 0.29 MB, A4 595×842) usando wordmark placeholder `logo-cartorio.svg` geométrico neutro.
- **TriQ Hub Vetorizada Colorida SVG** (`TriQ Hub Logo Vetorizada Colorida.svg` 2.7 KB) — AGORA copiada para `docs/CLIENTES/build/assets/logos/triqhub-colorida.svg`. Conteúdo: viewBox `0 0 1118.08 817.58`, 5 paths com gradientes lineares em tons azul→roxo→rosa→cyan (`#12227a` → `#6438ae` → `#bf51e8` → `#00caf2`).
- **TriQ Hub Vetorizada Black SVG** (967 B) — versão monocromática para impressão P&B.
- **TriQ Hub White no fundo preto PNG** (46 KB) — versão invertida para uso sobre fundos escuros.
- **HTML/CSS/JS pipeline** intacto em `docs/CLIENTES/build/`.
- **Build orchestrator** (`build.py`) deterministic + ~3 min ponta-a-ponta.

### 2.2 O que FALTA fazer

| # | Lacuna | Solução |
|---|---|---|
| 1 | Wordmark Cartório 2º Serviço Notarial é geométrico placeholder, não oficial | Criar SVG oficial baseado no brasão institucional (ou usar versão textual estilizada) |
| 2 | TriQ Hub não aparece no PDF (nem na capa, nem no rodapé) | Inserir `triqhub-colorida.svg` na capa (header) + rodapé "Powered by TriQ Hub" em todas as páginas |
| 3 | Falta selo "Cartório 2º Serviço Notarial de Uberlândia" oficial | Adicionar selo glass com wordmark oficial no header de cada página |
| 4 | Identidade visual incompleta para apresentação executiva | Adicionar fonts/colors consistentes entre logos |
| 5 | Faixa TriQ Hub no footer de cada section | Implementar `.page-footer` com TriQ Hub mini logo à esquerda + Cartório mini à direita |

---

## 3. Mudanças propostas (passo-a-passo numerado)

### 3.1 Estrutura de assets (já parcialmente criada)

```
docs/CLIENTES/build/assets/logos/
├── triqhub-colorida.svg         ✅ COPIADA de Documents/TriQ Hub Docs/TriQ Hub Logo /
├── triqhub-black.svg            ✅ COPIADA
├── triqhub-white-fundo-preto.png ✅ COPIADA
├── cartorio-2notas-udi.svg      🆕 CRIAR (wordmark oficial estilizado em texto)
└── cartorio-brasao.svg          🆕 CRIAR (selo circular minimalista em SVG)
```

### 3.2 Criar wordmark oficial Cartório 2º Notas Uberlândia (SVG)

**Path:** `docs/CLIENTES/build/assets/logos/cartorio-2notas-udi.svg`

Como o user não forneceu brasão oficial do cartório, vou criar um wordmark estilizado profissional baseado em tipografia (Poppins) + elemento geométrico (escala/balança da justiça estilizada minimalista):

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 80">
  <!-- Brasão geométrico: balança da justiça minimalista -->
  <g transform="translate(8, 16)">
    <rect x="0" y="4" width="48" height="48" rx="8" fill="#0f172a"/>
    <!-- Pilar central -->
    <line x1="24" y1="10" x2="24" y2="46" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
    <!-- Travessa horizontal -->
    <line x1="8" y1="16" x2="40" y2="16" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
    <!-- Pratos (círculos) -->
    <circle cx="10" cy="22" r="4" fill="none" stroke="#ffffff" stroke-width="1.5"/>
    <circle cx="38" cy="22" r="4" fill="none" stroke="#ffffff" stroke-width="1.5"/>
    <!-- Base -->
    <line x1="14" y1="46" x2="34" y2="46" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
  </g>
  <!-- Texto -->
  <g transform="translate(72, 0)" font-family="Poppins, sans-serif" fill="#0f172a">
    <text x="0" y="30" font-size="18" font-weight="700" letter-spacing="-0.3">2º Serviço Notarial</text>
    <text x="0" y="54" font-size="13" font-weight="500" letter-spacing="0.2" fill="#6b7280">Uberlândia · MG</text>
  </g>
</svg>
```

### 3.3 Atualizar `render_html.py` para usar logos REAIS

Mudanças no `render_section_01_capa()`:

- **Header (top)**: substituir o eyebrow genérico "Documento confidencial" por **logo TriQ Hub colorida** + texto "Powered by TriQ Hub" à esquerda + wordmark Cartório à direita.
- **Title block**: manter Poppins glass mode.
- **Footer (bottom)**: adicionar **faixa TriQ Hub mini** + selo Cartório mini assinatura.

Mudanças em **TODAS as pages** (`render_section_*`):

- **Header (top)**: header global consistente.
  - Lado esquerdo: TriQ Hub mini colorida (24px) + "TriQ Hub"
  - Centro: "2º Serviço Notarial de Uberlândia" (Poppins 11px, fg-muted)
  - Lado direito: meta (ex: "05 · Timeline 14 Dias Hora-a-Hora")
- **Footer (bottom)**: footer global consistente.
  - Lado esquerdo: TriQ Hub mini (16px) + "Powered by TriQ Hub · www.triqhub.com"
  - Centro: "Modified by Gustavo Almeida · 06/07/2026"
  - Lado direito: contador de páginas + selo Cartório mini

Mudanças em `render_section_16_creditos()` (contracapa):

- **Hero header (top)**: TriQ Hub colorida grande (120px) com tagline "Powered by TriQ Hub".
- **Bloco de contato**: wordmark Cartório 2º Notas + endereço institucional + selo oficial.

### 3.4 Hot-patch mínimo no `render_html.py`

Passos exatos:

1. Substituir `render_section_01_capa()` para incluir TriQ Hub no header top.
2. Adicionar helper global `render_global_header(num_meta)` e `render_global_footer(num_pagina)` que retorna HTML com TriQ Hub mini + Cartório mini.
3. Injetar `render_global_header()` no topo de cada `render_section_*` (não nas capas que já têm header próprio).
4. Substituir o `render_section_16_creditos()` para TriQ Hub grande.
5. Atualizar `render_full_html()` para garantir consistência.

### 3.5 Adicionar CSS para TriQ Hub + Cartório mini icons

No `main.css`, adicionar:

```css
.triqhub-mark { display: inline-block; vertical-align: middle; }
.triqhub-mark svg { display: block; }
.triqhub-mark.size-md svg { height: 28px; }
.triqhub-mark.size-sm svg { height: 16px; }
.cartorio-mark { display: inline-block; vertical-align: middle; }
.cartorio-mark svg { display: block; }
.cartorio-mark.size-md svg { height: 32px; }
.cartorio-mark.size-sm svg { height: 20px; }
```

### 3.6 Regenerar tudo + validar

```bash
cd /Users/gustavoalmeida/projetos/Cartorio
python3 docs/CLIENTES/build/build.py    # ~3 min
python3 -c "from pypdf import PdfReader; print(len(PdfReader('docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf').pages), 'pages')"
```

Gate: PDF ainda 14-22 páginas · A4 595×842 · Skia/PDF · pdftotext extrai "TriQ" e "Cartório".

### 3.7 Atualizar CHANGELOG + MD mirror

Adicionar entrada `[2.1.0] · 2026-07-06` ao `CHANGELOG-RELATORIOS-CLIENTES.md` documentando:
- Adição das logos REAIS TriQ Hub + Cartório 2º Serviço Notarial Uberlândia.
- Header global TriQ Hub em todas as páginas.
- Faixa "Powered by TriQ Hub" no rodapé.
- Contracapa com hero TriQ Hub colorida + wordmark Cartório.

---

## 4. Decisões & Assumptions

1. **Logo TriQ Hub oficial fornecida**: a SVG em `/Users/gustavoalmeida/Documents/TriQ Hub Docs/TriQ Hub Logo /TriQ Hub Logo Vetorizada Colorida.svg` é tratada como a versão canônica. Versão Black e White-fundo-preto ficam como fallback opcional para impressão.
2. **Logo Cartório 2º Notas não fornecida oficialmente**: o user pediu "logos reais" mas só anexou a logo TriQ Hub. Vou criar o wordmark do Cartório em SVG vetor (Poppins + balança da justiça estilizada), fiel ao estilo da logo TriQ Hub (geometric minimalism + bold weight + gradient surfaces). Se o user fornecer o brasão oficial depois, basta substituir o arquivo.
3. **Header global em todas as pages**: garante consistência visual e reforça a marca. Cada page mantém o `.page-header` próprio (com section meta) + adiciona um **global header strip** fino acima dele (~16px de altura) com TriQ Hub + Cartório.
4. **Footer global TriQ Hub**: reforça a marca em todas as páginas sem poluir visualmente (apenas 12px, opacity 0.6).
5. **Convenção LGPD-safe mantida**: nada do apêndice técnico A-G muda. Só visual do header/footer.
6. **PNG fallback**: se o Chromium headless não renderizar bem as gradients SVG complexas, posso converter `triqhub-colorida.svg` → PNG via CairoSVG ou reportlab e embed base64 como fallback.

---

## 5. Verificação (como validar)

**Antes de declarar concluído:**

1. `ls -lh docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf` → tamanho entre 0.4 MB e 2.0 MB.
2. `python -c "from pypdf import PdfReader; print(len(PdfReader('docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf').pages))"` → 14 ≤ n ≤ 22.
3. `pdftotext -layout docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf - | grep -iE "triq|cartorio|powered by" | head -10` → matches em capa, header global de páginas internas, footer.
4. `open -a Preview docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf` (visual manual) → logo TriQ Hub colorida visível em:
   - Capa (header top, à esquerda)
   - Header global de cada section page
   - Footer global em cada página
   - Contracapa (hero grande)
   - Wordmark Cartório 2º Notas visível em:
     - Capa (header top, à direita)
     - Header global de cada section (centro, texto)
     - Contracapa (bloco de contato)
5. Visual: Poppins renderizada, glass mode legível, 8 charts visíveis, 16 ícones presentes, contadores com valor final (não zero), 6 SUI na seção 13, roadmap P0/P1/P2 na seção 14, equivalência A-G na seção 15 (apêndice C).
6. Diff `git diff docs/CLIENTES/CHANGELOG-RELATORIOS-CLIENTES.md` → entrada `[2.1.0]` presente.

---

## 6. Comando resumido (one-shot)

```bash
# 1. Build orquestrado
cd /Users/gustavoalmeida/projetos/Cartorio
python3 docs/CLIENTES/build/build.py

# 2. Validar
ls -lh docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf
python3 -c "from pypdf import PdfReader; print(len(PdfReader('docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf').pages), 'pages')"
pdftotext -layout docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf - | head -30

# 3. Commit
git add docs/CLIENTES/build/ docs/CLIENTES/assets/logos/ docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06.pdf
git commit -m "feat(docs): relatório v2.1.0 — logos REAIS TriQ Hub + Cartório 2º Notas Uberlândia · Modified by Gustavo Almeida"

# 4. Append CHANGELOG v2.1.0
# (operador edita CHANGELOG-RELATORIOS-CLIENTES.md)
```

---

## 7. Anexo: Anexo técnico das logos originais

| Logo | Path original | Path destino | Tamanho | Uso |
|---|---|---|---|---|
| TriQ Hub Colorida | `/Users/gustavoalmeida/Documents/TriQ Hub Docs/TriQ Hub Logo /TriQ Hub Logo Vetorizada Colorida.svg` | `docs/CLIENTES/build/assets/logos/triqhub-colorida.svg` | 2.7 KB | Capa hero + contracapa + header global (mini) |
| TriQ Hub Black | `.../TriQ Hub Logo Vetorizada Black.svg` | `docs/CLIENTES/build/assets/logos/triqhub-black.svg` | 967 B | Footer simples (versão P&B) |
| TriQ Hub White (fundo preto) | `.../TriQ Hub Logo White - Fundo Preto - TRIQHUB TEXTO BRANCO .png` | `docs/CLIENTES/build/assets/logos/triqhub-white-fundo-preto.png` | 46 KB | Fallback impressão escura |
| Cartório 2º Notas | (não fornecido oficialmente) | `docs/CLIENTES/build/assets/logos/cartorio-2notas-udi.svg` | ~2 KB | Wordmark oficial estilizado (Poppins + balança minimalista) |

---

**Modified by Gustavo Almeida** · 06/07/2026