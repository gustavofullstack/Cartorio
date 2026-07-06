# Plano · PDF v2 — Executivo TriQ Hub → 2º Ofício (22/06–06/07/2026)

> **Status**: Pronto para aprovação. Aguardando GO do Gustavo.
> **Mudança vs v1**: incorporação das logos reais da TriQ Hub (fornecedor) e posicionamento da TriQ Hub como **empresa executora** + 2º Ofício como **cliente/destinatário**.

---

## 1. Resumo

Regerar o PDF executivo Felipe & Djalma com **as logos TriQ Hub reais** incorporadas em pontos-chave (capa, rodapé, cabeçalho de seções, encerramento) — sem alterar o conteúdo técnico já validado. Mudança puramente visual + de marca: o relatório agora comunica claramente que a **TriQ Hub é a empresa de tecnologia** que está prestando o serviço para o **2º Serviço Notarial de Uberlândia**.

---

## 2. Análise do Estado Atual (já temos tudo do v1)

| Recurso v1 | Estado | Reaproveitar? |
|---|---|---|
| `evidence_pdf.json` | ✓ em `.trae/documents/` | SIM (recoletar p/ timestamp atual) |
| 8 charts PNG | ✓ em `docs/CLIENTES/assets/charts/` | SIM |
| 16 ícones PNG | ✓ em `docs/CLIENTES/assets/icons_png/` | SIM |
| 4 fontes Poppins TTF | ✓ em `docs/CLIENTES/assets/fonts/` | SIM |
| `build_pdf.py` | ✓ em `.trae/work/.../pdf-cartorio/` | SIM — modificar p/ injetar logos |
| `Felipe_Djalma_STATUS_2026-07-06.pdf` (22p) | ✓ entregue | Manter como v1; gerar v2 ao lado |

**Logos TriQ Hub disponíveis** (5 arquivos em `.trae/attachments/...`):
- `TriQ Hub Logo Vetorizada Black.png` (preto/branco)
- `TriQ Hub Logo Vetorizada Black.svg`
- `TriQ Hub Logo Vetorizada Colorida.png` ← **preferida p/ capa colorida**
- `TriQ Hub Logo Vetorizada Colorida.svg`
- `TriQ Hub Logo White - Fundo Preto - TRIQHUB TEXTO BRANCO .png` ← **preferida p/ header preto**

---

## 3. Decisões de Design (propostas)

| Aspecto | Decisão | Justificativa |
|---|---|---|
| Capa | **Logo TriQ Hub Colorida** centralizada no topo + nome do projeto + destinatários abaixo | "Quem fez" fica claro |
| Header (todas as páginas conteúdo) | Logo TriQ Hub White (preto) à esquerda + texto "2º SERVIÇO NOTARIAL DE UBERLÂNDIA" | Identifica o cliente |
| Footer (todas as páginas) | "Tecnologia: TriQ Hub" + Modified by Gustavo Almeida | "Quem está fazendo" |
| Capa (parte inferior) | Logo TriQ Hub Colorida menor (40mm) + "Executado por TriQ Hub" | Reforça a marca executora |
| Posição relativa | TriQ Hub **acima** de 2º Ofício na hierarquia visual do documento | Quem entrega o serviço aparece primeiro; cliente aparece como destinatário |

**Texto do header** (padrão em todas as páginas de conteúdo):
```
[TRIQ HUB logo]  2º SERVIÇO NOTARIAL DE UBERLÂNDIA  ·  Relatório executivo 22/06 → 06/07/2026
```

**Texto do footer** (padrão):
```
Tecnologia: TriQ Hub · Modified by Gustavo Almeida · v1.1                                 06
```

---

## 4. Mudanças Concretas em `build_pdf.py`

| # | Local | Mudança | Por quê |
|---|---|---|---|
| 1 | Imports | Adicionar leitura das logos via `Image()` em pontos de capa/header/footer | Renderizar PNG (mais simples que SVG) |
| 2 | `cover_page_bg` | Inserir `Image("logo_colorida.png", width=70, height=22)` no topo (~Y=PAGE_H-100) | Marca visível na capa |
| 3 | `header_footer` | Inserir `Image("logo_white.png", width=18, height=18)` à esquerda do texto do header | Marca visível em todas as páginas internas |
| 4 | `header_footer` | Atualizar texto do header para `"2º SERVIÇO NOTARIAL DE UBERLÂNDIA"` + "Tecnologia: TriQ Hub" no footer | Hierarquia cliente + fornecedor explícita |
| 5 | Capa (story) | Inserir `Image("logo_colorida.png", width=80, height=25)` antes do título | Reforça marca na capa |
| 6 | Página final (Contato) | Adicionar linha "Executado por TriQ Hub · Gustavo Almeida, Tech Lead" | Encerramento reforça fornecedor |
| 7 | `OUT_PDF` | Renomear para `executive-report-2026-07-06-v2.pdf` (não sobrescrever v1) | Versionamento explícito |
| 8 | `metadata.title` | Atualizar para `"Relatório Executivo — TriQ Hub → 2º Serviço Notarial de Uberlândia"` | Metadados refletem relação |

---

## 5. Arquivos a Criar/Modificar

### 5.1 Pasta de build (intermediária) — `~/.trae/work/.../pdf-cartorio/`
```
build_pdf.py                          # modificar conforme §4
assets/logos/                         # NOVA pasta
├── triqhub_colorida.png              # copiado do upload
├── triqhub_white.png                 # copiado do upload
└── triqhub_black.png                 # opcional
out/executive-report-2026-07-06-v2.pdf  # saída v2
```

### 5.2 Entregáveis finais (workspace do usuário)
```
docs/CLIENTES/
├── Felipe_Djalma_STATUS_2026-07-06.pdf       # v1 (preservado)
├── Felipe_Djalma_STATUS_2026-07-06-v2.pdf    # v2 NOVO (com logos TriQ Hub)
├── assets/logos/triqhub_*.png                # logos copiadas
├── CHANGELOG-RELATORIOS-CLIENTES.md          # atualizar p/ v1.2.0
└── relatorio-2-semanas-felipe-djalma-2026-07-06/  # (já existe; v2 entra)
.brain/
└── executive-report-felipe-djalma-2026-07-06-v2.pdf  # cópia paralela
```

### 5.3 Comando de cópia das logos
```bash
mkdir -p /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/assets/logos
cp "/Users/gustavoalmeida/.trae/attachments/6a4b99e14eac4e209ead3cfc/d8eac760-fb8f-410c-8fb1-eda57d4e5ae5_4a9b6489-7ee9-44ff-bc36-e5776f99cab1_TriQ Hub Logo Vetorizada Colorida.png" \
   /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/assets/logos/triqhub_colorida.png
cp "/Users/gustavoalmeida/.trae/attachments/6a4b99e14eac4e209ead3cfc/9b95f443-9da2-4c69-add7-21314f0fc67d_e1906a4f-89a6-412f-b1ca-d185d70bca00_TriQ Hub Logo White - Fundo Preto - TRIQHUB TEXTO BRANCO .png" \
   /Users/gustavoalmeida/projetos/Cartorio/docs/CLIENTES/assets/logos/triqhub_white.png
```

---

## 6. Estratégia de Render das Logos

| Logo | Tamanho PDF (largura × altura) | Posição | Quando aparece |
|---|---|---|---|
| `triqhub_colorida.png` | 70 × 22 mm | Capa — topo centralizado | Página 1 apenas |
| `triqhub_colorida.png` | 80 × 25 mm | Capa — abaixo do título, centro | Página 1 apenas |
| `triqhub_white.png` | 18 × 18 mm | Header — esquerda (band preta) | Todas as páginas internas |
| `triqhub_colorida.png` | 40 × 13 mm | Capa — rodapé | Página 1 |
| (opcional) `triqhub_black.png` | 30 × 9 mm | Última página (Contato) — após assinatura | Última página |

**Render via reportlab**: usar `Image("logo.png", width=70*mm, height=22*mm)`. Reportlab detecta PNG automaticamente.

**Validação de proporção**: triqhub_colorida tem proporção ~3.2:1 (largura:altura). Sempre passar ambos `width` e `height` para evitar distorção.

---

## 7. Validação

| Gate | Comando | Critério |
|---|---|---|
| Tamanho | `ls -lh docs/CLIENTES/Felipe_Djalma_STATUS_2026-07-06-v2.pdf` | < 1 MB (logos adicionam ~50KB) |
| Metadados | `pdfinfo` | A4, language=pt-BR, title atualizado |
| Integridade | `qpdf --check` | exit 0 |
| Texto extraível | `pdftotext` | Capa extraível como texto |
| Logos visíveis | `pdftoppm -r 100 -f 1 -l 1 v2.pdf preview` + visualização | Logo TriQ Hub presente na capa e header |

---

## 8. Conformidade AGENTS.md

- **Conventional Commits**: se commitado, `docs(clientes): relatorio executivo v2 com logos TriQ Hub — Modified by Gustavo Almeida`.
- **Branch**: `feat/relatorio-felipe-djalma-2026-07-06-v2` (gated by Gustavo).
- **Sem tocar** `audit.py`/`pii.py`.
- **PDF v1 preservado** (não sobrescrito).

---

## 9. Resumo em 5 linhas

Plano focado: regenerar o PDF executivo v1 já validado, **somente alterando o posicionamento visual das logos TriQ Hub** (capa, header, footer, encerramento) para que o relatório comunique explicitamente "TriQ Hub executou para 2º Ofício". Conteúdo técnico (8 charts, 16 ícones, 22 páginas, Poppins, glass mode, 13 seções) **permanece 100% intacto** — reaproveita `evidence_pdf.json`, charts, ícones, fontes e o `build_pdf.py` modificado em 7 pontos cirúrgicos. Saída: `Felipe_Djalma_STATUS_2026-07-06-v2.pdf` (~22 páginas, < 1 MB) ao lado do v1 preservado, com `qpdf --check` validando integridade.
