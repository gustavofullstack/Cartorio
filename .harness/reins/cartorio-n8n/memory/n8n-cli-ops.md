---
description: Padroes de operacao N8N via CLI e API - export, ativacao, quirks de schema, IF node bug e custom nodes workaround. Carregar quando for auditar/editar/migrar workflows N8N ou diagnosticar erro 4xx em POST /workflows.
---

# N8N CLI & API Ops

## Audit todos os workflows (sem credencial UI)

API key (`CARTORIO_API_KEY` env) bate 401 — UI nao ta exposta. CLI e o caminho confiavel:

```bash
ssh cartorio "docker exec \$(docker ps --format '{{.Names}}' | grep '^cartorio_n8n\.' | head -1) n8n export:workflow --all --pretty --output=/tmp/n8n-workflows.json"
ssh cartorio "docker cp \$(docker ps --format '{{.Names}}' | grep '^cartorio_n8n\.' | head -1):/tmp/n8n-workflows.json /tmp/"
scp cartorio:/tmp/n8n-workflows.json /tmp/
```

`/home/node/.n8n/config` so tem `encryptionKey`, sem basic auth.

Inspecao: `jq '.[] | {id, name, active, nodes: [.nodes[].type] | unique}'`.

## POST /workflows strict schema

API rejeita propriedades extras:

- `description` → "must NOT have additional properties"
- `tags` → "read-only"
- `active` → "read-only"

**Body minimo aceito**: `{name, nodes, connections, settings}`.

**Padrao correto em 3 chamadas**:
1. `POST /api/v1/workflows` com body minimo
2. `PATCH /workflows/{id}` com `{description, tags}`
3. `POST /workflows/{id}/activate` com body `{}`

## IF node `main[1] = []` quebra POST /workflows

`connections.<IF_NODE>.main[1]` (false branch) com array vazio da erro `unknown_connection_target`. Achei em `25-protocolo-concluido-pdf.json` pre-existing — `connections.Tem concluidos?.main[0][1].node = "Noop (sem concluidos)"` mas esse node nao existe no `nodes[]`.

**Fix**: ou omitir a entrada, ou conectar a um NoOp node real.

## Custom nodes nao aceitam activate

`@devlikeapro/n8n-nodes-chatwoot.Chatwoot` e `n8n-nodes-evolution-api.evo-api` dao `Unrecognized node type` no POST /activate, mesmo listados nos installed types. Variant correta do Evolution (ja usada em WF 12 staging) eh `n8n-nodes-evolution-api.evolutionApi` mas exige credential `evolutionApi` cadastrada — quebra activate ate config.

**Workaround usado em TODOS os 18 WFs E6** (substituir por httpRequest):

Chatwoot:
```
POST https://chatwoot.2notasudi.com.br/api/v1/accounts/1/conversations
header: api_access_token={{ $env.CHATWOOT_BOT_TOKEN }}
body: {source_id, message, inbox_id}
```

Evolution:
```
POST {{ $env.EVOLUTION_API_URL }}/message/sendText/cartorio-2notas
header: apikey={{ $env.EVOLUTION_API_KEY }}
body: {number, text}
```

Quando migrar de httpRequest para node oficial, **testar staging com 1 WF de cada tipo antes de promover 18**.

## Validar JSON antes de commit

Antes de qualquer git add em batch de WFs, validar parse:

```bash
for f in /Users/gustavoalmeida/projetos/Cartorio/infra/n8n-workflows/*.json; do
  python3 -c "import json; json.load(open('$f'))" || echo "INVALID: $f"
done
```

22 arquivos do range 13-30 validados OK — checagem pega typos de virgula/colchete antes de commit.