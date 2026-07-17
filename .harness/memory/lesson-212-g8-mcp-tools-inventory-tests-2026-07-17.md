# Lesson 212 — G8.07.T1 MCP tools inventory tests (14 PASSED) (2026-07-17)

Type: project + reference

## Contexto

SUPER_PLANO_G8 (draft) squad 07 = MCP servers. T1 = "Testes de integração mockados para
todas as tools expostas no `mcp_server.py`". Wave 26 (lesson 198) reportou 13 tools MCP,
mas **nenhum teste unitário** validava esse inventário (risco: regressão silenciosa
se alguém remover/renomear tool).

## Entrega (Wave 30 A1)

`backend/tests/test_mcp_tools_inventory_g8.py` — **14 testes PASSED em 0.62s**.

| Classe | Testes | Cobre |
|--------|--------|-------|
| TestMCPInventory | 7 | module load + name canônico + version ≥0.6 + ≥13 tools + nomes únicos + sem empty + tools canônicos presentes |
| TestMCPAppMount | 2 | mcp_app() callable + retorna Starlette app |
| TestMCPSourceCode | 4 | sys.path setup + ImportError fallback + sem self-loop HTTP + docstring lista tools |
| TestMCPIntegration | 1 | count tools dentro margem Wave 26 snapshot [13-20] |

### Testes canônicos críticos (anti-regressão)

1. **test_canonico_tools_presentes** — garante que os 7 tools canônicos não somem:
   `cartorio_calcular_emolumento`, `cartorio_consultar_protocolo`, `cartorio_criar_protocolo`,
   `cartorio_gerar_segunda_via`, `cartorio_audit_verify`, `cartorio_saudacao`, `super_server_info`
2. **test_no_http_self_loop** — regex que detecta uso de `localhost:8000` em chamadas
   `httpx./requests./url=`, impedindo reintrodução do bug de recursão localhost
3. **test_tools_count_matches_wave26_snapshot** — count deve estar entre 13-20
   (margem para adições controladas, regression se cair)

## Validação gates pós-wave

| Gate | Antes (lesson 211) | Depois (Wave 30 A1) |
|------|--------------------|---------------------|
| pytest | 3191 | **3205** (+14) |
| mypy strict | 0/155 | 0/155 |
| ruff | 0 | 0 |

## Cross-refs

- lesson-211 (mega-commit 148 untracked)
- lesson-210 (g7_orchestrator tests Wave 29 A1)
- lesson-209 (Wave 29 closeout)
- lesson-198 (G7 Wave 26: MCP 13 tools + coding-vps 63 + WS ping 6)
- lesson-186 (G6 Wave 13 + SUPER_PLANO_G7)
- SUPER_PLANO_G8_100_TASKS.md Squad 07 (próximo: T2/T3/T4)

## Próxima wave (Wave 30 A2)

**G8.08.T2**: Criptografia de payload de webhooks falhos na tabela DLQ.
- Modifica `backend/app/services/dlq.py` para usar `app.services.crypto.encrypt()`
- Adiciona coluna `payload_encrypted` (BLOB ou BYTEA) ou usa TDE pgcrypto
- LGPD Art.46 (segurança) + Art.16 (eliminação segura pós-retention)
- Testes: encrypt/decrypt round-trip + DLQ insert/read com payload criptografado

Modified by Gustavo Almeida