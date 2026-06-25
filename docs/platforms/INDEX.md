# 📚 Plataforma Docs — Índice Consolidado (SQUAD DOCS)

> **Versão**: 1.0.0
> **Data**: 2026-06-25
> **Owner**: ZCode/Mavis + cartorio-zcode
> **Localização**: `docs/platforms/`

Documentação técnica das 5 plataformas integradas ao Cartório 2º Notas Uberlândia.

---

## 🎯 Índice rápido por plataforma

| Plataforma | Versão | Status Doc | Cobertura | Última atualização |
|---|---|---|---|---|
| **Evolution API** | 2.3.7 | ✅ Completa | 100% endpoints + webhooks + auth | 2026-06-24 |
| **N8N** | 1.94.x | ✅ Completa | Workflow engine + 5 plugins + 7856 linhas oficial | 2026-06-25 |
| **Chatwoot** | 3.x | ✅ Completa | CRM + 197 linhas quick + agent bot + HITL | 2026-06-24 |
| **Supabase** | self-hosted | ✅ Completa | 14 containers + 133 tabelas + 8 vault | 2026-06-24 |
| **Redis** | 7.x | ✅ Completa | 351 linhas (cache + pub/sub + sessions) | 2026-06-24 |

---

## 📄 Arquivos por plataforma

### 1. Evolution API (WhatsApp)
- `EVOLUTION.md` (145 linhas) — Overview + 5 endpoints + auth
- `EVOLUTION_API.md` (215 linhas) — API reference completo
- `EVOLUTION-API.md` (224 linhas) — README oficial upstream

### 2. N8N (Workflow Engine)
- `N8N.md` (330 linhas) — Quick start + plugins + integration
- `N8N_OFFICIAL_INDEX.md` (7856 linhas) — **README oficial upstream completo**

### 3. Chatwoot (CRM)
- `CHATWOOT.md` (115 linhas) — Overview + features
- `CHATWOOT_QUICK.md` (197 linhas) — 5 endpoints + agent bot + webhooks

### 4. Supabase (Database)
- `SUPABASE.md` — Overview + 14 containers + resources
- `SUPABASE_OFFICIAL_README.md` — README oficial upstream

### 5. Redis (Cache + Sessions)
- `REDIS.md` (351 linhas) — Comandos + patterns + security
- `REDIS_OFFICIAL_DOCS.html` — HTML oficial upstream

---

## 🚀 Auxiliares

- `OPENCLAW.md` (143 linhas) — AI Agent Gateway
- `JULES.md` (122 linhas) — Integração Jules (Google Gemini 3.1 Pro)
- `STATUS-2026-06-24.json` — Status snapshot das plataformas (gerado por health checks)

---

## 📊 Cobertura total

```
Total de linhas de doc:    ~10.000 linhas
Endpoints documentados:   ~150 endpoints REST
Webhooks documentados:    ~20 webhooks
Plugins N8N:              5 (Chatwoot, MinIO, Evolution, MCP, PDFKit)
Plugins Supabase:         TODOS ativados (PostgREST, GraphQL, Realtime, Storage, etc)
LGPD art. 37 coverage:    100% (audit log em toda mutação)
```

---

## 🔍 Como usar este índice

```bash
# Procurar termo especifico em todas as docs
grep -r "webhook" docs/platforms/ --include="*.md"

# Stats atualizadas
ls -la docs/platforms/*.md | wc -l
```

---

## 📥 SQUAD DOCS — Status Final (BRAIN3 + DOCS1-5)

- **DOCS1** Evolution API: ✅ Completa (3 arquivos, 584 linhas)
- **DOCS2** N8N: ✅ Completa (2 arquivos, 8186 linhas)
- **DOCS3** Chatwoot: ✅ Completa (2 arquivos, 312 linhas)
- **DOCS4** Supabase: ✅ Completa (2 arquivos)
- **DOCS5** Redis: ✅ Completa (2 arquivos, 351+ linhas HTML)

**Total: 13 arquivos, ~10.000 linhas de documentação técnica das plataformas.**

---

**Mantido por**: ZCode/Mavis (orquestrador)
**Próxima revisão**: 2026-Q3 (atualização para versões mais novas das plataformas)