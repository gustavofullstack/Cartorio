# Ingestao offline do corpus privado BRAIN

O script `scripts/brain_corpus_ingest.py` cria uma fronteira local e fail-closed
para o corpus mantido em `.private/brain-ingest-quarantine/2026-07-31-ce236ba32b01`.
Ele nao chama rede, LLM, embeddings, APIs, navegadores ou automacao de escritorio.

## Execucao

```bash
uv run --project backend python scripts/brain_corpus_ingest.py
```

O unico stdout e um resumo numerico sem nomes, paths, texto extraido ou valores
de PII. O processo retorna `2` quando existir qualquer erro parcial bloqueante.

## Limites de seguranca

- Aceita somente DOCX, ODT, PDF e TXT locais; symlinks e formatos desconhecidos
  geram erro bloqueante opaco.
- Cada arquivo e extraido em processo isolado, com timeout por arquivo. PDFs
  usam somente o binario local `pdftotext`, tambem com timeout e stderr descartado.
- A saida e permitida apenas em `derived/`, subdiretorio da propria quarentena
  ignorada pelo Git. Os arquivos-fonte nunca sao alterados.
- IDs de fonte sao SHA-256 opacos do caminho relativo. Manifestos e relatorios
  nao contem nome, caminho, excecao original ou texto-fonte.
- Unidades persistidas possuem localizador, ID e hash. Antes de persistir, os
  padroes reconhecidos de CPF, CNPJ, email, telefone, CEP e RG sao substituidos.
  URLs tambem sao removidas. Os manifestos guardam somente tipo e contagem de PII.

## Derivados

- `manifest.sanitized.json`: inventario sanitizado, hashes, contagens e estado.
- `units.sanitized.jsonl`: unidades sanitizadas com localizadores e hashes.
- `errors.blocking.json`: codigos categoricos de erro, sempre bloqueantes.

Uma fonte sem texto extraivel (por exemplo, PDF escaneado sem OCR local) permanece
no relatorio como `empty_extraction`; nenhuma etapa posterior deve consumir o
corpus enquanto `is_blocked` for verdadeiro.

Assinatura: @Codex/corpus_pipeline
