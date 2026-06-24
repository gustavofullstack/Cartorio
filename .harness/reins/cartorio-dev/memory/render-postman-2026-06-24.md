# Render + Postman — 2026-06-24

> Sessão: ZCode + MiniMax-M3 (orquestrador).
> **Resultado: SUCCESS — Render auto-deploy ON + Postman collection v2 50 requests**.

## Render (já conectado, working)

- **Service ID**: `srv-d8u04aojs32c73c92j8g`
- **URL**: `https://cartorio-lrkp.onrender.com`
- **Plan**: free
- **Region**: ohio
- **Auto-deploy**: `yes` ✅ (commits em master → rebuild automático)
- **Branch**: `master`
- **Última deploy visível** (no commit `a8824ae` ou similar)

## Postman Collection v2 (commit 3b75e54)

- **Arquivo**: `docs/POSTMAN_COLLECTION.json` (52 KB)
- **Requests**: 50 (1 por path OpenAPI)
- **Auth**: API Key no header `X-API-Key` (com fallback via variable `cartorio_api_key`)
- **Variables**: `cartorio_api_key`, `base_url`
- **Importar no Postman**: File → Import → Selecionar o JSON

## Postman Guide (commit 3b75e54)

- **Arquivo**: `docs/POSTMAN_GUIDE.md` (39 linhas)
- Como importar collection
- Onde setar `cartorio_api_key` (variable)
- Lista dos 10 endpoints mais importantes
- Exemplo: testar `/health/llm`, `/atendimento/list-active`, `/cliente/1/lgpd/anonimizar`
- Troubleshooting (401 = key errada, 404 = endpoint não existe)

## docs/API.md atualizado (commit 3b75e54)

- Seção "Documentação OpenAPI" adicionada com:
  - Swagger UI: https://api.2notasudi.com.br/docs
  - ReDoc: https://api.2notasudi.com.br/redoc
  - OpenAPI JSON: https://api.2notasudi.com.br/openapi.json
  - Postman Collection: POSTMAN_COLLECTION.json (50 paths, 80+ endpoints)
  - Postman Guide: POSTMAN_GUIDE.md

## Próximos passos

### Curto prazo
- [ ] Testar import no Postman (clicar "Run collection" → todos 50 devem passar com 200/201/404)
- [ ] Validar que o `cartorio_api_key` variable está setado
- [ ] Gerar ambiente dev/prod separados (2 variables)

### Médio prazo
- [ ] Ativar `pullRequestPreviewsEnabled` no Render (já tem `autoDeploy: yes`)
- [ ] Setup Render pre-commit hook para preview deploys
- [ ] Configurar DNS `n8n.2notasudi.com.br` + `supabase.2notasudi.com.br` no Cloudflare (manual)

Modified by Gustavo Almeida
