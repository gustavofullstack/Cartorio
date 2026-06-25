# A14 — Backup DB 4x/dia (pg_basebackup + WAL)

## Status (2026-06-25 09:15 BRT)

**SQUAD A — A14 Backup DB — VERIFIED & CLOSED**

### VPS Install (verificado via SSH cartorio -> root@100.99.172.84)

Data/hora: 2026-06-25 09:08 BRT (2026-06-25 12:08 UTC)

Outputs:
```
=== 1. Install script to /usr/local/bin ===
-rwxr-xr-x 1 root root 4393 Jun 25 12:07 /usr/local/bin/pg_basebackup_4x.sh

=== 2. Validate bash syntax ===
OK - pg_basebackup_4x.sh syntax OK
OK - install_pg_backup_cron.sh syntax OK

=== 3. Run install_pg_backup_cron.sh (1a vez) ===
[install_pg_backup_cron] CRIANDO /etc/cron.d/cartorio-pgbase (primeira instalacao)
[install_pg_backup_cron] OK - cron instalado em /etc/cron.d/cartorio-pgbase
[install_pg_backup_cron] Agendamento: 0 */6 * * * (00:00, 06:00, 12:00, 18:00 UTC)

=== 4. Run install_pg_backup_cron.sh (2a vez — idempotente) ===
[install_pg_backup_cron] OK - /etc/cron.d/cartorio-pgbase ja existe com conteudo canonico (idempotente, sem mudancas)

=== 5. Confirmar cron file ===
-rw-r--r-- 1 root root 365 Jun 25 12:07 /etc/cron.d/cartorio-pgbase
--- CONTENT ---
# A14 — pg_basebackup 4x/dia (00:00, 06:00, 12:00, 18:00 UTC).
# Owner: cartorio-dev. Installed by install_pg_backup_cron.sh (idempotente).
# Logs: /var/log/cartorio-pgbase.log (vazio = OK).
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

0 */6 * * * root /usr/local/bin/pg_basebackup_4x.sh >> /var/log/cartorio-pgbase.log 2>&1
```

### Cron file install
- `/etc/cron.d/cartorio-pgbase` (root:root 0644, 365 bytes)
- Schedule: `0 */6 * * * root /usr/local/bin/pg_basebackup_4x.sh >> /var/log/cartorio-pgbase.log 2>&1`
- Idempotente: 2a execucao detecta conteudo canonico e skip

### Script install
- `/usr/local/bin/pg_basebackup_4x.sh` (root:root 0755, 4393 bytes)
- bash -n syntax: OK
- v1.1.0 (com banner S3 placeholder explicito)

### Commits existentes (3 commits A14)
- `23c5014` — chore(scripts): A14 backup postgres 4x/dia + WAL + S3 mensal
- `9cd2ca4` — docs(backup): A14 backup_postgres_a14 README
- `5502bc2` — feat(res): backup DB 4x/dia pg_basebackup + WAL + /api/v1/health/backup-v2

### Commit desta sessao (verify+close, NAO PUSHED)
- `a14-verify-and-close` — feat(obs): A14 verify+close (S3 placeholder + Prometheus metric + tests)

## Gates

| Gate                       | Status                | Evidence                                                            |
|----------------------------|-----------------------|---------------------------------------------------------------------|
| install_pg_backup_cron.sh  | DONE                  | SSH cartorio + output captured acima                                |
| S3 placeholder banner      | DONE                  | pg_basebackup_4x.sh banner + backend/.env.example AWS_* commented  |
| pytest                     | 20/20 PASS            | `uv run pytest tests/test_backup_v2.py tests/test_health_backup.py` |
| coverage backup_v2.py      | 92% (>90% gate)       | `--cov=app.services.backup_v2` (per-module)                         |
| Prometheus metric          | DONE                  | `backup_last_success_timestamp_seconds` gauge em metrics.py         |
| ruff check                 | PASS                  | `uv run ruff check` em 4 arquivos                                   |
| ruff format                | PASS                  | 4 files already formatted                                           |
| mypy                       | PASS                  | `Success: no issues found in 3 source files`                        |
| LGPD review                | N/A                   | Nenhuma mudanca em audit.py ou pii.py (regra Lesson 5/6)            |

## LGPD

- Backup NUNCA expoe PII em logs (apenas timestamps + paths de diretorios)
- Endpoint `/health/backup-v2` PUBLICO sem auth (apenas metadados de saude)
- Retencao 7d local (regra fora deste script para retencao cartorio 5y)
- DPA AWS pendente (Gustavo aciona via L1) — afeta apenas upload S3 mensal (placeholder)

## Pre-requisitos Gustavo (S3 upload mensal)

Para ativar upload S3 (1o dia do mes):
1. Criar bucket S3: `s3://cartorio-backups-prod/pgbase/`
2. Criar IAM user com policy minima de write nesse bucket
3. Exportar 4 vars no env do cron OU criar `/root/.aws/credentials`:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_S3_BUCKET`
   - `AWS_REGION` (default `sa-east-1`)
4. Instalar `aws-cli` no VPS: `apt install awscli`
5. Atualizar `#TODO Sprint 5` no `pg_basebackup_4x.sh` com `aws s3 sync ...`

Ate la, backup LOCAL (7d) segue 4x/dia normalmente e script loga
"SKIPPED (credenciais AWS nao configuradas)" todo dia 1o do mes
(LOGS em `/var/log/cartorio-pgbase.log`).

## Lesson canon (cross-project)

- `pg_basebackup -Ft -z -X stream -c fast` = RPO ~= 0 (WAL streaming incluso)
- Idempotencia via marker `.complete` em subdiretorio `YYYYMMDD_HH/`
  protege contra duplicacao se cron rodar 2x na mesma janela de 6h
- `0 */6 * * *` em UTC = 00, 06, 12, 18 UTC (cron NAO tem timezone configuravel
  no /etc/cron.d; verificar com `date -u` no VPS)
- Para upload S3 mensal, separar creds AWS do env do cartorio-api
  (script roda como root via cron, nao pega .env da app)

Modified by Gustavo Almeida
