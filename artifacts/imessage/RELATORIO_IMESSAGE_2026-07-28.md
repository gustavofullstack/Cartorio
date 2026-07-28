# RELATÓRIO iMESSAGE — 2026-07-28 (00:20–00:45 BRT)

Executor: ZCode (sessão local Mac) · Agente: PIETRA · MiniMax-M3 1M XMax
Método: evidence-first. Nada marcado PASS sem evidência direta.

---

## 1. Pré-checks

| # | Item | Status | Evidência |
|---|------|--------|-----------|
| 1 | `hermes gateway list` → profile `cartorio` ativo | **PASS** | `✓ cartorio — PID 730` |
| 2 | `lsof -i :8793` → Photon sidecar vivo | **PASS** | `node PID 751 LISTEN localhost:8793` + conexão ESTABLISHED c/ PID 730 |
| 3 | `launchctl list` → label exato | **PASS** | `730  0  ai.hermes.gateway-cartorio` |
| 4 | Sem 2º consumer no mesmo PHOTON_PROJECT_ID | **PASS** | sidecar 751 (cartorio) = projeto `438527e1-…`; sidecar 1166 (default) = projeto `bcdcc0f7-…` — projetos distintos |
| 5 | SOUL.md com nome exato da tool | **PASS c/ ressalva** | `~/.hermes/profiles/cartorio/SOUL.md:23` cita `cartorio_calcular_emolumento` (`mcp__cartorio__cartorio_calcular_emolumento`). Ressalva: ver Gap G2 |
| 6 | `HERMES_GATEWAY_BUSY_ACK_ENABLED=false` + display photon limpo | **PASS** | env do PID 751 tem `HERMES_GATEWAY_BUSY_ACK_ENABLED=false`; `config.yaml:127-133` photon: `tool_progress:"off"`, `interim_assistant_messages:false`, `busy_ack_detail:false`, `busy_steer_ack_enabled:false`, `streaming:false`, `show_reasoning:false` |
| 7 | `PHOTON_ALLOW_ALL_USERS` / `ALLOW_ALL_INBOUND` | **FINDING** | env do PID 751: `PHOTON_ALLOW_ALL_USERS=true`. A linha está aberta a qualquer remetente. Pode ser intencional (canal público do cartório), mas precisa de decisão explícita do Gustavo — ver Gap G4 |

## 2. Estado do código (working tree)

- `backend/app/services/cartorio_agent.py`: **sem diff** — retry envelope 3×20s já commitado (estado do super prompt de 27/07 estava desatualizado).
- `backend/tests/test_retry_envelope_3x20s.py`: **15/15 PASS** (27,9s) via `make -C backend test-one`.
- Working tree dirty apenas com docs/memória (`.harness/memory/MEMORY.md`, `GOALS.md`, `STATUS.md`, `docs/DEAD_CODE_AUDIT_2026-07-28.json`, `.brain/memory/2026-07-28.md`).

## 3. Verificação MCP live (prova de transporte + autoridade)

Executado contra produção, com chave do profile `.env` (não reproduzida aqui):

| Etapa | Resultado | Evidência |
|-------|-----------|-----------|
| `POST /mcp` sem auth | 307 → `/mcp/` → **401** | rota Traefik existe (Lesson 282 superada — fix de 27/07 23:14 confirmado) |
| `initialize` c/ auth | **200** | server `cartorio-mcp-cabuloso v0.6.0`, protocol 2025-03-26 |
| `tools/list` | **14 tools** `cartorio_*` | inclui `cartorio_calcular_emolumento` |
| `tools/call calcular_emolumento(tipo=autenticacao, folhas=1)` | **200** | retornou `total: "28.90"`, `tabela_referencia: "TABELA_2026_MG"` |
| Gateway registra MCP no boot | OK | `agent.log` 00:33: `MCP server 'cartorio' (HTTP): registered 19 tool(s)` |

## 4. ⚠️ DESCOBERTA P0 — Tabela de emolumentos do backend É PLACEHOLDER E ESTÁ ERRADA

Fonte oficial: `backend/data/fontes/cpo86642025.pdf` = **Portaria CGJ/TJMG nº 8.664/2025** (DJe 18/12/2025, vigência 01/01/2026).
SHA-256: `84781a023d6d51d9cf68a4d2ecd0c78b7fa3b0c04ba800be4d7e085aa7173417`
Colunas oficiais: Emolumentos | TFJ | **Valor Final ao Usuário**.

| Ato | PDF oficial (valor final) | Backend `emolumento.py` | SOUL.md | Veredito backend |
|-----|--------------------------|-------------------------|---------|------------------|
| Autenticação de cópia (folha) | 8,55 + 2,66 = **11,21** | **28,90** | 11,21 | ❌ ERRADO (+158%) |
| Reconhecimento de firma | 8,55 + 2,66 = **11,21** | **32,10** | 11,21 | ❌ ERRADO (+186%) |
| Procuração genérica | 52,43 + 16,51 = **68,94** | **156,40** | 68,94 | ❌ ERRADO (+127%) |
| Testamento público | 332,64 + 104,60 = **437,24** | (não suportado) | 437,24 | — |
| "28,90" no PDF oficial | — | — | — | **valor não existe na Portaria** (grep zero ocorrências) |

Raiz: `backend/app/services/emolumento.py:51` — comentário literal do código:
`# Tabela placeholder - MG 2026 (substituir por carga real do estado)` + `# TODO Gustavo` na linha 66.

**O MCP tool que o T2 obriga chamar está servindo valores placeholder inflados para clientes reais, com selo `TABELA_2026_MG` e `valido_ate: 2026-12-31`.** O SOUL.md (memorizado) é quem está correto.

Expectativa do super prompt (autenticação = R$ 8,55 + TFJ): **CONFIRMADA pelo PDF** — e o backend está errado, não o prompt.

## 5. Resultados T0–T8

| Teste | Status | Evidência / motivo |
|-------|--------|--------------------|
| **T0** Identity | **PASS (probe local)** | `hermes --profile cartorio -z "Oi, quem é você?"` → *"Sou a Pietra, a agente do 2º Tabelionato de Notas de Uberlândia…"* — zero leak Hermes/modelo, zero emoji. Falta confirmação no iPhone |
| **T1** Menu institucional | **SKIP** | requer turno no dispositivo real |
| **T2** Emolumento c/ tool call | **FAIL_FUNCTIONAL (probe local)** | `hermes -z "Quanto custa uma autenticação?"` respondeu **R$ 28,90 de memória** sem tool call (toolset `mcp-cartorio` não existe no contexto CLI — "ignoring unknown --toolsets entries"). Agravante: 28,90 bate com o backend placeholder **errado** — modelo provavelmente absorveu o valor errado em sessões anteriores. No gateway photon a tool ESTÁ registrada (ver §3), mas o valor que ela serve é errado (ver §4). **T2 não pode PASS enquanto o backend servir placeholder** |
| **T3** Borda isenção/urgência | **SKIP** | requer dispositivo real |
| **T4** PII scrub | **SKIP** | requer dispositivo real |
| **T5** Protocolo DRAFT/HITL | **SKIP** | requer dispositivo real |
| **T6** Anti-leak UX | **PASS (config)** | flags photon todas em off/false (pré-check 6). Falta validação empírica no iPhone |
| **T7** Retry/timeout | **PASS (unitário)** | 15/15 testes do retry envelope 3×20s. Sem teste de caos em runtime |
| **T8** Round-trip + evidência | **BLOCKED** | requer iPhone físico do Gustavo. Último inbound real: `2026-07-28 00:22:48` de `+553****0250` (corpo vazio `￼` — anexo/reação) |

**Bônus — bug de saudação:** no probe T2 (00:35 BRT) a Pietra abriu com **"Boa tarde"**. Regra do SOUL.md: 18:00–04:59 → "Boa noite". MiniMax não está recebendo/aplicando o relógio BRT.

## 6. Evidências (artefatos)

- Fixture oficial: `backend/data/fontes/cpo86642025.pdf` (SHA-256 acima)
- Extração: `pdftotext -layout` → `/tmp/cpo8664.txt` (linhas 85, 139, 159-160)
- Logs gateway: `~/.hermes/profiles/cartorio/logs/{gateway,agent}.log`
- MCP responses capturados nesta sessão (initialize/tools-list/tools-call) — transcripts na sessão
- Testes: `make -C backend test-one TEST=tests/test_retry_envelope_3x20s.py` → 15 passed

## 7. Gaps restantes

- **G1 (P0):** `EMOLUMENTOS_2026` placeholder em produção. Corrigir `emolumento.py` com os valores da Portaria 8.664/2025 (incl. faixas de escritura por valor — Tabela 1 item 4b), ajustar testes `t043/t044/t045`, redeploy `cartorio_api`. Sem isso, T2 FAIL estrutural.
- **G2 (P1):** Divergência de autoridade — SOUL.md memorizado (correto) vs MCP tool (errada). Após G1, alinhar e manter regra "tool é a fonte; memória é cache".
- **G3 (P2):** Saudação contextual quebrada (Boa tarde às 00:35). Injetar horário BRT no contexto ou remover saudação automática.
- **G4 (decisão):** `PHOTON_ALLOW_ALL_USERS=true` — confirmar se linha é pública por design.
- **G5 (P2):** Sidecar com churn de re-subscribe a cada ~2min (`inbound stream ended — re-subscribing`) + restart do gateway 00:32–00:33 (`stdin EOF (parent exited)`). Investigar estabilidade antes da bateria no iPhone.
- **G6 (higiene):** `MCP_CARTORIO_API_KEY` (JWT) existe em plaintext em `~/.hermes/profiles/cartorio/.env` e `.env.bak-*` — esperado localmente, mas evitar eco em logs/sessões.

## 8. Próxima ação recomendada

1. **Gustavo decide:** corrigir tabela placeholder agora (task nova `E_.S_.T_` com testes de borda + review) **antes** de qualquer bateria T0–T8 no iPhone — testar preço contra backend errado só gera evidência de erro.
2. Após fix + redeploy: re-prova MCP (`tools/call` autenticacao → esperado `11.21`).
3. Então: bateria T0–T8 no iPhone físico (checklist do super prompt), com atenção especial a T2 (tool call real) e T6 (zero leak).
4. Investigar G5 (churn sidecar) em paralelo.

---
*Gerado por ZCode em 2026-07-28 00:45 BRT. Nenhum secret reproduzido neste relatório.*
