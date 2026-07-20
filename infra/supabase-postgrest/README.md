# Supabase REST compatibility layer

The production `cartorio_supabase` service is PostgreSQL/pgvector. This
PostgREST container exposes that database through the Supabase-compatible
`/rest/v1/*` surface at `https://supbase.2notasudi.com.br`.

Deployment facts (20 July 2026):

- image: `postgrest/postgrest:v12.2.12`
- database: `cartorio_supabase:5432/supabase`
- database schema cache: 223 relations, 25 functions
- Traefik strips `/rest/v1` before forwarding to PostgREST
- API health probes use `/rest/v1/`

Secrets are injected from the existing Docker service environment (`POSTGRES_PASSWORD`
and `JWT_SECRET`) and must never be stored in this repository. The container is
attached to the existing `cartorio_supabase_default` and `easypanel-cartorio`
networks so Traefik can resolve the `supabase-postgrest` alias.

This layer does not claim GoTrue/Auth, Storage, Realtime, or Edge Functions.
Those surfaces require separate services and must be validated independently
before being marked available.

Validation:

```bash
curl -fsS https://supbase.2notasudi.com.br/rest/v1/
curl -fsS 'https://supbase.2notasudi.com.br/rest/v1/audit_log?select=id&limit=1'
```
