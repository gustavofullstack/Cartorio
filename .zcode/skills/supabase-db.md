# Skill: Supabase Database Management
## Purpose
Manage Supabase PostgreSQL database.
## URL
- https://supbase.2notasudi.com.br
- Studio: https://supbase.2notasudi.com.br:3000
- Health: GET /auth/v1/health
## Database (cartorio)
- Tables: 134
- Core Tables: 13 (clientes, conversas, protocolos, documentos, emolumentos, atendimentos, agendamentos, audit_log, outbox_messages, webhook_events, lgpd_consents, lgpd_audit_anpd, workflow_publication_outbox)
- RLS: 14 tables with row-level security
- Functions: 60 custom functions
- Audit Log: 809+ entries
- Alembic: v0016
## Key Functions
- fn_audit_chain_verify: Audit chain integrity
- fn_auto_audit: Auto-insert audit_log
- fn_set_updated_at: Updated_at trigger
- notify_outbox_new: pg_notify for outbox
- criar_protocolo: Protocol creation
- lgpd_consent_webhook: LGPD consent processing
- decrypt_pii / encrypt_pii: PII encryption
## Cron Jobs: 5 active
## Vault: 8 entries
## Webhooks: 3 (outbox/protocolo/consent)
## Realtime: 5 channels
