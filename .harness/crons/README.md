# Crons ZCode — Rotinas automáticas do orquetrador

> Cada cron é uma **rotina documentada** que ZCode/Mavis executa automaticamente
> ao abrir nova sessão ou em pontos de verificação. NÃO são crons de SO (cron
> do Linux) — são checklists de saúde do projeto.

## Por que este arquivo existe

O briefing do Gustavo pediu "CRONS" mas sem credenciais SSH eu não posso
instalar crons de SO na VPS. O que eu POSSO fazer é:

1. Documentar as rotinas que DEVEM rodar
2. Configurar alarmes/lembretes pra cada sessão
3. Deixar pronto o script pra Gustavo instalar via SSH quando puder

## Crons (4 rotinas)

### 1. `daily-coverage` — a cada sessão
**Trigger:** abertura de qualquer sessão ZCode no projeto Cartório
**Ação:**
```bash
cd backend && source .venv/bin/activate
python -m pytest 2>&1 | tail -3
```
**Critério:** 199+ tests passando, coverage ≥ 90%
**Se falhar:** PARAR tudo e investigar. Não commitar nada.

### 2. `weekly-audit-cleanup` — checar ADR-013
**Trigger:** ao final de cada semana (verificar com `git log --since="7 days ago"`)
**Ação:**
```bash
# Se houver restart do cartorio_api nos ultimos 7 dias
docker service ps cartorio_cartorio_api --filter "desired-state=running"
# Verificar se mount /var/backups/cartorio ainda esta binded
docker service inspect cartorio_cartorio_api --format '{{ json .Spec.TaskTemplate.ContainerSpec.Mounts }}'
```
**Critério:** mount backup presente. Se sumiu, ADR-013 watchdog deveria ter
re-aplicado; se nao re-aplicou, tem bug no watchdog.
**Ação corretiva:** `docker service update --mount-add type=bind,source=/var/backups/cartorio,target=/var/backups/cartorio,readonly cartorio_cartorio_api`

### 3. `sprint-board` — toda sessão que termina
**Trigger:** antes de commitar `SESSION_SUMMARY` ou `progress-audit`
**Ação:** ler `.harness/TASKS.md` e listar:
- Tasks Sprint 3 done desde a última sessão
- Tasks ainda abertas
- SUI que Gustavo precisa fechar
- Bugs P0 com ADR pronto mas fix não aplicado

**Output:** atualizado em `docs/sessions/YYYY-MM-DD-progress-audit.md`

### 4. `pii-leak-sweep` — antes de qualquer merge em `master`
**Trigger:** pre-commit hook (se GitHub Actions existir) ou manual
**Ação:**
```bash
# Garante que nenhum CPF/RG/telefone/email em texto puro caiu em log ou response
grep -rE "[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}" backend/app/ \
  --include="*.py" | grep -v "test_" | grep -v "# exemplo"
# Deve retornar 0 matches
```
**Critério:** 0 matches fora de testes ou comentários de exemplo
**Ação corretiva:** se vazou, aplicar scrub do `app/services/pii.py`

## Como instalar no SO (quando Gustavo puder)

SSH na VPS:
```bash
# Cria usuario restrito pra cron
sudo useradd -r -s /bin/bash cartorio-cron

# Diretorio de scripts
sudo mkdir -p /opt/cartorio/crons
sudo chown cartorio-cron:cartorio-cron /opt/cartorio/crons

# Script de coverage diaria
cat > /opt/cartorio/crons/daily-coverage.sh <<'EOF'
#!/bin/bash
cd /opt/cartorio/Cartorio/backend
source .venv/bin/activate
pytest 2>&1 | tee /var/log/cartorio/coverage-$(date +%F).log
EOF

# Crontab
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/cartorio/crons/daily-coverage.sh") | crontab -
```

## Por que NAO instalei agora

Não tenho SSH na VPS 100.99.172.84. Instalar crons via SSH é tarefa SUI.
Este arquivo é o "como instalar" pra quando Gustavo puder fazer.
