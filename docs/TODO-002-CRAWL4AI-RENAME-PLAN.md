# TODO-002 — Plano de Rename `cartorio_crwal4ai` → `cartorio_crawl4ai`

> **Status**: 📋 PLANO PREPARADO — NÃO EXECUTADO
> **Prioridade**: LOW (cosmético)
> **Gate**: aprovação Gustavo (PROMPT-2.json v2.0: "NENHUM commit sem aprovação prévia")
> **Data**: 2026-07-02
> **Lesson aplicada**: 290 (1 fix cirúrgico) + 116 (drift detection)

---

## 1. Contexto

O serviço `cartorio_crwal4ai` roda Swarm há várias turnas com typo `crwal` em vez de
`crawl`. O container em si está **healthy** (imagem `unclecode/crawl4ai:latest` amd64
— Easypanel trocou automaticamente de `:all-arm64` que crashava). A correção é só
**no nome do serviço Swarm**, não na imagem.

**Origem do typo** (lesson 123 brain): renomeações parciais em turnos anteriores
introduziram o typo em ambos os lados (JSON declarava `cartorio-crwal4ai`, Swarm usa
`cartorio_crwal4ai`).

**Risco real do rename**: BAIXO se feito com cuidado.
- Único consumer: nada no backend importa este serviço via DNS interno hoje
  (verificar antes de mover).
- Dependências externas: zero (apenas Traefik labels).
- Reversibilidade: alta (Swarm permite `docker service update --name`).

---

## 2. Análise de impacto — mapa categorizado das 24 ocorrências

Mapeei via `grep -rln "crwal4ai\|crawl4ai"` em todo o repo. Resultado:

### Categoria A — MANTER (memória/histórico, descrevem estado passado)

| Arquivo | Ocorrências | Razão para manter |
|---|---|---|
| `.brain/memory/2026-07-02.md` | 6 | Memória histórica Wave 0+2 (estado passado). Reescrever = falsificar histórico. |
| `.brain/memory/2026-07-02-auditoria-pos-deploy.md` | 2 | Auditoria pós-deploy já fechada. |
| `.brain/loop-state.json` | 3 | Lesson 123: `crwal4ai VXLAN`. Estado de lesson, não pode regredir. |
| `.harness/TASKS.md` | 1 | Linha 1342: task WAVE-2 marcada `[x]` (DONE). Reescrever = falsificar log. |

### Categoria B — RENOMEAR (referências futuras/operacionais)

| Arquivo | Linhas | Contexto |
|---|---|---|
| `docs/ARCHITECTURE.md` | 69, 142 | Diagrama C2 + tabela de serviços |
| `docs/SERVICE_INVENTORY.md` | 46, 113, 138, 207, 220, 299, 408 | Inventário operacional (mas notar TODO-002 no próprio doc) |

### Categoria C — JÁ CORRETO (`crawl4ai`)

| Arquivo | Linhas | Notas |
|---|---|---|
| `.secrets/MANIFEST.md` | 63, 84 | Já usa `crawl4ai` |
| `docs/PROMPTS-INDEX.md` | 24, 66, 84 | Mistura: v2.0 usa correto, estado Swarm ainda é typo |
| `docs/SPRINT_REVIEW_2026-07-02.md` | 27, 33, 72 | Histórico Wave 0-6 + backlog TODO-002 |
| `PROMPT-2.json` | 261, 404, 605 | Já usa `crawl4ai` correto |

---

## 3. Decisão proposta

**Ordem de execução** (cada fase = 1 commit separado, gated):

### Fase 1 — Docs internos (BAIXO RISCO, gated commit)
Renomear `crwal4ai` → `crawl4ai` em **Categoria B** (`docs/ARCHITECTURE.md` + `docs/SERVICE_INVENTORY.md`).
Adicionar nota: "⚠️ Swarm service name real ainda é `cartorio_crwal4ai` (TODO-002 fase 2)".

**Critério**: docs apontam nome correto; divergência declarada explicitamente.

### Fase 2 — Swarm rename (MÉDIO RISCO, gated execução humana)
Renomear o serviço Swarm via Easypanel UI ou CLI:

```bash
# Pré-rename — capturar estado
ssh vps-cartorio "docker service inspect cartorio_crwal4ai --pretty" > /tmp/crwal4ai-pre.json
ssh vps-cartorio "docker service logs cartorio_crwal4ai --tail 50" > /tmp/crwal4ai-pre.log

# Renomear (Easypanel UI: editar service name OU CLI:)
ssh vps-cartorio "docker service update --name cartorio_crawl4ai cartorio_crwal4ai"

# Traefik labels (se houver — verificar antes)
ssh vps-cartorio "docker service inspect cartorio_crawl4ai --format '{{ json .Spec.Labels }}'"
```

### Fase 3 — Pós-rename (BAIXO RISCO)
- [ ] `health_check_27services.sh` → 27/27 UP (substituir `crwal4ai` por `crawl4ai` no script)
- [ ] Buscar referências em outros serviços: `docker exec cartorio_api grep -r crwal4ai /app`
- [ ] Validar `curl http://cartorio_crawl4ai:11235/health` → 200
- [ ] Atualizar `docs/SERVICE_INVENTORY.md` linha 207 (tira nota "nome real é `cartorio_crwal4ai`")
- [ ] Atualizar `docs/SPRINT_REVIEW_2026-07-02.md` backlog (marcar TODO-002 DONE)

### Fase 4 — Limpeza de memória (CUIDADO)
- [ ] Adicionar lesson 292 ao MEMORY.md: "TODO-002 resolvido: cartorio_crwal4ai renomeado em DD/MM"
- [ ] **NÃO** editar `.brain/memory/2026-07-02*.md` (registro histórico)
- [ ] Atualizar `.brain/loop-state.json` removendo entrada `crwal4ai VXLAN fix` (se issue resolvida)

---

## 4. Script de migration Swarm (referência, NÃO executar)

```bash
#!/usr/bin/env bash
# rename-crwal4ai-to-crawl4ai.sh
# ATENÇÃO: requer aprovação Gustavo + janela de manutenção
set -euo pipefail

SERVICE_OLD="cartorio_crwal4ai"
SERVICE_NEW="cartorio_crawl4ai"

echo "[1/6] Pré-checks"
ssh vps-cartorio "docker service ls --filter name=${SERVICE_OLD} --format '{{.Name}} {{.Replicas}}'"
# esperado: "cartorio_crwal4ai 1/1"

echo "[2/6] Procurar dependentes"
ssh vps-cartorio "docker service ls --format '{{.Name}}' | xargs -I{} sh -c 'docker service inspect {} --format \"{{.Name}}: {{range .Spec.TaskSpec.Networks}}{{.Aliases}} {{end}}\" 2>/dev/null' | grep -i crwal4ai || echo 'nenhum dependente'"
# esperado: "nenhum dependente"

echo "[3/6] Backup config"
ssh vps-cartorio "docker service inspect ${SERVICE_OLD}" > "/tmp/${SERVICE_OLD}-backup-$(date +%Y%m%d-%H%M%S).json"

echo "[4/6] Rename (scale 0 → update → scale 1)"
ssh vps-cartorio "docker service scale ${SERVICE_OLD}=0"
sleep 5
ssh vps-cartorio "docker service update --name ${SERVICE_NEW} ${SERVICE_OLD}"
sleep 3
ssh vps-cartorio "docker service scale ${SERVICE_NEW}=1"

echo "[5/6] Pós-checks"
sleep 15
ssh vps-cartorio "docker service ls --filter name=${SERVICE_NEW} --format '{{.Name}} {{.Replicas}}'"
# esperado: "cartorio_crawl4ai 1/1"

echo "[6/6] Smoke test interno"
ssh vps-cartorio "docker exec cartorio_api curl -sf http://cartorio_crawl4ai:11235/health || echo 'WARN: smoke falhou'"
```

---

## 5. Critérios de aprovação (gate Gustavo)

Antes de qualquer execução, Gustavo deve confirmar:

- [ ] Janela de manutenção definida (sugestão: horário baixo, < 5min downtime)
- [ ] Backup recente do Supabase (`backup-2026-07-02-03h00` ou mais novo)
- [ ] Acesso SSH ao VPS-cartorio validado
- [ ] Easypanel UI acessível para rollback se necessário
- [ ] Aceita que **Fase 1** (docs) pode ser commit sem Fase 2 (Swarm) — divergência fica declarada

---

## 6. Critérios de sucesso (validação pós-execução)

| Critério | Comando |
|---|---|
| Swarm service existe com novo nome | `docker service ls \| grep cartorio_crawl4ai` |
| Replica 1/1 UP | `docker service ls --filter name=cartorio_crawl4ai` |
| Healthcheck responde | `curl -sf http://cartorio_crawl4ai:11235/health` |
| Sem consumer quebrado | `health_check_27services.sh --only-down` exit=0 |
| Nenhum serviço dependente reportando WARN | `health_check_27services.sh` exit=0 |

---

## 7. Rollback

Se algo der errado:

```bash
ssh vps-cartorio "docker service scale cartorio_crawl4ai=0"
ssh vps-cartorio "docker service update --name cartorio_crwal4ai cartorio_crawl4ai"
ssh vps-cartorio "docker service scale cartorio_crwal4ai=1"
```

Restauração de config: `docker service update --config-ref <backup-id> cartorio_crwal4ai`.

---

## 8. Lições aplicadas

- **Lesson 290**: 1 fix cirúrgico por chamada — Fase 1 (docs) é 1 commit. Fase 2 (Swarm) = chamada separada com aprovação.
- **Lesson 116**: drift detection — divergência docs-vs-Swarm registrada explicitamente durante Fase 1.
- **AGENTS.md § Security**: nenhum segredo envolvido (rename não toca .env).
- **PROMPT-2.json v2.0 § philosophy**: nenhuma execução sem aprovação prévia.

---

## 9. Próximos passos concretos

1. **AGORA**: Gustavo revisa este plano, decide se executa Fase 1 (docs only).
2. **PRÓXIMA SESSÃO** (se aprovado): executar Fase 1, commitar, validar.
3. **FUTURO** (se Fase 1 OK): agendar Fase 2 com janela de manutenção.
4. **ALTERNATIVA**: se Gustavo decidir NÃO renomear, basta fechar TODO-002 como "WONTFIX" no backlog.

---

**Mantido por**: ZCode/Mavis (cartorio-zcode agent)
**Modified by Gustavo Almeida** · 2026-07-02T19:30Z