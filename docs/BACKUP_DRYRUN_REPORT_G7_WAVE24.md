# Backup Dry-Run Restore Sample — G7.08.T2 (Wave 24)

| Campo | Valor |
|-------|--------|
| **Task** | G7.08.T2 — Backup dry-run restore sample |
| **Wave** | G7 Wave 24 |
| **Data (UTC)** | 2026-07-17T11:48:39Z |
| **Agente** | cartorio-sre (slot A2) |
| **Escopo** | Dry-run **local** apenas — **sem SSH VPS**, **sem mutar produção** |
| **Status** | **[WORK] sample local** · **[HOLD-GUSTAVO] prod `/var/backups`** |

---

## 1. O que foi dry-run (script + passos)

### 1.1 Scripts e assets

| Asset | Path | Papel |
|-------|------|--------|
| Dry-run validator | `scripts/backup_dryrun.py` | Valida `.sql.gz` + restore simulado SQLite; `--tar-list` para bundle |
| Backup diário VPS | `infra/backup/cartorio-backup.sh` | `pg_dump -Fc` multi-DB + tar.gz + envs |
| Backup basebackup 4×/dia | `scripts/backup_postgres_a14.sh` | `pg_basebackup -Ft -z` → dirs em `/var/backups/postgres` |
| Report G6 (referência) | `docs/BACKUP_DRYRUN_REPORT_2026-07-16.md` | Sample minúsculo (<1KB) → HOLD size gate |

### 1.2 Passos executados (Wave 24)

1. **Fixture SQL sintética** (pg_dump-like, schema-qualified `public.*`) com as 8 tabelas canônicas + INSERT de demo (sem PII real).
2. Compactação `gzip` + sidecar `.sha256`.
3. **`python3 scripts/backup_dryrun.py <sample.sql.gz>`** — gates: size, magic gzip, SHA256, CREATE TABLE, tabelas canônicas, SQLite restore.
4. **Bundle tar.gz** no layout de `cartorio-backup.sh` + **`python3 scripts/backup_dryrun.py --tar-list <bundle.tar.gz>`**.
5. Tentativa **`--latest`** em `/var/backups/cartorio` no host local → **Permission denied** (esperado fora do VPS).
6. **Enhancement do script** (esta wave):
   - Parse de `CREATE TABLE public.tabela` / `"public"."tabela"` (pg_dump real).
   - Strip de schema + `DEFAULT now()` no caminho SQLite.
   - Flag `--tar-list` para bundles diários.
   - `PermissionError` em `--latest` vira mensagem **HOLD-GUSTAVO** (exit 2).

### 1.3 Comandos reproduzíveis

```bash
# Sample SQL.gz (fixture Wave 24 — path efêmero /tmp)
python3 scripts/backup_dryrun.py \
  /tmp/cartorio_backup_g7_wave24/full_backup_sample.sql.gz \
  --report /tmp/cartorio_backup_g7_wave24/auto_report.md

# Bundle estilo cartorio-backup.sh
python3 scripts/backup_dryrun.py \
  --tar-list /tmp/cartorio_backup_g7_wave24/cartorio_backup_sample.tar.gz

# Prod (somente no VPS, como root/cron user) — NÃO executado nesta wave
ssh cartorio 'python3 /path/to/scripts/backup_dryrun.py --latest --report /tmp/backup_dryrun_prod.md'
# ou
ssh cartorio 'ls -lah /var/backups/cartorio/*.sql.gz /var/backups/cartorio/*.tar.gz | tail -20'
```

---

## 2. Restore sample simulado local

### 2.1 SQL.gz (pg_dump plain + gzip)

| Check | Resultado |
|-------|-----------|
| Arquivo | `/tmp/cartorio_backup_g7_wave24/full_backup_sample.sql.gz` |
| Tamanho | **1201 bytes** (> 1KB gate) |
| Gzip magic `1f 8b` | **OK** |
| SHA256 sidecar | **MATCH** (`36b6da18659ebf4e…`) |
| CREATE TABLE | **8** |
| INSERT INTO | **8** |
| Tabelas canônicas | **8/8** (`cliente`, `protocolo`, `atendimento`, `documento`, `emolumento`, `audit_log`, `conversa`, `agendamento`) |
| SQLite in-memory restore | **8/8 CREATE aplicados** |
| Exit code | **0 [WORK]** |

### 2.2 Tar bundle (layout `cartorio-backup.sh`)

| Check | Resultado |
|-------|-----------|
| Arquivo | `/tmp/cartorio_backup_g7_wave24/cartorio_backup_sample.tar.gz` |
| Tamanho | **10582 bytes** |
| `tar -tzf` / `tarfile` list | **OK** (8 membros) |
| Dumps presentes | `supabase_{cartorio,n8n,chatwoot,evolution}_*.dump` |
| Envs / n8n JSON | presentes (sample) |
| Exit code `--tar-list` | **0 [WORK]** |

> **Nota**: dumps `-Fc` (custom format) **não** são re-importados no SQLite. O dry-run de bundle valida **integridade do envelope** (tar legível + artefatos esperados). Restore real de `-Fc` exige `pg_restore` no Postgres (critérios §3).

### 2.3 O que **não** foi feito (deliberado)

| Ação | Motivo |
|------|--------|
| SSH VPS / leitura `/var/backups/cartorio` | Auto-mode / wave rule: não SSH se falhar; host local `Permission denied` |
| `pg_restore` em prod ou staging | Mutação / risco de dados |
| Download de backup prod | PII + secrets em `.env` do bundle |
| S3 restore drill | Fora do escopo G7.08.T2 sample |

---

## 3. Critérios de sucesso — restore **prod**

Checklist para Gustavo (ou SRE com SSH autorizado) em janela de manutenção:

### 3.1 Pré-condições

- [ ] Backup mais recente em `/var/backups/cartorio/` com idade **≤ 24h** (cron 03:00).
- [ ] Sidecar SHA256 presente **ou** hash recalculado e registrado no ticket de restore.
- [ ] `scripts/backup_dryrun.py --latest` no VPS → exit **0** (para `.sql.gz` plain).
- [ ] Bundle `cartorio_backup_*.tar.gz`: `tar -tzf` lista `supabase_*.dump` + (ideal) n8n workflows.
- [ ] Espaço em disco ≥ **2×** tamanho do backup no volume alvo.
- [ ] Snapshot/volume atual preservado **antes** de qualquer `pg_restore` destrutivo.

### 3.2 Restore sample (staging / DB temporário — preferido)

```bash
# Exemplo: restore de dump custom (-Fc) em database descartável
docker exec -i cartorio_supabase.1.<task> \
  createdb -U admin restore_dryrun_$(date +%Y%m%d)

docker exec -i cartorio_supabase.1.<task> \
  pg_restore -U admin -d restore_dryrun_YYYYMMDD --no-owner --no-acl \
  < /var/backups/cartorio/supabase_cartorio_TIMESTAMP.dump

# Sanity
docker exec cartorio_supabase.1.<task> \
  psql -U admin -d restore_dryrun_YYYYMMDD -c "\dt"
docker exec cartorio_supabase.1.<task> \
  psql -U admin -d restore_dryrun_YYYYMMDD -c \
  "SELECT COUNT(*) FROM audit_log; SELECT COUNT(*) FROM cliente;"
```

**DoD sample prod-adjacent**:

| Critério | Meta |
|----------|------|
| `pg_restore` exit | 0 (warnings de owner/ACL aceitáveis com `--no-owner --no-acl`) |
| Tabelas canônicas | todas presentes |
| `audit_log` row count | > 0 se prod tinha tráfego |
| Hash chain audit | opcional: `scripts/audit_chain_verify.sh` no DB restaurado |
| Drop DB dryrun | limpar `restore_dryrun_*` após validação |

### 3.3 Restore full disaster (P0)

Seguir `docs/OUTAGE_RECOVERY_RUNBOOK.md` § rollback DB + ordem de serviços.  
Nunca restaurar dump em cima do volume vivo sem:

1. scale apps → 0  
2. backup do estado atual  
3. restore  
4. realinhar `DATABASE_URL` (Lesson 176 — DNS interno `cartorio_supabase`, não IP externo)  
5. scale 0→1 e smoke (`/health`, `/ready`, `/api/v1/health/radar`)

### 3.4 RTO/RPO de referência

| Item | Alvo operacional |
|------|------------------|
| RPO | ≤ 24h (backup diário 03:00); ideal ≤ 6h se basebackup 4× ativo |
| RTO sample dry-run | ≤ 30 min (VPS + DB temp) |
| RTO full stack | 1–2 h (runbook outage + restore) |

---

## 4. Gaps / HOLD-GUSTAVO

| ID | Gap | Owner | Ação |
|----|-----|-------|------|
| **H1** | Backup **real** em `/var/backups/cartorio` não validado nesta máquina (Permission denied / sem SSH) | Gustavo | SSH `cartorio` → `backup_dryrun.py --latest` + `--tar-list` no último bundle |
| **H2** | Cron VPS: confirmar que `cartorio-backup.sh` está em `/usr/local/bin` e `/etc/cron.d/cartorio-backup` aponta path **VPS** (não path Mac) | Gustavo / sre | `cat /etc/cron.d/cartorio-backup`; `ls -lt /var/backups/cartorio \| head` |
| **H3** | `cartorio-backup.sh` ainda referencia container `cartorio_supabase-db-1` e user `supabase_admin` — pode divergir do Swarm atual (`cartorio_supabase` / user `admin`, Lesson 176) | Gustavo | Alinhar nomes container/user no script prod |
| **H4** | Dumps `-Fc` sem dry-run de schema no SQLite | sre (follow-up) | Opcional: `pg_restore -l` list-only no VPS |
| **H5** | Report G6 (2026-07-16) falhou size gate (229 B) — **substituído** por sample Wave 24 ≥1KB | — | Encerrado para sample local |

### Mensagem operacional

```
[HOLD-GUSTAVO] G7.08.T2 — sample local WORK; falta dry-run no backup prod real em
/var/backups/cartorio no VPS (SSH + permissão root/cron). Não mutar prod nesta wave.
```

---

## 5. Diff relevante no validador (Wave 24)

Arquivo: `scripts/backup_dryrun.py`

- Regex de tabelas: schema-qualified (`public.cliente`).
- SQLite: strip schema, `DEFAULT now()` → `CURRENT_TIMESTAMP`, `NUMERIC(p,s)` → `REAL`.
- CLI: `--tar-list PATH`.
- `--latest`: trata `PermissionError` com HOLD explícito.

---

## 6. Cross-links

- `docs/BACKUP_DRYRUN_REPORT_2026-07-16.md` — dry-run G6 (sample <1KB)
- `docs/OUTAGE_RECOVERY_RUNBOOK.md` — recovery + rollback DB
- `docs/DATABASE_OPERATIONS.md` — ops Postgres
- `infra/backup/E6_S7_T10_setup.md` — setup cron backup
- `.harness/memory/lesson-176-sre-incident-2026-07-14-502-recovery.md` — drift de credenciais pós-restore
- `docs/adr/013-backup-mount-watchdog.md` — mount watchdog

---

## 7. Definition of Done (task)

| Item | Estado |
|------|--------|
| Sample restore simulado local (sqlite + tar list) | ✅ WORK |
| Report `docs/BACKUP_DRYRUN_REPORT_G7_WAVE24.md` | ✅ este arquivo |
| Script dry-run robusto a pg_dump real | ✅ enhanced |
| Dry-run backup prod VPS | ⏸ HOLD-GUSTAVO |
| Commit / push | ❌ não (regra wave) |

---

**Modified by Gustavo Almeida** — cartorio-sre G7 Wave 24 (G7.08.T2)
