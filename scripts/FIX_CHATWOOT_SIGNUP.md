# FIX Chatwoot Signup Loop — Passo a Passo

**Problema:** Ao tentar login com `admin@2notasudi.com.br`, Chatwoot mostra tela de signup. Quando você tenta criar conta, dá erro "já existe". Loop infinito.

**Causa raiz verificada live (2026-07-01 12:30 BRT):**

```bash
ssh root@100.99.172.84 'docker exec cartorio_chatwoot sh -c "env | grep SIGNUP"'
# ENABLE_ACCOUNT_SIGNUP=true  ← PROBLEMA
```

Quando `ENABLE_ACCOUNT_SIGNUP=true`, a UI do Chatwoot renderiza **signup** em vez de **login**. Mas o admin já existe, então signup falha.

## Solução (2min)

### Opção 1: Easypanel UI (recomendado)

1. Abra https://easypanel.2notasudi.com.br
2. Projeto **cartorio** → service **chatwoot**
3. Aba **Environment** (ou "Env Vars")
4. **Adicione** ou **edite**:
   - Nome: `ENABLE_ACCOUNT_SIGNUP`
   - Valor: `false`
5. **Save** → Easypanel vai reiniciar o serviço automaticamente
6. Aguarde 30s
7. Recarregue https://chat.2notasudi.com.br — agora deve mostrar **login**

### Opção 2: SSH direto (alternativa)

```bash
ssh root@100.99.172.84
docker service update --env-add ENABLE_ACCOUNT_SIGNUP=false cartorio_chatwoot
# ou (mais limpo):
docker service inspect cartorio_chatwoot > /tmp/cw.json
# edita o env, depois:
docker service update --config /tmp/cw.json cartorio_chatwoot
```

### Login após fix

- URL: https://chat.2notasudi.com.br
- Email: **admin@2notasudi.com.br**
- Senha: a que você definiu quando criou o admin (ou via recovery email)

Se não lembra a senha, recupere via Chatwoot Super Admin panel ou reset via DB.

## Por que isso acontece

`ENABLE_ACCOUNT_SIGNUP=true` foi setado na config antiga do Chatwoot 3.x. No Chatwoot 4.x:
- A flag deveria ser `FRONTEND_SIGNUP_ENABLED`
- O comportamento padrão deveria ser signup DESABILITADO (LGPD)

A flag legacy `ENABLE_ACCOUNT_SIGNUP` ainda é respeitada por compatibilidade — daí o bug.

## Após o fix

```bash
# Confirmar que tá OK
ssh root@100.99.172.84 'docker exec cartorio_chatwoot sh -c "env | grep SIGNUP"'
# esperado: ENABLE_ACCOUNT_SIGNUP=false

# Testar login
curl -sS -I https://chat.2notasudi.com.br/auth/sign_in
# esperado: 200 (não 302 pra /auth/signup)
```

## Referência

- Chatwoot 4.x docs: https://www.chatwoot.com/docs/self-hosted/configuration/environment-variables
- Lesson 110 (pgvector) — outra issue Chatwoot
- T11 do `task-bank-turn50.json`

Modified by Gustavo Almeida.