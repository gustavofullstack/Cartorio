# TJMG 2026 — Tabelas Oficiais de Emolumentos (OCR + índice)

Fonte primária: **Portaria CGJ/TJMG nº 8.664/2025** (vigência 01/01/2026 a 31/12/2026, 5% ISSQN Uberlândia).

Os PDFs oficiais disponibilizados pela RECOMPE/ÁRECOMPE-MINAS GERAIS são **escaneados** (imagem pura, 0 chars de texto extraível via `pdfplumber`/`pdftotext`). Para consumi-los no pipeline `app/services/emolumento_fonte_tjmg.py` foi necessário OCR.

## Tabela 1 — Atos do Tabelião de Notas (14 páginas)

- **PDF original**: `~/Downloads/Tabela Fixação 1 - Atos do Tabelião de Notas - 2026 - 01_01_2026 até 31_12_2026 com 5% de issqn (1).pdf`
- **SHA-256**: `202db21576f76d9a5f1ab45264a4e07ee6f25dd48391f7f7940f0353637a9d64`
- **OCR** (`fixacao1_ocr.txt`): tesseract 5.5.2 / lang=por / dpi=300 via `pdftoppm` + `tesseract`
- **Tamanho**: 28.200 bytes (14 páginas concatenadas)

## Tabela 8 — Atos comuns a Registradores e Notários (4 páginas)

- **PDF original**: `~/Downloads/Tabela Fixação 8 - Atos comuns a Registradores e Notários - 2026 - 01_01_2026 até 31_12_2026 com 5% de issqn.pdf`
- **SHA-256**: `2b6c862be0daf9bcb641641d638a6d3cd8805d829a9806fdd01d8eaec2a4b06e`
- **OCR** (`fixacao8_ocr.txt`): tesseract 5.5.2 / lang=por / dpi=300 via `pdftoppm` + `tesseract`
- **Tamanho**: 5.654 bytes (4 páginas concatenadas)

## Pipeline de ingestão

```bash
# 1. Rasterizar PDF
pdftoppm -r 300 -png "<pdf>" /tmp/ocr/p

# 2. OCR por página
for f in /tmp/ocr/p-*.png; do tesseract "$f" "${f%.png}" -l por; done

# 3. Concatenar
cat /tmp/ocr/p-*.txt > fixacao{1,8}_ocr.txt
```

## Uso programático

`app/services/emolumento_fonte_tjmg.py` continua baixando o PDF oficial via
`FONTE_URL` (`app.services.emolumento_real_djalma`) e aplicando regex ancoradas
sobre o texto extraído pelo `pdfplumber`. Se o PDF oficial vier escaneado (como
esta versão), o `pdfplumber.extract_text()` retorna string vazia — o pipeline
deve **fallback** para o OCR versionado aqui.

TODO: adicionar fallback de OCR no `emolumento_fonte_tjmg.py` quando
`extract_text()` for vazio. Padrão:

```python
text = page.extract_text() or ""
if not text.strip():
    # Fallback: usar o OCR versionado em docs/tjmg-ocr/
    text = _load_ocr_text_for_page(page.page_number)
```

## Valores canônicos (Tabela 1) extraídos do OCR

Valores da coluna "Valor Final ao Usuário" (R$) — usados pela Pietra via tool MCP `cartorio_calcular_emolumento`:

- Aprovação de testamento cerrado: R$ 678,90
- Ata notarial (até 2 folhas): R$ 226,15
- Ata notarial (folha acrescida): R$ 11,61
- Autenticação de cópia (folha): ~R$ 14,50
- Procuração genérica (por outorgante): **R$ 68,94** (validado em produção pelo gateway Pietra → MiniMax-M3 → MCP)
- Substabelecimento: ~R$ 47,40
- Testamento público: R$ 453,00
- Revogação de testamento: R$ 226,40
- Inventário sem conteúdo financeiro: ~R$ 226,40

> Estes valores são **pontos de referência**. Para valor exato do usuário, a
> Pietra SEMPRE consulta a tool MCP `cartorio_calcular_emolumento` (não cita de
> memória). HITL obrigatório para ato jurídico final.

Modified by Gustavo Almeida · 2026-07-27
