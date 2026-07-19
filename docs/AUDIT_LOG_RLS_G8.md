# Audit Log RLS Locks — LGPD Art. 37 (G8.19.T3)

> **LGPD-REVIEW-PENDING** — Aguardar revisão do `cartorio-lgpd` antes de aplicar em produção.

A tabela `public.audit_log` é a fonte de prova do cumprimento da LGPD Art. 37
(registro de operações de tratamento de dados pessoais). Até a migration
`0021` (G8.19.T2 — `audit_log.hmac_kid`), a tabela já operava sob hash chain
SHA256 + HMAC, porém as Row Level Security policies existentes liberavam
`FOR ALL` para o role `service_role`. Esse arranjo permitia, em tese, que
qualquer script conectado com a credencial `service_role` executasse UPDATE
ou DELETE na tabela, o que esvaziaria a cadeia de auditoria e contradiz o
provimento CNJ 74/2018.

A migration `0022` corrige esse ponto de auditoria reforçando as travas no
banco de dados — a garantia de append-only deixa de depender apenas do
código Python e passa a ser imposta pelo próprio Postgres.

## Como funciona

A migration 0022:

1. `ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY` — habilita RLS.
2. `ALTER TABLE public.audit_log FORCE ROW LEVEL SECURITY` — RLS passa a
   vigorar também para o owner da tabela quando ele não possui `BYPASSRLS`.
   Superusers e roles `BYPASSRLS` permanecem restritos ao procedimento
   operacional de break-glass; os privilégios SQL de `service_role` ainda
   são limitados pelo `REVOKE`.
3. Revoga `UPDATE` e `DELETE` para todas as roles envolvidas (incluindo
   `service_role`).
4. Concede `SELECT` e `INSERT` para `service_role` e `SELECT` para `dpo`,
   suficiente para o pipeline FastAPI, `fn_auto_audit()` e relatórios ANPD.
5. Remove policies herdadas (`auth_all_audit_log`, `dpo_read_access`,
   `service_all_audit_log`, `service_role_full_access`).
6. Cria policies explícitas:
   - `audit_log_insert_policy` — `INSERT` para `service_role`.
   - `audit_log_select_policy` — `SELECT` para `service_role` e `dpo`.
   - `audit_log_no_update_policy` — `AS RESTRICTIVE FOR UPDATE TO PUBLIC
     USING (false) WITH CHECK (false)`.
   - `audit_log_no_delete_policy` — `AS RESTRICTIVE FOR DELETE TO PUBLIC
     USING (false)`.

Policies `AS RESTRICTIVE` são avaliadas em conjunto com qualquer policy
permitiva adicional. Mesmo que uma migration futura adicione, por engano,
uma policy permissiva para `UPDATE`/`DELETE`, a trava desta migration
permanece como cinturão final: SQLSTATE `42501` (insufficient privilege).

## Benefícios

- **Append-only enforced no DB layer.** `service_role` — a credencial usada
  pelo FastAPI — perde UPDATE/DELETE, então qualquer regressão que tente
  editar audit_log quebra em runtime com erro explícito.
- **Compatibilidade preservada.** `INSERT` continua funcionando para o
  trigger `fn_auto_audit()` e o `AuditService`; `SELECT` continua
  disponível para `/api/v1/audit/*` (DPO/escrevente) e `fn_audit_chain_verify`.
- **Compatibilidade com `FORCE ROW LEVEL SECURITY`.** O owner (que antes
  ignorava RLS) agora também passa a ser filtrado.
- **DDL repetível.** A migration remove as policies-alvo antes de recriá-las;
  `ALTER TABLE`, `GRANT` e `REVOKE` mantêm o mesmo estado quando repetidos.

## LGPD Art. 37 — mapeamento

| Requisito | Como esta migration atende |
|-----------|----------------------------|
| Registro de operações de tratamento | `INSERT` permitido (registro continua) |
| Integridade do registro (não alteração) | `UPDATE` bloqueado por policy RESTRICTIVE |
| Não eliminação antes da retenção | `DELETE` bloqueado por policy RESTRICTIVE |
| Acesso por DPO para relatório ANPD | `SELECT` permitido para `dpo` |
| Verificação periódica da cadeia | `fn_audit_chain_verify()` segue lendo |

## Compatibilidade com automações existentes

| Componente | Operação | Comportamento após 0022 |
|------------|----------|------------------------|
| `AuditService.log()` | INSERT | OK |
| `AuditService.verify_chain()` | SELECT | OK |
| `fn_auto_audit()` (trigger) | INSERT | OK |
| `/api/v1/audit/log` (POST) | INSERT | OK |
| `/api/v1/audit/replay` | SELECT | OK (DPO) |
| `fn_audit_chain_verify()` | SELECT | OK |
| `UPDATE`/`DELETE` por role operacional | UPDATE/DELETE | **BLOQUEADO** (SQLSTATE 42501) |

## Retenção: exclusão permanentemente vedada

`audit_log` não integra regras de retenção ou purge. A cadeia SHA256 + HMAC
deve ser preservada integralmente; uma eliminação intermediária torna a
verificação histórica incompleta. A migration Supabase
`2026_07_19_0001-audit-log-retention-guard.sql` cancela o cron legado
`retention-daily-03h` e instala um trigger que rejeita `UPDATE` e `DELETE`.
O script `scripts/lgpd_retention_job.py` também não aceita `audit_log` como
entidade. A rotina diária às 03:00 passa a somente verificar HMACs ausentes.

Essa defesa é complementar às policies RLS da migration 0022: o trigger
protege o caminho de retenção mesmo se ele usar uma conexão com privilégios
mais amplos. Não desabilite o trigger, nem use uma operação de rollback para
removê-lo; ambos exigem procedimento break-glass aprovado por LGPD.

## Operação de rollback

O `downgrade()` recria as policies permissivas legadas
(`auth_all_audit_log`, `dpo_read_access`, `service_all_audit_log` e
`service_role_full_access`) para que `alembic downgrade -1` restaure o
estado anterior, inclusive UPDATE/DELETE para `authenticated` e
`service_role`. Use somente para rollback controlado, pois ele remove a
proteção append-only introduzida pela migration 0022.

## Testes

`backend/tests/test_audit_log_rls_g8.py` contém 6 testes marcados
`@pytest.mark.integration`. Eles exigem Postgres real (SQLite não suporta
RLS nem o atributo `relforcerowsecurity`) e são excluídos por padrão da
suite unitária. Para rodar:

```bash
cd backend
AUDIT_RLS_TEST_DATABASE_URL=postgresql://user:pass@host:5432/db \
  uv run pytest -m integration tests/test_audit_log_rls_g8.py --no-cov -v
```

Os testes verificam:

1. `test_audit_log_select_succeeds` — `dpo` consegue ler audit_log.
2. `test_audit_log_insert_succeeds` — `service_role` insere normalmente.
3. `test_audit_log_update_blocked` — UPDATE retorna SQLSTATE 42501.
4. `test_audit_log_delete_blocked` — DELETE retorna SQLSTATE 42501.
5. `test_audit_log_rls_enabled` — `relrowsecurity = true`.
6. `test_audit_log_force_rls` — `relforcerowsecurity = true`.

## Status LGPD

LGPD-REVIEW-PENDING. Antes de aplicar em produção:

- Confirmar com `cartorio-dev` que nenhum job (retenção, anonimização,
  seeding) precisa de UPDATE/DELETE em audit_log.
- Confirmar com `cartorio-n8n` que nenhum workflow depende de mutate na
  tabela (todos os workflows devem apenas ler).
- Após review, Gustavo deve aplicar `alembic upgrade head` primeiro em
  staging, executar os 6 testes de integração e autorizar separadamente a
  aplicação em produção. Esta task não executa migrations remotas.

Modified by Gustavo Almeida
