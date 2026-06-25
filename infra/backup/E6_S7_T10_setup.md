# E6.S7.T10 — Setup cron `cartorio-backup-status` (hourly)

**Task**: `E6.S7.T10` (do `.harness/TASKS.md` linha 432)
**Status**: 2026-06-25 — código versionado, deploy na VPS pendente
**Owner**: `cartorio-highspeed` (per TASK.md) ou Gustavo

## Objetivo

Cron hourly que consulta `/api/v1/health/backup` e envia alerta Telegram quando `ok=false`.

Complementa o cron `cartorio-backup.sh` (daily 03:00) com monitoramente mais frequente (hourly), reduzindo MTTR (Mean Time To Recovery) para falhas de backup.

## Instalação

### Pré-requisitos

```bash
# Dependências do script
apt install curl jq

# Diretórios de runtime (devem existir)
mkdir -p /var/log/cartorio-backup-status /var/lib/cartorio-backup-status
```

### Variáveis de ambiente

Criar `/etc/cartorio-backup/cartorio-backup-status.env` (chmod 600):

```bash
# API endpoint
CARTORIO_API_URL=https://api.2notasudi.com.br

# API key (validar que tem permissao de leitura em /health/backup)
# Pode ser a mesma CARTORIO_API_KEY de outros servicos
CARTORIO_API_KEY=<cole-aqui>

# Telegram (opcional - sem isso, so loga)
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_CHAT_ID=<chat-id>
```

### Deploy do script

```bash
# Copiar script
sudo cp infra/backup/cartorio-backup-status.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/cartorio-backup-status.sh

# Copiar cron file
sudo cp infra/cron/cartorio-backup-status /etc/cron.d/
sudo chmod 644 /etc/cron.d/cartorio-backup-status
```

### Ativar

```bash
# Reiniciar cron daemon
sudo systemctl restart cron

# Verificar que o job foi carregado
sudo systemctl status cron
grep cartorio-backup-status /var/log/syslog  # ou /var/log/cron
```

## Teste manual

```bash
# Test dry-run (NAO envia Telegram)
CARTORIO_API_KEY=test \
CARTORIO_API_URL=https://api.2notasudi.com.br \
TELEGRAM_BOT_TOKEN=test \
TELEGRAM_CHAT_ID=test \
/usr/local/bin/cartorio-backup-status.sh --dry-run

# Verificar log
tail -20 /var/log/cartorio-backup-status.log

# Verificar state
cat /var/lib/cartorio-backup-status/last_status.json | jq
```

## Uninstall

```bash
sudo rm -f /etc/cron.d/cartorio-backup-status
sudo rm -f /usr/local/bin/cartorio-backup-status.sh
sudo rm -rf /var/lib/cartorio-backup-status
# Manter /var/log/cartorio-backup-status.log para auditoria
sudo systemctl restart cron
```

## Integração com E1.S4.T2

Este cron depende do endpoint `/api/v1/health/backup` ter `source: "status_json"` ou `source: "local_path"` funcionando (ver E1.S4.T2 em `.harness/TASKS.md`).

Se a VPS ainda não tem:
1. `backup.sh` escrevendo `/var/log/cartorio-backup-status.json` OU
2. `/var/backups/cartorio` montado no container cartorio_api

...então `ok=false` será reportado hourly (mas SEM ser false positive — o cron enviará alerta correto: "Backup FAIL").

## Saídas (outputs)

### Sucesso (ok=true, age recente)

Log:
```
[2026-06-25T17:00:00Z] [INFO] Iniciando check (DRY_RUN=false)
[2026-06-25T17:00:00Z] [INFO] Consultando https://api.2notasudi.com.br/api/v1/health/backup
[2026-06-25T17:00:00Z] [INFO] HTTP 200
[2026-06-25T17:00:00Z] [INFO] ok=true age_hours=4.2 source=status_json
[2026-06-25T17:00:00Z] [INFO] Backup OK (age=4.2h)
```

Exit code: `0`

### Falha (ok=false ou age > 26h)

Log:
```
[2026-06-25T17:00:00Z] [INFO] Iniciando check (DRY_RUN=false)
[2026-06-25T17:00:00Z] [INFO] ok=false age_hours=48.0 source=status_json
[2026-06-25T17:00:00Z] [ERROR] Backup FAIL
[2026-06-25T17:00:00Z] [INFO] Telegram alert enviado: 🚨 Backup FAIL...
```

Telegram message (HTML):
```
🚨 Backup FAIL

Status: ok=false
Age: 48h
Source: status_json
```

Exit code: `1` (cron marca como erro, mas nao para o proximo run)

### Testes automatizados

```bash
cd backend
uv run pytest tests/test_setup_backup_status_cron_e6_s7_t10.py --no-cov -v
```

6 testes cobrem:
- Script existe em `infra/backup/`
- Script tem curl + endpoint + jq parser
- Cron file existe em `infra/cron/`
- Cron schedule é hourly
- Setup doc existe
- Referência em PENDENCIAS_SUI + MEMORY.md

Modified by ZCode/Mavis + Gustavo Almeida (2026-06-25)
