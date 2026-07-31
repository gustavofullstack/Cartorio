# Ingestao offline do corpus privado BRAIN

O script `scripts/brain_corpus_ingest.py` cria uma fronteira local e fail-closed
para o corpus mantido em `.private/brain-ingest-quarantine/2026-07-31-ce236ba32b01`.
Ele nao chama rede, LLM, embeddings, APIs, navegadores ou automacao de escritorio.

## Execucao

```bash
uv run --project backend python scripts/brain_corpus_stage_zip.py \
  /caminho/privado/corpus.zip --destination \
  .private/brain-ingest-quarantine/<batch>
uv run --project backend python scripts/brain_corpus_ingest.py
```

O unico stdout e um resumo numerico sem nomes, paths, texto extraido ou valores
de PII. O processo retorna `2` quando existir qualquer erro parcial bloqueante.

## Limites de seguranca

- Aceita somente DOCX, ODT, PDF e TXT locais; symlinks e formatos desconhecidos
  geram erro bloqueante opaco.
- O staging rejeita path traversal, symlink, criptografia, colisão Unicode/case,
  extensão inesperada, excesso de tamanho/ratio e nunca sobrescreve lote existente.
- Cada arquivo e extraido em processo isolado, com timeout por arquivo. PDFs
  usam somente `pdftotext -layout`, com timeout e stderr descartado.
- DOCX preserva locators para body, tabelas/células, caixas de texto, cabeçalho,
  rodapé, notas e comentários; elementos gráficos ainda exigem revisão visual.
- PDF sem camada de texto usa fallback OCR exclusivamente local (`pdftoppm` e
  `tesseract`) por pagina. O fallback limita cinco paginas, 80 MiB de imagens,
  60 segundos de renderizacao e 20 segundos por pagina; os temporarios vivem em
  `derived/` e sao removidos. Limite, timeout ou dependencia ausente gera erro
  opaco bloqueante.
- A saida e permitida apenas em `derived/`, subdiretorio `0700` da quarentena
  ignorada pelo Git; derivados são `0600`. Os arquivos-fonte nunca sao alterados.
- IDs de fonte sao SHA-256 opacos do caminho relativo. Manifestos e relatorios
  nao contem nome, caminho, excecao original ou texto-fonte.
- Unidades persistidas possuem localizador, ID e hash. Antes de persistir, máscaras
  específicas e o scrubber canônico são aplicados; URLs são removidas. Nomes e
  endereços livres continuam sob revisão contextual obrigatória.

## Derivados

- `manifest.sanitized.json`: inventario sanitizado, hashes, contagens e estado.
- `units.sanitized.jsonl`: unidades sanitizadas com localizadores e hashes.
- `errors.blocking.json`: codigos categoricos de erro, sempre bloqueantes.

Uma fonte sem texto extraivel (por exemplo, PDF escaneado sem OCR local) permanece
no relatorio como `empty_extraction`; nenhuma etapa posterior deve consumir o
corpus enquanto `is_blocked` for verdadeiro.

## Etapa seguinte (classificação)

Após ingestão com `is_blocked=false`, rodar a classificação offline (ainda
sem publicação):

```bash
uv run --project backend python scripts/brain_corpus_classify.py
```

Saída em `derived/classification.sanitized.json`. Documentação completa do
ciclo de vida, HITL e gates: `docs/BRAIN_PIPELINE_CONHECIMENTO.md`.

Assinatura: @Codex/corpus_pipeline
