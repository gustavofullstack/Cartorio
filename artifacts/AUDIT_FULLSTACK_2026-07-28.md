# Auditoria Fullstack de Producao — Cartorio

- Data: 2026-07-28
- Escopo: lint/type local, testes direcionados, endpoints de prod, Docker Swarm na VPS, logs 24h, recursos, Redis, Tailscale, higiene de secrets
- Modo: somente leitura. Nada foi modificado, reiniciado ou derrubado. Secrets mascarados (apenas nomes de variaveis).

## 1. Tabela de status por item

| # | Item | Resultado | Status |
|---|------|-----------|--------|
| 1a | Ruff (`app/ tests/`) | All checks passed (0 findings) | VERDE |
| 1b | Mypy (`app/`) | Success: no issues found in 230 source files | VERDE |
| 1c | Pytest subset (`pietra or emolumento or audit`) | Run 1: 3 failed / 824 passed. Run 2: 828 passed. Falhas flaky em `TestSanitizerGlitchRetryFlow` (2 testes) | AMARELO |
| 2 | Deprecations como erro (`test_pietra_inline_tool_calls.py -W error::DeprecationWarning`) | 13 passed — nenhum DeprecationWarning no caminho | VERDE |
| 3 | Endpoints prod | ver tabela abaixo | AMARELO |
| 4 | Docker services | 3 servicos degradados (0/1): `cartorio_supabase_realtime`, `vps_whoami` (crash loops); 4 servicos 0/0 (escalados a zero); `cartorio_system-api` com 5 restarts (exit 137) em ~3h | VERMELHO |
| 5 | Logs system-api 24h | 13 linhas de erro; padrao unico: LLM MONITOR providers offline | AMARELO |
| 6 | Traefik | Sem erros reais; apenas 404 de scanners de internet (wp-json, robots.txt) | VERDE |
| 7 | Disco/RAM | Disco 15% (165G livres); RAM 2.7G usada / 13.2G disponivel | VERDE |
| 8 | Redis (memory-cache) | hit rate 71.5% (7166 hits / 2850 misses); mem 7.62M | VERDE |
| 9 | Tailscale | VPS online; `agent-os` offline ha 1 dia | VERDE |
| 10 | Secrets hygiene | 1 secret real (`OPENCODE_GO_API_KEY`, prefixo `sk-j03K***`) commitado em 3 arquivos de doc em `infra/openclaw-agent/` | VERMELHO |

### 3. Endpoints de producao

| Endpoint | HTTP | Latencia | Nota |
|----------|------|----------|------|
| https://api.2notasudi.com.br/health | 200 | 0.06s | OK |
| https://api.2notasudi.com.br/ready | 200 | 0.06s | OK |
| https://api.2notasudi.com.br/api/v1/health/radar | 200 | 0.46s | OK |
| https://flow.2notasudi.com.br/ | 503 | 0.70s | `/healthz` retorna 200 — n8n UP; 503 apenas no path raiz |
| https://whatsapp.2notasudi.com.br/ | 200 | 0.64s | OK |
| https://agent.2notasudi.com.br/health | 404 | 0.30s | hermes UP ha 11h, mas rota /health nao existe (raiz tambem 404) |
| https://supbase.2notasudi.com.br/ | 503 | 0.05s | `/auth/v1/health` retorna 200; raiz sem backend (realtime em crash loop) |
| https://easypanel.2notasudi.com.br/ | 200 | 0.21s | OK |

## 2. Erros agrupados por padrao (system-api, ultimas 24h)

| Padrao | Count | Exemplo (mascarado) |
|--------|-------|---------------------|
| LLM MONITOR: Provider `opencode_go` OFFLINE (double failure) — [NETWORK] All connection attempts failed | 4 | Erro de rede ao chamar OpenCode-Go |
| LLM MONITOR: Provider `minimax` OFFLINE (double failure) — [NETWORK] All connection attempts failed | 4 | idem (monitor chama via OpenCode-Go) |
| Outros (traceback/critical/exception) | 0 | — |
| (filtrado) "identity leak interceptado" | presente, excluido conforme instrucao | — |

Sem PII nos trechos de erro.

### Crash loops identificados (VPS)

| Servico | Sintoma | Causa raiz (logs) |
|---------|---------|-------------------|
| `cartorio_supabase_realtime` (0/1) | Exited (1) a cada ~6s | `RuntimeError: Failed to detect IP version for DB_HOST: nxdomain` — DNS do DB_HOST nao resolve; `cartorio_supabase` (postgres:17) esta escalado 0/0 |
| `vps_whoami` (0/1) | Exited (2) repetido (~6 em 20 min) | Container sobe e morre; servico de teste/diagnostico |
| `cartorio_system-api` | 5 instancias Exited (137 = SIGKILL) entre ~12:50 e ~15:30 UTC; atual healthy | Exit 137 = kill externo (deploy/update ou healthcheck). Host sem pressao de memoria. Investigar se houve sequencia de deploys ou healthcheck agressivo |

Servicos 0/0 (escalados a zero, provavelmente aposentados — confirmar e remover): `cartorio_api`, `cartorio_evolution-api`, `cartorio_redis`, `cartorio_supabase`.

## 3. Deprecation warnings (suite, 8 warnings)

1. `datetime.datetime.utcnow()` deprecated — `tests/test_agendamento_b04.py:91`, `tests/test_protocolo_endpoint.py:73`
2. SQLAlchemy default datetime adapter deprecated (Python 3.12 + sqlite) — `tests/test_lgpd_direito_esquecimento.py` (3 testes)

Nenhum vira erro com `-W error::DeprecationWarning` no arquivo critico testado.

## 4. Riscos priorizados

### P0
- Nenhum bloqueador imediato: API principal (health/ready/radar) 200, n8n/auth/whatsapp operacionais, disco e RAM folgados.

### P1
1. **Secret real commitado em docs**: `OPENCODE_GO_API_KEY` com valor real (prefixo `sk-j03K***`) em:
   - `/Users/gustavoalmeida/Projetos/Cartorio/infra/openclaw-agent/workspace/TOOLS.md:76`
   - `/Users/gustavoalmeida/Projetos/Cartorio/infra/openclaw-agent/HTTP-API.md:122`
   - `/Users/gustavoalmeida/Projetos/Cartorio/infra/openclaw-agent/TROUBLESHOOTING_LOBECHAT_2026-07-14.md:41,51`
   Acao: rotacionar a chave e purgar do historico git.
2. **`cartorio_supabase_realtime` em crash loop (0/1)** — DB_HOST nxdomain; realtime/websockets do Supabase fora do ar. Acao: corrigir DB_HOST ou escalar `cartorio_supabase` (hoje 0/0), ou desativar o servico se nao usado.
3. **LLM providers `opencode_go` e `minimax` OFFLINE** (double failure, rede) — degradacao de fallback do LLM monitor. Acao: verificar conectividade VPS→OpenCode-Go e credenciais/endpoint.
4. **`cartorio_system-api` com 5 restarts exit 137 em ~3h** — servico flapping. Acao: correlacionar com deploys (Easypanel) ou revisar healthcheck/limits de memoria do servico.

### P2
1. **Testes flaky** `TestSanitizerGlitchRetryFlow::test_retry_persistente_faz_strip_da_sentenca` e `::test_retry_persistente_sem_util_cai_fallback` — falham na suite completa, passam isolados (3/3). Suspeita de poluicao de estado entre testes. Acao: isolar fixture/estado compartilhado.
2. **`agent.2notasudi.com.br/health` 404** — endpoint de health esperado nao existe no hermes. Acao: expor `/health` ou ajustar o contrato de monitoramento.
3. **`vps_whoami` crash loop** — servico de diagnostico; remover ou consertar.
4. **Deprecation warnings** de `datetime.utcnow()` em 2 arquivos de teste — migrar para `datetime.now(datetime.UTC)`.
5. **Servicos 0/0 residuais** (`cartorio_api`, `cartorio_evolution-api`, `cartorio_redis`, `cartorio_supabase`) — limpar stack para reduzir superficie e confusao operacional.
6. **`flow/` 503 no path raiz** (healthz 200) — comportamento do n8n; se o root e usado por uptime externo, apontar probe para `/healthz`.
7. **`agent-os` (Tailscale) offline ha 1 dia** — verificar se e esperado.

## 5. Acoes recomendadas (nao executadas)

1. Rotacionar `OPENCODE_GO_API_KEY` e remover valor literal dos 3 arquivos em `infra/openclaw-agent/` (+ `git filter-repo`/BFG se historico importa).
2. Corrigir `DB_HOST` do `cartorio_supabase_realtime` (ou escalar `cartorio_supabase` para 1, ou remover o servico realtime se obsoleto).
3. Diagnosticar falha de rede para OpenCode-Go a partir da VPS (DNS/egress/firewall) e validar credencial `OPENCODE_GO_API_KEY` no provider.
4. Investigar causa dos exit 137 do `cartorio_system-api` (`docker service ps`, eventos de deploy no Easypanel, limites de memoria do servico).
5. Tornar deterministicos os 2 testes flaky do glitch validator (revisar estado global/fixtures).
6. Adicionar rota `/health` no hermes (agent) ou corrigir probes externas.
7. Remover servicos 0/0 e `vps_whoami` da stack.
8. Trocar `datetime.utcnow()` por `datetime.now(datetime.UTC)` nos testes.
9. Apontar monitoramento de `flow.2notasudi.com.br` para `/healthz`.
