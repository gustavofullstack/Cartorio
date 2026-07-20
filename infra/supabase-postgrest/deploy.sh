#!/usr/bin/env bash
set -euo pipefail

# Run on the VPS as root. Values are read from existing secret stores and are
# never echoed or committed.
db_pass="$(docker service inspect cartorio_supabase \
  --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}' \
  | awk -F= '$1 == "POSTGRES_PASSWORD" {print substr($0, index($0, "=") + 1)}')"
jwt_secret="$(grep '^JWT_SECRET=' /etc/easypanel/projects/cartorio/api/code/.secrets/supabase.env \
  | cut -d= -f2-)"
db_pass_encoded="$(printf '%s' "$db_pass" | python3 -c \
  'import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip(), safe=""))')"

docker rm -f cartorio_supabase_postgrest >/dev/null 2>&1 || true
docker run -d \
  --name cartorio_supabase_postgrest \
  --restart unless-stopped \
  --network cartorio_supabase_default \
  --network-alias supabase-postgrest \
  -e "PGRST_DB_URI=postgres://admin:${db_pass_encoded}@cartorio_supabase:5432/supabase" \
  -e PGRST_DB_SCHEMA=public \
  -e PGRST_DB_ANON_ROLE=anon \
  -e "PGRST_JWT_SECRET=${jwt_secret}" \
  -e PGRST_DB_MAX_ROWS=1000 \
  postgrest/postgrest:v12.2.12 >/dev/null

docker network connect --alias supabase-postgrest easypanel-cartorio cartorio_supabase_postgrest
echo "PostgREST started; validate /rest/v1/ without printing credentials."
