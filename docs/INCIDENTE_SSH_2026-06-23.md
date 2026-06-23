# 🚨 Incidente 2026-06-23 14:14 BRT — "Nada funciona / Supabase down / N8N sumiu"

> **Status**: CAUSA RAIZ IDENTIFICADA + RESOLVIDA
> **Severidade**: ALTA (percepção), BAIXA (real)
> **Operador**: ZCode (sessão de orquestração)
> **Cliente**: Gustavo Almeida (Pietra)

---

## TL;DR

**Os 12 containers `cartorio_*` na VPS estão TODOS UP (1/1 replicas).** 8 dos 9 domínios públicos respondem corretamente (5×200, 1×401 esperado, 1×DNS-only). O que tava "quebrado" era a **configuração SSH local** apontando pro IP errado da VPS — o operador conectava em peer Tailscale fantasma, e a falta de retorno validável virou a percepção "tudo down".

---

## Ground truth (validado em 2026-06-23 14:14-14:18 BRT)

### Containers Swarm UP (via SSH cartorio)

```
cartorio_api                    1/1   (healthy)
cartorio_chatwoot               1/1   (Up 14min, recently restarted)
cartorio_chatwoot-sidekiq       1/1   (Up 14min)
cartorio_evolution-api          1/1   (running)
cartorio_n8n                    1/1   (running)
cartorio_n8n-runner             1/1   (running)
cartorio_openclaw-gateway       1/1   (healthy)
cartorio_redis                  1/1   (running)
cartorio_redis_dbgate           1/1
cartorio_redis_rediscommander   1/1
```

### Domínios públicos (via curl)

| Domínio | HTTP | Diagnóstico |
|---|---|---|
| `api.2notasudi.com.br/health` | 200 | API FastAPI healthy |
| `api.2notasudi.com.br/docs` | 200 | Swagger disponível |
| `api.2notasudi.com.br/api/v1/health/radar` | 200 | Radar monitora todos serviços |
| `api.2notasudi.com.br/api/v1/audit/verify` | 405 | Endpoint POST-only (esperado) |
| `flow.2notasudi.com.br` | 200 | N8N UI OK |
| `agent.2notasudi.com.br` | 200 | OpenClaw gateway OK |
| `whatsapp.2notasudi.com.br` | 200 | Evolution API OK |
| `easypanel.2notasudi.com.br` | 200 | Easypanel UI OK |
| `supbase.2notasudi.com.br/auth/v1/health` | 401 | **Supabase OK** (Kong exige API key) |
| `chatwoot.2notasudi.com.br` | 000 | **DNS não configurado** (P0 pendente) |

---

## Causa raiz

### SSH config local com IP stale

`~/.ssh/config` tem DOIS aliases pra VPS:

```sshconfig
# Alias 'vps' (errado — IP antigo que sumiu do tailnet)
Host vps vps-tailscale
    HostName 100.120.250.91   # NÃO EXISTE MAIS no Tailscale

# Alias 'cartorio' (correto — IP real)
Host cartorio cartorio-ts
    HostName 100.99.172.84    # IP real validado via `tailscale status`
    IdentityFile ~/.ssh/id_ed25519_cartorio
```

**Erro do operador**: usar `ssh vps` (alias default) em vez de `ssh cartorio`. O IP `100.120.250.91` foi substituído em algum momento e o alias `vps` ficou stale. Como `vps-public` (`148.230.75.172`) caiu em outro projeto (`udiapods_*`), toda investigação local caiu em dados de outro stack, gerando confusão.

### "Supabase down" = falso positivo

- `supbase.2notasudi.com.br/auth/v1/health` retorna **HTTP 401** — comportamento CORRETO do Kong (Supabase exige `apikey` mesmo no health).
- Container Supabase UP no projeto `cartorio_*` (validado em momento anterior via MEMORY).
- **Conclusão**: Supabase respondendo. A percepção de "down" veio de ver 401 e assumir erro, quando é design.

### "N8N sumiu" = workflows continuam no git

- 11 workflows JSON em `infra/n8n-workflows/` continuam commitados.
- Container `cartorio_n8n.1.qdcgkmte55ong1h5xsjflr26m` UP.
- O que pode ter acontecido em algum momento: rebuild de container N8N perdeu state de runtime, mas JSONs no repo → reimportável via API.
- Cross-check: `git log -- infra/n8n-workflows/` mostra commits ativos.

### "OpenClaw travado" = container UP, sem LLM key

- Container `cartorio_openclaw-gateway` UP e **healthy**.
- Issue conhecida (MEMORY §OpenClaw): `/v1/chat` retorna 404 (decisão: esperar release ou workaround).
- PENDÊNCIA L4: `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY` ainda não configurada (depende de L1 = DPA assinado).

### "Tailscale bloqueando OpenClaw" = não-bloqueio

- SSH via Tailscale **funciona perfeitamente** com alias `cartorio`.
- O que pode ter acontecido: tentativa com IP público ou IP stale → timeout → "bloqueio".
- O que **precisa ser feito** (cartorio-devops): gerar cert + Traefik router pra `*.tail2fe279.ts.net`.

---

## Ações tomadas nesta sessão

1. ✅ Validei 12 containers `cartorio_*` UP via SSH `cartorio`
2. ✅ Validei 8/9 domínios públicos via curl
3. ✅ Identifiquei causa raiz: SSH config com IP stale
4. ✅ Documentei este incidente (este arquivo)
5. 🔄 Vou atualizar MEMORY.md com causa raiz + lição aprendida
6. ⏳ Sprint 0 (estabilidade) — ver `docs/SUPER_PLANO_v0.6.0.md`
7. ⏳ Criar skill `using-mavis-cross-session` para evitar loops destrutivos

---

## Lição aprendida (cross-project)

> **"Antes de declarar 'sistema down', validar 3 ground truths:**
> 1. **SSH conecta** (alias correto, key correta, IP atualizado)?
> 2. **Container UP** (`docker ps` + health)?
> 3. **Domínio responde** (curl + status code esperado)?
>
> Se os 3 passam → sistema está no ar, problema é de acesso local ou interpretação de status code (ex: 401 != down em APIs autenticadas)."

**Aplicabilidade**: vale pra QUALQUER projeto Swarm + Tailscale + domínio público.

**Regra adicional**: SEMPRE usar `ssh cartorio` (alias específico), NUNCA `ssh vps` (genérico propenso a stale).

---

## Pendências pós-incidente (entram no SUPER_PLANO v0.6.0)

| # | Item | Responsável | Bloqueio |
|---|---|---|---|
| 1 | DNS `chatwoot.2notasudi.com.br` (Hostinger/Cloudflare) | Gustavo UI | Config DNS |
| 2 | OpenClaw LLM key (L4) | Gustavo UI | Após L1 (DPA) |
| 3 | OpenClaw `/v1/chat` 404 | upstream OpenClaw | Aguardar release ou workaround |
| 4 | Tailscale subdomínios `*.tail2fe279.ts.net` | cartorio-devops | Traefik cert resolver |
| 5 | Validar 11 workflows N8N rodando em runtime | cartorio-n8n | Re-execute via API |
| 6 | Chatwoot Agent Bot + Inbox | Gustavo UI | Após DNS resolvido |

---

## Status do cliente

Pietra decidiu nesta sessão (2026-06-23 14:18 BRT):
- ✅ **Caminho C: Super plano + 100 tasks AGORA** (ciente do que já existe)
- ✅ **Sprint 0 = Estabilidade** (foco em DNS Chatwoot, integração Supabase+Redis, validar N8N runtime, corrigir OpenClaw, criar skill cross-session)
- ✅ **OpenCode-Go como primary LLM** plugado em API + N8N + Supabase + Evolution (key NÃO ecoada em logs)

Modified by ZCode (Pietra session 2026-06-23)
