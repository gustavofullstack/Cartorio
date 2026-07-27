#!/usr/bin/env bash
# Sincroniza os artefatos de backup mais recentes para storage S3 compatível.
# Credenciais são fornecidas somente pelo secret manager/role da VPS.

set -euo pipefail

backup_root="${BACKUP_ROOT:-/var/backups/cartorio}"
bucket="${AWS_S3_BUCKET:-}"
region="${AWS_REGION:-}"
prefix="${OFFSITE_BACKUP_PREFIX:-cartorio}"
encryption="${AWS_S3_SSE:-AES256}"

fail() {
  printf 'OFFSITE_BACKUP=BLOCKED %s\n' "$1" >&2
  exit 2
}

[[ -n "${bucket}" ]] || fail 'AWS_S3_BUCKET ausente'
[[ -n "${region}" ]] || fail 'AWS_REGION ausente'
command -v aws >/dev/null 2>&1 || fail 'aws CLI ausente'

logical_backup=$(find "${backup_root}" -maxdepth 1 -type f -name 'cartorio_backup_*.tar.gz' \
  -printf '%T@ %p\n' | sort -rn | head -n 1 | cut -d' ' -f2-)
[[ -n "${logical_backup}" ]] || fail 'backup lógico ausente'

pgbase_dir=$(find "${backup_root}/pgbase" -mindepth 1 -maxdepth 1 -type d \
  -exec test -f '{}/.complete' \; -printf '%T@ %p\n' 2>/dev/null \
  | sort -rn | head -n 1 | cut -d' ' -f2-)
[[ -n "${pgbase_dir}" ]] || fail 'backup físico ausente'

upload() {
  local source="$1"
  local destination="$2"
  aws s3 cp --only-show-errors --region "${region}" --sse "${encryption}" \
    "${source}" "${destination}"
}

logical_destination="s3://${bucket}/${prefix}/logical/$(basename "${logical_backup}")"
pgbase_destination="s3://${bucket}/${prefix}/pgbase/$(basename "${pgbase_dir}")/"

upload "${logical_backup}" "${logical_destination}"
aws s3 sync --only-show-errors --region "${region}" --sse "${encryption}" \
  "${pgbase_dir}/" "${pgbase_destination}"

# Garante que pelo menos o objeto lógico pode ser localizado sem imprimir metadados.
aws s3api head-object --bucket "${bucket}" \
  --key "${prefix}/logical/$(basename "${logical_backup}")" >/dev/null
printf 'OFFSITE_BACKUP=PASS\n'
