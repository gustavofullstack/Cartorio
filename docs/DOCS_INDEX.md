# 📚 Índice de Documentações Externas (Squad DOCS)

> **Status**: 5/5 (100%) — Squad DOCS COMPLETO ✅
> **Data**: 2026-06-25

Documentação consolidada de todos os serviços externos usados no projeto.

---

## 📂 Documentações Baixadas

| # | Serviço | Path | Tamanho | Versão |
|---|---------|------|---------|--------|
| 1 | **Evolution API** | [docs/evolution-api/README.md](evolution-api/README.md) | v2 README | v2.3.7 |
| 2 | **N8N** | [docs/n8n/README.md](n8n/README.md) | README | Latest |
| 3 | **Chatwoot** | [docs/chatwoot/README.md](chatwoot/README.md) | README | Latest |
| 4 | **Supabase** | [docs/supabase/README.md](supabase/README.md) | README | Latest (PG 15+) |
| 5 | **Redis** | [docs/redis/README.md](redis/README.md) | README | 8.8 |

---

## 🎯 O que cada doc contém

### docs/evolution-api/README.md
- Arquitetura completa (Baileys + Cloud API)
- Autenticação (apikey header)
- Variáveis de ambiente principais
- Links oficiais (docs, GitHub, Docker Hub)
- Status da nossa integração (cartorio-2notas instance)

### docs/n8n/README.md
- Conceitos fundamentais (workflows, nodes, triggers)
- Nodes principais (HTTP, Webhook, Code, Schedule, IF, Set)
- Plugins instalados (5)
- Padrões B07-B11 aplicados
- 34 workflows ativos listados
- Pendências Sprint 5+

### docs/chatwoot/README.md
- 12 funções do Chatwoot no Cartório
- Autenticação (API v1 + v2 OAuth)
- Endpoints principais
- 6 webhooks recebidos pela API
- Squad H 100% DONE
- INC-005b HOLD documentado

### docs/supabase/README.md
- 13 tabelas core do Cartório
- 134 tabelas totais
- 12 recursos Supabase (PostgREST, Auth, Storage, Realtime, Edge Functions, etc)
- 4 funções custom
- 16 migrações Alembic
- RLS ativo em 4 tabelas

### docs/redis/README.md
- Conexão (Tailscale + 4 DBs lógicos)
- Comandos mais usados (GET/SET/HSET/LPUSH/XADD)
- Padrões (Cache-Aside, Write-Through, Redlock)
- Métricas importantes
- Comandos perigosos (NUNCA em prod)
- Python clients (sync/async)

---

## 🔗 Links Externos para Aprofundar

| Serviço | Docs Oficial | GitHub |
|---------|--------------|--------|
| Evolution API | https://docs.evolutionfoundation.com.br | https://github.com/evolution-foundation/evolution-api |
| N8N | https://docs.n8n.io/ | https://github.com/n8n-io/n8n |
| Chatwoot | https://www.chatwoot.com/docs/ | https://github.com/chatwoot/chatwoot |
| Supabase | https://supabase.com/docs | https://github.com/supabase/supabase |
| Redis | https://redis.io/docs/ | https://github.com/redis/redis |

---

## ✅ Squad DOCS — DONE 100%

```
STATUS: 5/5 (100%)

DOCS1: Baixar docs Evolution API → docs/evolution-api/ ✅
DOCS2: Baixar docs N8N → docs/n8n/ ✅
DOCS3: Baixar docs Chatwoot → docs/chatwoot/ ✅
DOCS4: Baixar docs Supabase → docs/supabase/ ✅
DOCS5: Baixar docs Redis → docs/redis/ ✅
```

**Squad DOCS é 5/5 DONE = 100%!** Segunda squad a 100% (junto com Squad H Chatwoot).

---

## 🛠️ Como Atualizar

```bash
# Para cada serviço, atualizar quando:
# - Nova versão major é lançada
# - API breaking change
# - Novos recursos críticos

# Comando para verificar versão atual:
curl https://doc.evolution-api.com/  # Verificar se site voltou a funcionar
curl https://docs.n8n.io/  
curl https://www.chatwoot.com/docs/
curl https://supabase.com/docs
curl https://redis.io/docs/

# Editar README.md correspondente manualmente com mudanças
```

---

**Mantido por**: ZCode/Mavis (cartorio-zcode agent)
**Data de criação**: 2026-06-25 19:17 BRT
**Última atualização**: 2026-06-25 19:17 BRT