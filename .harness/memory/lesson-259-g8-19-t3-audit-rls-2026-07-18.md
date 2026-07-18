# Lesson 259 — G8.19.T3 audit_log append-only com RLS (2026-07-18)

## Contexto

A tabela `audit_log` já possuía hash chain SHA256 + HMAC, mas o schema
Supabase mantinha policies `FOR ALL` para `service_role` e `authenticated`.
A aplicação tratava o log como append-only; o banco, porém, ainda aceitava
UPDATE/DELETE para roles privilegiadas. G8.19.T3 adiciona prevenção na
camada Postgres para reforçar os registros exigidos pela LGPD Art. 37.

## Descobertas

1. Os roles propostos `audit_create_role` e `audit_query_role` não existiam
   no schema. Os roles canônicos já disponíveis são `service_role` (backend)
   e `dpo` (consulta read-only), criados pela migration Supabase 0004.
2. A revision Alembic `0021` já estava ocupada pela G8.19.T2
   (`audit_log.hmac_kid`). A trava RLS precisou usar revision `0022`,
   encadeada em `0021`, para preservar um único head linear.
3. Uma policy `FOR UPDATE USING (false)` não constitui um deny absoluto
   quando existe outra policy permissiva `FOR ALL`: policies permissivas são
   combinadas com OR. As policies antigas precisaram ser removidas.
4. Policies `AS RESTRICTIVE` são combinadas com AND e funcionam como trava
   defensiva mesmo se alguém criar uma policy permissiva futura.
5. RLS não substitui privilégios SQL. Como o Supabase documenta
   `service_role` com `BYPASSRLS`, UPDATE/DELETE também precisam ser
   revogados no nível da tabela; BYPASSRLS não contorna `REVOKE`.
6. `FORCE ROW LEVEL SECURITY` inclui o table owner, mas superusers e roles
   com `BYPASSRLS` ainda exigem controles operacionais de break-glass.

## Decisão

A migration 0022:

- mantém `service_role` com SELECT/INSERT;
- mantém `dpo` com SELECT;
- revoga UPDATE/DELETE de `PUBLIC`, `anon`, `authenticated`,
  `service_role` e `dpo`;
- remove quatro policies amplas legadas;
- cria duas policies permissivas mínimas e duas policies restritivas de
  bloqueio;
- habilita e força RLS na tabela.

## Testes

Os seis cenários comportamentais dependem de Postgres real e usam
`AUDIT_RLS_TEST_DATABASE_URL`. Eles são marcados `integration`, portanto a
suite SQLite padrão permanece isolada. UPDATE e DELETE validam SQLSTATE
`42501`; SELECT, INSERT, `relrowsecurity` e `relforcerowsecurity` validam o
caminho permitido e os flags do catálogo.

## Lição reaproveitável

> Em PostgreSQL RLS, uma policy com predicado `false` não é uma regra DENY
> quando coexistem policies permissivas; audite e remova grants/policies
> amplos, use policies restritivas e valide o SQLSTATE com uma role real.

Aplicável a qualquer trilha append-only, ledger financeiro, outbox de
compliance, histórico de consentimento ou registro regulatório.

## Status

LGPD-REVIEW-PENDING. A migration não foi aplicada em produção.
