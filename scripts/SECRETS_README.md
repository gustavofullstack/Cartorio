# scripts/unify_services.sane.js + trigger_deploys.js

> Migração e deploy em massa dos serviços Cartório no Easypanel via LMDB.

## Por que existem

`unify_services.js` (original, 2026-07-02) foi escrito uma vez para corrigir envs de 10
serviços que ainda apontavam para hosts fantasmas (`db`, `cartorio_langfuse-db`,
`cartorio_argilla-redis`, etc). Junto com `trigger_deploys.js`, ele disparou
rolling-restart em massa que consolidou a stack em torno de `cartorio_supabase` +
`cartorio_redis`.

**O original continha senhas em texto puro** (`@Techno832466`, `argillaPassword123`,
`0vrszdxd19zweryz7cfl`). Como esses scripts rodam direto no VPS lendo o LMDB do
Easypanel em `/etc/easypanel/data`, são úteis para migração única mas **não
portáveis e não-commitableis**.

`unify_services.sane.js` é a versão **re-aproveitável**: lê credenciais de
`process.env` (com fallbacks em `deploy/secrets.env`, `/etc/cartorio/easypanel-secrets.env`,
`/tmp/easypanel-secrets.env`), aborta se faltar var obrigatória, e suporta dry-run.

## Uso

```bash
# 1. Copiar template e preencher
cp deploy/secrets.example.env /tmp/easypanel-secrets.env
$EDITOR /tmp/easypanel-secrets.env

# 2. Carregar vars no shell
set -a; source /tmp/easypanel-secrets.env; set +a

# 3. Dry-run (mostra o que mudaria sem persistir)
UNIFY_DRY_RUN=1 node scripts/unify_services.sane.js

# 4. Aplicar de verdade
node scripts/unify_services.sane.js

# 5. Disparar rolling-restart dos 10 serviços modificados
node scripts/trigger_deploys.js
```

## Requisitos

- Node 18+ (testado em 22.x)
- `lmdb` (`npm i lmdb` ou usar o node_modules do Easypanel em `/opt/easypanel/`)
- Acesso leitura+escrita em `/etc/easypanel/data` (root)
- Port 3000 do Easypanel reachable em localhost (ou via Traefik)

## Arquivos

| Arquivo | Status | Função |
|---|---|---|
| `scripts/unify_services.js` | ⚠️ original, NÃO RODAR | tem senhas em claro, era one-shot |
| `scripts/unify_services.sane.js` | ✅ use este | versão portável, sem segredos |
| `scripts/trigger_deploys.js` | ✅ | faz POST /api/deploy/<token> para cada serviço |
| `deploy/secrets.example.env` | ✅ template | copiar para `secrets.env` ou `/tmp/...` |

## Segurança

- `.gitignore` na raiz já exclui `deploy/secrets.env`, `.secrets/`, `*.env`
- Os caminhos `/etc/cartorio/easypanel-secrets.env` e `/tmp/easypanel-secrets.env`
  são convencionalmente fora do repo
- **Nunca** comitar `secrets.env` preenchido

Modified by Gustavo Almeida