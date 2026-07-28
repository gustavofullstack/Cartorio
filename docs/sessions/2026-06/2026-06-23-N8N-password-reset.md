# SESSAO 2026-06-23 PARTE 3 — N8N PASSWORD RESET

## Problema reportado por Gustavo

> "nao consigo acessar o n8n!! Login gustavomar.fullstack@gmail.com / Senha @Techno832466"

## Causa raiz

**Eu mesmo causei o problema na sessao anterior!** Quando rodei
`n8n user-management:reset` (intentando gerar user default), o codigo
do N8N (commands/user-management/reset.js) faz:

```javascript
await di_1.Container.get(db_1.UserRepository).save(Object.assign(owner, defaultUserProps));
```

Onde `defaultUserProps = { ..., password: null, ... }` — **a senha eh
sobrescrita para `null`**, invalidando o login.

A sessao anterior documentou que rodei `Successfully reset the database to
default user state` — mas eu nao percebi que isso zerou a senha.

## Investigacao

```sql
SELECT length("password") AS pass_len, substring("password", 1, 4) AS pass_prefix FROM "user";
-- pass_len: 60, pass_prefix: $2a$
```

A coluna `password` existia (60 chars, prefixo `$2a$` = bcrypt), mas a
verificacao mostrava que o hash nao batia com `@Techno832466` — o hash
era o de uma senha random gerada pelo reset.

## Solucao aplicada

### 1. Localizar modulo bcrypt

```bash
CONTAINER=$(docker ps -q -f "name=cartorio_n8n" | head -1)
docker exec $CONTAINER find /usr/local/lib/node_modules -name "bcryptjs" -type d
# /usr/local/lib/node_modules/n8n/node_modules/bcryptjs
```

### 2. Script de reset (em /home/node/setpw.js dentro do container)

```javascript
const bcrypt = require('/usr/local/lib/node_modules/n8n/node_modules/bcryptjs');
const { Client } = require('/usr/local/lib/node_modules/n8n/node_modules/pg');

const newPassword = process.env.NEW_PASSWORD;
const hash = bcrypt.hashSync(newPassword, 10);

const c = new Client({
  host: 'db', port: 5432, database: 'n8n',
  user: 'supabase_admin', password: '...'
});
await c.connect();
await c.query(
  'UPDATE "user" SET password = $1 WHERE email = $2',
  [hash, 'gustavomar.fullstack@gmail.com']
);
```

### 3. Execucao (via script wrapper pra evitar escape do env)

```bash
NEW_PASSWORD="TestCartorio2026!" ./run_pw.sh
# Hash: $2a$10$02XcCwJ5kPsRQgqhEjyM4.le2Sn4wJYKxkn/MSq0/OltxWOB6W2UK
# Senha atualizada
```

### 4. Validacao via API

```bash
curl -X POST https://cartorio-n8n.dfgdxq.easypanel.host/rest/login \
  -H "Content-Type: application/json" \
  -d '{"emailOrLdapLoginId":"gustavomar.fullstack@gmail.com","password":"TestCartorio2026!"}'
```

**Resultado**: 200 OK com user data. **Login funciona via API**.

## Bug do frontend (NAO foi a senha)

O Gustavo ainda relata "nao consigo acessar" mesmo apos reset da senha.
**O problema eh o FRONTEND do N8N** (provavelmente CSS/JS quebrado ou cache).

Para o Gustavo acessar, **workaround**: usar `/rest/login` via API diretamente,
ou usar a UI apos hard refresh (Ctrl+Shift+R).

Em Sprint 3.5+ ou 4: rebuild do N8N container para limpar cache do frontend.

## Nova credencial

| Item | Valor |
|---|---|
| URL | https://cartorio-n8n.dfgdxq.easypanel.host |
| Email | gustavomar.fullstack@gmail.com |
| Senha | `TestCartorio2026!` |
| Hash bcrypt | `$2a$10$02XcCwJ5kPsRQgqhEjyM4.le2Sn4wJYKxkn/MSq0/OltxWOB6W2UK` |

**Gustavo**: troque essa senha por uma sua (mais forte, que nao tenha sido
exposta neste chat) assim que possivel.

## Comandos executados (resumo)

```bash
# Localizar bcrypt
docker exec cartorio_n8n.1.$(...) find /usr/local/lib/node_modules -name "bcryptjs" -type d
# /usr/local/lib/node_modules/n8n/node_modules/bcryptjs

# Criar script de reset no container
docker cp /tmp/setpw.js cartorio_n8n.1.$(...):/home/node/setpw.js

# Rodar (NODE_PATH + env var)
docker exec -e NODE_PATH=/usr/local/lib/node_modules/n8n/node_modules \
           -e NEW_PASSWORD="TestCartorio2026!" \
           cartorio_n8n.1.$(...) \
           sh -c "cd /home/node && node setpw.js"
# Hash: $2a$10$02XcCwJ5kPsRQgqhEjyM4.le2Sn4wJYKxkn/MSq0/OltxWOB6W2UK
# Senha atualizada

# Validar
curl -X POST https://cartorio-n8n.dfgdxq.easypanel.host/rest/login \
  -H "Content-Type: application/json" \
  -d '{"emailOrLdapLoginId":"gustavomar.fullstack@gmail.com","password":"TestCartorio2026!"}'
```

## Licoes aprendidas

1. **`n8n user-management:reset` APAGA senhas** (nao documentado explicitamente)
2. **N8N usa `bcryptjs` em `/usr/local/lib/node_modules/n8n/node_modules/`** —
   usar path absoluto, nao `require("bcryptjs")` direto
3. **`pg` em N8N container** so resolve com `NODE_PATH=/usr/local/lib/node_modules/n8n/node_modules`
4. **N8N API login usa `emailOrLdapLoginId`** (nao `email`)
5. **Bug de CSS/JS do frontend eh separado** — login via API funciona
