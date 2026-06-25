# Crons do Cartório 2º Notas

## Instalação

```bash
# Copiar crons para o diretório do sistema
sudo cp infra/cron/cartorio-* /etc/cron.d/
sudo chmod 644 /etc/cron.d/cartorio-*
sudo systemctl restart cron

# Copiar scripts
sudo cp infra/monitoring/*.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/*.sh
```

## Crons configurados

| Arquivo | Frequência | Descrição |
|---------|-----------|-----------|
| `cartorio-backup-status` | Hourly | Verifica status do backup via API |
| `cartorio-health-check` | 5min | Health check de todos os serviços |

## Scripts

| Script | Descrição |
|--------|-----------|
| `health_check_all.sh` | Testa 8 serviços + Telegram alert |
| `monitor_services.sh` | Monitoramento contínuo |
| `backup_n8n.sh` | Exporta workflows N8N via API |
| `deploy_api.sh` | Deploy automatizado da API |
