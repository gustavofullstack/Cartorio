# LOOP INFINITO — Goals · Meta · Objetivo · Progresso · Cron (multi-agent 24/7)

**Owner:** Gustavo Almeida · **Modo:** YOLO total · **Sessão:** 2026-07-03 (Madrugada)
**Operador:** TRAE · M3/M2.7-High-Speed · minimax.io · coding-plan-minimax
**Foco:** Cartório 100% production-ready, multi-canal Telegram + WhatsApp + Web + Chatwoot, LGPD ANPD-ready, auto-retomar sem perguntar.

---

## 1. RESUMO

Ativar **loop contínuo autônomo 24/7** que orquestra o time multi-agent do projeto Cartório + MZ NET simultaneamente, sem parar quando Gustavo dorme/sai/desconecta. Combina:

- **Meta única** (super-objetivo macro)
- **Goals vivas** (A→Z + squads) com % auto-atualizado
- **Objetivos parciais** derivados do backlog real
- **Progresso auto-salvo** em arquivos canônicos (append-only)
- **Cron duplo**: macOS launchd (local) + crontab VPS Linux
- **Watchdog** que detecta falha e relança loop automaticamente
- **Auto-recover** se sessão TRAE cair (15-30s sem input = continua sozinho)

> Gustavo: **SE SUMIR / DORMIR / SAIR**, o loop continua sozinho. Não precisa responder prompts. Tudo auto.

---

## 2. ESTADO ATUAL (Phase 1 — Exploration)

### 2.1 Inventário do que JÁ EXISTE (não recriar)

| Componente | Path | Função |
|---|---|---|
| Script loop MZ NET | `~/bin/netloop.sh` | Roda via launchd `com.gustavo.netloop.plist`, 300s |
| Script loop Cartório 100t | `~/bin/cartorio-yolo-100t.sh` | YOLO 100 tasks (criado nesta sessão, não executado) |
| Watchdog Cartório | `~/bin/cartorio-loop-watchdog.sh` | Tick 15min, relança engineer-loop |
| Loop cron | `~/projetos/Cartorio/.harness/loop-engineer/goal-loop-cron.sh` | 01-analyze + 02-test |
| 5 sub-agents | `~/projetos/Cartorio/.harness/agents/0{1..5}-*.sh` | analyze→test→fix→doc→memory |
| Installer launchd | `~/projetos/Cartorio/.harness/loop-engineer/crons/install-launchd.sh` | Cria plist 4h |
| Plan 100 tasks | `~/projetos/Cartorio/.harness/PLAN_100_TASKS_LOOP.md` | Squads S0/A/B/C/D/E/H/J |
| Plan YOLO 100t | `~/projetos/Cartorio/.trae/documents/yolo-super-plano-100t-cartorio-2026-07-03.md` | Criado nesta sessão |
| Plan anterior | `~/projetos/Cartorio/.trae/documents/PLAN_LOOP_GOALS_CRON_MULTIAGENT.md` | Já previa gaps similares |
| Loop state | `~/projetos/Cartorio/.brain/loop-state.json` | Runtime state |
| Brain memory | `~/projetos/Cartorio/.brain/memory/*.md` | 7 arquivos datados |
| GOALS MZ NET | `~/GOALS.md` | Letras A-Z, 76% global |
| MEMORY cross-session | `~/MEMORY.md` | 414 linhas |
| Cross-rein MEMORY | `~/projetos/Cartorio/.harness/memory/MEMORY.md` | 956 linhas, 140 lessons |
| PROGRESS | `~/projetos/Cartorio/PROGRESS.md` | Append-only log |
| Cron ativo atual | `LOOP-ENGINEER-MZNET` ID `f083006d` (10min, schedule tool) |
| LaunchAgents ativos | `com.gustavo.netloop` (5min), `com.gustavo.caddy` (KeepAlive) |

### 2.2 Gaps detectados

1. **Loop YOLO 100t SEM launchd**: `~/bin/cartorio-yolo-100t.sh` existe (criado hoje), mas plist **não instalado**
2. **Falta wrapper unificado**: dois loops (netloop + cartório-yolo) correm independentes — sem master que decide prioridade
3. **Falta watchdog de segundo nível**: se `cartorio-yolo-100t.sh` crashar ou plist sumir, nada detecta
4. **Falta auto-restart TRAE session**: se sessão TRAE cair, prompt não retoma sozinho (precisa hook)
5. **Falta PROGRESS.md unificado**: hoje Cartório tem, MZ NET não tem
6. **GOALS.md precisa de round novo (v24)** com fase Cartório integrada
7. **Métricas não persistem entre sessions**: loop-state.json cresce sem compact (BRAIN8 pendente)

### 2.3 Cronograma de Gustavo (da mensagem)

- 15-30s sem input = continua sozinho
- 1 min sem input = continua
- Dorme = continua
- Sai = continua
- Sudo + Root + Admin = sem pedir permissão

### 2.4 Constraints inegociáveis (AGENTS.md + MSG)

- ✅ Audit log tamper-evident (SHA256 + HMAC)
- ✅ PII scrubbing 3 camadas
- ✅ HITL obrigatório
- ✅ mypy 0 + ruff 0 + pytest >= 90% coverage
- ✅ Mudança em `audit`/`pii` exige review `cartorio-lgpd`
- ✅ Conventional Commits terminando com `Modified by Gustavo Almeida`
- ✅ LGPD-by-design
- ✅ Coding-plan-minimax-[M3/M2.7-HighSpeed] = gastar MENOR quantidade de tokens
- ✅ SEM chamadas, SEM prompts, SEM obstrução

---

## 3. PROPOSED CHANGES

### 3.1 Arquitetura do Loop Infinito

```
┌─────────────────────────────────────────────────────────────┐
│                MASTER LOOP (nova peça)                       │
│  ~/bin/master-loop.sh                                       │
│  - Decide prioridade (Cartório vs MZ NET vs other)          │
│  - Roda sequencialmente 1 round por ciclo                   │
│  - Cron 5min (mais agressivo que os filhos)                  │
│  - Watchdog interno: detecta filho morto, relança           │
│  - Append em PROGRESS.md unificado                          │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬─────────────────┐
    ▼            ▼            ▼                 ▼
┌────────┐ ┌─────────┐ ┌──────────┐   ┌─────────────┐
│ netloop│ │cartorio │ │ engineer │   │healthcheck  │
│ MZ NET │ │YOLO 100t│ │ loop     │   │/health/radar│
│ 5min   │ │ 10min   │ │ 4h       │   │ 1min        │
└────────┘ └─────────┘ └──────────┘   └─────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  ~/GOALS.md     │ <- append-only por round
        │  PROGRESS.md    │ <- append-only por round
        │  .brain/loop-   │ <- JSON patch leve
        │  state.json     │
        │  ~/MEMORY.md    │ <- append-only cross-session
        └─────────────────┘
```

### 3.2 Meta única (super-objetivo)

> **100% production-ready + multi-canal + LGPD ANPD-ready + auto-retomar**

Critério de done:
- [ ] Telegram `/start /menu /agendar /protocolo /humano /lgpd` funcionando em prod (Gustavo testou celular)
- [ ] WhatsApp Evolution conectado (`cartorio-2notas` state=open, QR escaneado)
- [ ] Chatwoot inbox Telegram conectado (handoff escrevente)
- [ ] Painel web escrevente ativo
- [ ] LGPD Art. 18 endpoints completos
- [ ] DPA Evolution + M3 + Opencode-Go assinados
- [ ] RIPD v1.2 arquivado
- [ ] Privacy policy v2 publicada no site
- [ ] DPO nomeado + contato público
- [ ] Audit chain SHA256+HMAC verify 100% green
- [ ] PII scrub 3 camadas testado com property-based + mutation
- [ ] mypy 0 + ruff 0 + pytest 1211+ + coverage 90%+
- [ ] Backup verificado (cron 03:00)
- [ ] Cron ativo 24/7 (5 crons simultâneos, watchdog detecta fail)

### 3.3 Goals A→Z (integrado MZ NET + Cartório)

Ver `~/GOALS.md` round v22 (76% atual). Round v23 fase Cartório já adicionado. Round v24 (próximo) consolida os dois domínios.

**Tabela de progresso** (auto-atualizada por master-loop):

| Letra | Domínio | Objetivo | % atual | Evidência |
|---|---|---|---|---|
| A | MZ NET | YOLO mode + inventário | 100% ✅ | settings.json validado |
| B | MZ NET | Benchmark 1G baseline | 100% ✅ | iperf3 OK |
| C | MZ NET | Cron launchd 24/7 | 100% ✅ | netloop PID 35750 |
| D | MZ NET | DNS DoH | 100% ✅ | MagicDNS active |
| E | MZ NET | Endpoints medidos | 80% 🔧 | gw traceroute 5.6ms |
| F | MZ NET | pf firewall LGPD | 80% 🔧 | 9 block rules |
| G | MZ NET | Git mirror zed-config | 100% ✅ | 5 commits |
| H | MZ NET | HTTPS-only HSTS | 60% 🔧 | mTLS cert |
| I | MZ NET | MAC randomizado | 50% 🔧 | en0 estável |
| J | MZ NET | JWT + secrets 600 | 100% ✅ | vault OK |
| K | MZ NET | Kill switch SSH/VPS | 70% 🔧 | Tailscale UP |
| L | MZ NET | Logs centralizados | 100% ✅ | ~/Library/Logs |
| M | MZ NET | MCP servers 14+ | 50% 🔧 | 12/14 |
| N | MZ NET | Netstat clean | 60% 🔧 | 50 LISTEN mapped |
| O | MZ NET | Rotas ordenadas | 50% 🔧 | en0 default |
| P | MZ NET | Prometheus exporter | 0% ⏳ | pendente |
| Q | MZ NET | QoS SSH/HTTPS | 0% ⏳ | pendente |
| R | MZ NET | Caddy/Traefik | 60% 🔧 | HTTP :8081 |
| S | MZ NET | SSH hardened | 90% ✅ | fail2ban OK |
| T | MZ NET | Tailscale ACLs | 30% 🔧 | 7 peers |
| U | MZ NET | sysctl TCP buffers | 0% ⏳ | pendente |
| V | MZ NET | VPS inventário | 60% 🔧 | 63d uptime |
| W | MZ NET | Wi-Fi analysis | 40% 🔧 | system_profiler |
| X | MZ NET | XPC services | 70% ✅ | disk 97% warning |
| Y | MZ NET | YAML unificado | 70% ✅ | configs OK |
| Z | MZ NET | Zero-trust final | 50% 🔧 | parcial |
| **AA-AZ** | Cartório | (squads S0/A/B/C/D/E/H/J + Brain8) | 60% 🔧 | ver PLAN_100_TASKS_LOOP |
| **BA-BZ** | LGPD ANPD | (D13-D25 + sprint 3 LGPD-026-032) | 30% 🔧 | RIPD pendente |
| **CA-CZ** | Testes | mutation + property + load k6 | 0% ⏳ | pendente |

### 3.4 Objetivos parciais (TOP 30 derivados do backlog)

Ordem de prioridade para auto-execução:

1. **B.1** Regenerar CHATWOOT_API_KEY (token inválido)
2. **B.2** Wire MCP server Evolution (#26)
3. **B.3** Wire MCP server Chatwoot (#27)
4. **B.4** Wire MCP server Redis (#28)
5. **B.5** Endpoints LGPD sprint 3 (LGPD-026-032)
6. **B.6** PII output scrub router.py:553 (P0.7)
7. **B.7** PII output scrub integrations.py:190 (P0.7)
8. **B.8** Response shape pii_blocked+handoff (P0.8)
9. **B.9** Audit log conversa.pii_blocked (P0.9)
10. **B.10** DPA Evolution template
11. **B.11** DPA M3 template
12. **B.12** DPA Opencode-Go template
13. **B.13** RIPD v1.2 finalizar
14. **B.14** DPO nomear + contato publicar
15. **B.15** Privacy policy v2 site
16. **B.16** DPO dashboard métricas
17. **B.17** Encryption at-rest Postgres
18. **B.18** Breach notification 72h
19. **B.19** Training interno 5 vídeos
20. **B.20** Mutation testing setup
21. **B.21** Property-based testing (hypothesis)
22. **B.22** Load test k6 1000 req/s
23. **B.23** crwal4ai imagem fix
24. **B.24** Drenar 7 pending Telegram updates
25. **B.25** Cleanup repo (modified files)
26. **B.26** Patch Traefik custom.yaml (DNS routers)
27. **B.27** Wire LiteLLM tracing na API
28. **B.28** Wire Argilla feedback na API
29. **B.29** Compact loop-state.json (BRAIN8)
30. **B.30** Auditoria ANPD anual

### 3.5 Cronograma de execução (master-loop)

```bash
# /Users/gustavoalmeida/bin/master-loop.sh
ROUNDS_PER_HOUR=12  # 1 round a cada 5min
DOMAIN_ROTATION=(cartorio mznet cartorio mznet cartorio mznet)  # alterna prioridade
```

**Por round** (5min):
1. Lê `~/GOALS.md` round atual + pendências
2. Seleciona próximo objetivo parcial (B.N)
3. Executa 1 task (analyze → test → fix → doc → memory)
4. Append em PROGRESS.md
5. Append em MEMORY.md (cross-session)
6. Patch leve em loop-state.json (current_round, last_domain)
7. Atualiza % na tabela de goals
8. Sleep 240s (sobra 60s buffer)

**Por ciclo** (1h = 12 rounds):
- Compact log rotativo (manter últimos 1000)
- Verificar watchdog dos filhos
- Auto-relançar se plist sumiu
- Backup snapshot do estado

**Por dia** (24h = 288 rounds):
- Append em GOALS.md round vN+1
- Consolidar lessons do dia
- Limpar cache de logs antigos

### 3.6 Filesystem de outputs

**CRIAR:**
1. `/Users/gustavoalmeida/bin/master-loop.sh` (loop master unificado)
2. `/Users/gustavoalmeida/Library/LaunchAgents/com.gustavo.master-loop.plist` (cron 5min)
3. `/Users/gustavoalmeida/Library/LaunchAgents/com.gustavo.cartorio-yolo-100t.plist` (cron 10min)
4. `/Users/gustavoalmeida/Library/LaunchAgents/com.gustavo.master-watchdog.plist` (cron 1min)
5. `~/PROGRESS.md` unificado (MZ NET + Cartório juntos)
6. `/Users/gustavoalmeida/projetos/Cartorio/.brain/memory/2026-07-03-loop-goals.md` (1-pager loop)
7. `~/GOALS.md` round v24 (append)

**EDITAR (append-only):**
1. `~/MEMORY.md` (entrada datada sessão 2026-07-03T11:00Z)
2. `~/GOALS.md` (round v24, fase loop infinito)
3. `/Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md` (Lesson 141, 142, 143)
4. `/Users/gustavoalmeida/projetos/Cartorio/.brain/loop-state.json` (patch leve)
5. `~/PROGRESS.md` (unificado MZ NET + Cartório)

**NÃO TOCAR:**
- `backend/app/services/audit.py`, `audit_*.py`, `pii.py` (read LGPD review)
- `backend/.env`, `.env.example` (secrets)
- VPS remoto sem aprovação explícita (regra AGENTS.md)
- `~/.zshrc`, `~/.zshenv` (exceto path seguro)

---

## 4. ASSUMPTIONS & DECISIONS

### 4.1 Decisões locked-in (da sessão)

- **D1**: Modo YOLO 100% autônomo. SEM prompts, SEM permissão.
- **D2**: Gustavo sumir/dormir/sair = loop continua. Watchdog detecta inactivity e retoma.
- **D3**: SUDO + Root + Admin do Gustavo = sem pedir permissão em comandos sudo.
- **D4**: Coding-plan-minimax-[M3/M2.7-HighSpeed] = minimizar tokens, maximizar entregas.
- **D5**: Append-only em MEMORY.md, GOALS.md, PROGRESS.md, .harness/memory/MEMORY.md.
- **D6**: Conventional Commits terminando com `Modified by Gustavo Almeida`.
- **D7**: Gates rígidos: mypy 0, ruff 0, pytest 1211+, coverage 90%+.
- **D8**: Mudança em `audit`/`pii` exige review `cartorio-lgpd` antes do commit.
- **D9**: LGPD-by-design sempre.
- **D10**: Auto-recuperável: se TRAE session cair, próxima session retoma do estado em `loop-state.json`.

### 4.2 Assumptions

- **A1**: Gustavo MacBook Pro com launchd funcional
- **A2**: VPS 100.99.172.84 / 187.77.236.77 reachable via Tailscale
- **A3**: Redis recovered, 8/8 services swarm UP (loop-state 2026-07-02)
- **A4**: `~/bin/master-loop.sh` ainda não existe (precisa criar)
- **A5**: `~/Library/LaunchAgents/com.gustavo.master-loop.plist` ainda não existe
- **A6**: TRAE session TRAE restart preserva `loop-state.json` (persiste em `.brain/`)

### 4.3 Out of scope

- Rotação de chaves API (decisão Gustavo 2026-06-24 — NUNCA sob pressão)
- Mudanças destrutivas (rm -rf, force push, drop db) — sempre via SUI approval
- Push direto para origin (sempre via PR, regra AGENTS.md)
- Modificar arquivos de produção sem commit

---

## 5. VERIFICATION STEPS

### 5.1 Setup de loop (fase 1)
```bash
# 1. Master script existe e executável
test -x /Users/gustavoalmeida/bin/master-loop.sh && echo "  ✅ master-loop.sh OK"

# 2. Plists instalados
launchctl list | grep -E "(gustavo.master-loop|cartorio-yolo-100t|master-watchdog)" && echo "  ✅ plists OK"

# 3. Cron ativo
crontab -l | grep master-loop  # se VPS

# 4. PROGRESS.md unificado criado
test -f /Users/gustavoalmeida/PROGRESS.md && echo "  ✅ PROGRESS.md OK"

# 5. Goals round v24
grep -c "ROUND v24" /Users/gustavoalmeida/GOALS.md && echo "  ✅ GOALS v24 OK"

# 6. Lesson 141-143 em cross-rein
grep -c "Lesson 141\|Lesson 142\|Lesson 143" /Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md && echo "  ✅ Lessons OK"

# 7. Loop-state patch
jq -e .current_session /Users/gustavoalmeida/projetos/Cartorio/.brain/loop-state.json && echo "  ✅ loop-state OK"
```

### 5.2 Gates por round (5min)
```bash
# Master loop output
tail -50 /Users/gustavoalmeida/Library/Logs/master-loop.log | grep "round="

# Round counter increasing
test "$(cat /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/yolo-100t-round-counter)" -gt 0 && echo "  ✅ counter OK"

# No error em last 100 linhas
grep -c "ERROR\|FATAL\|PANIC" /Users/gustavoalmeida/Library/Logs/master-loop.err.log && echo "  ✅ no errors"

# Children loops still alive
launchctl list | grep -E "(gustavo.netloop|cartorio-yolo-100t)" && echo "  ✅ children alive"
```

### 5.3 SUI gates (Gustavo em celular)

| Ação | Como verificar | Auto-resolve? |
|---|---|---|
| Escanear QR WhatsApp | `curl -H "apikey: $EV_KEY" evolution.../instance/connectionState/cartorio-2notas` → `state=open` | NÃO (precisa Gustavo) |
| Criar DNS A records | `dig chatwoot.2notasudi.com.br @1.1.1.1 +short` → 187.77.236.77 | NÃO (painel Hostinger) |
| Testar Telegram `/start` | Gustavo transcreve resposta | NÃO (precisa celular) |

### 5.4 Done criteria (loop infinito)
- [ ] master-loop.sh instalado + plist carregado
- [ ] 3 plists filhos rodando (master-loop, cartorio-yolo-100t, master-watchdog)
- [ ] cron ativo 24/7 (verificar KeepAlive = true em todos)
- [ ] logs em `~/Library/Logs/master-loop.{out,err}.log`
- [ ] PROGRESS.md unificado sendo atualizado por round
- [ ] GOALS.md round v24+ sendo appendados
- [ ] MEMORY.md cross-session sendo appendado
- [ ] loop-state.json patch leve por round
- [ ] Auto-recuperação: se plist sumir, watchdog detecta e relança em <5min
- [ ] Auto-retomar: TRAE session reload lê loop-state.json e continua do round N+1

---

## 6. ROLLBACK PLAN

Se master-loop crashar persistentemente:
1. `launchctl unload ~/Library/LaunchAgents/com.gustavo.master-loop.plist`
2. `launchctl unload ~/Library/LaunchAgents/com.gustavo.master-watchdog.plist`
3. Investigar `~/Library/Logs/master-loop.err.log`
4. Reverter `~/PROGRESS.md` corrupto (git checkout)
5. Restart master: `launchctl load ~/Library/LaunchAgents/com.gustavo.master-loop.plist`

Se SUI fix quebrar prod:
1. Auto-rollback via Easypanel snapshot (J8 task)
2. Alertmanager → Telegram GRUPO Pietra
3. Postmortem em `docs/POSTMORTEMS.md`

Se Gustavo quiser parar tudo:
```bash
launchctl unload ~/Library/LaunchAgents/com.gustavo.master-loop.plist
launchctl unload ~/Library/LaunchAgents/com.gustavo.cartorio-yolo-100t.plist
launchctl unload ~/Library/LaunchAgents/com.gustavo.master-watchdog.plist
# netloop e caddy continuam (são separados)
```

---

## 7. ASSUNTOS LGPD / SEGURANÇA

- **PII**: master-loop NUNCA escreve dados pessoais em log. Só metadados (hostnames, latência, contadores).
- **Audit**: toda ação do master-loop gera entrada em audit chain (SHA256+HMAC) antes de qualquer commit.
- **Secrets**: master-loop lê de `~/.zcode/secrets/` (chmod 600), nunca de `.env` em texto puro.
- **SUDO**: master-loop executa sudo SEM pedir senha (Gustavo é admin), mas só para:
  - `launchctl load/unload`
  - `kill` de processos próprios
  - `chmod`, `chown` em paths autorizados
  - NUNCA: `rm -rf`, `dd`, `mkfs`, formatação, drop database

---

## 8. NOTAS OPERACIONAIS

- **Cache de tokens**: M3 prompt cache ativo (`anthropic-beta: prompt-cache-2024-12`). Speedup 157× visto na sessão anterior.
- **MCP servers usados**: 14 MCPs reais ativos (`.config/zed/MEMORY.md` linha 13). Lista inclui sequential-thinking, context7, puppeteer, fetch, git, github, filesystem, chrome-devtools, jules, render, linear, postgres, playwright, trash.
- **Coding plan**: minimax M3 + M2.7-highspeed. Minimizar tokens = usar append-only em arquivos pequenos, evitar re-leitura completa.
- **Watchdog 1min**: detecta se master-loop travou (sem novo round em 6min) e mata + relança.
- **KeepAlive**: todos os plists têm KeepAlive=true para auto-restart em caso de crash.

---

## 9. DONE CRITERIA — LOOP INFINITO OPERACIONAL

```
✅ master-loop.sh em ~/bin/ (executável)
✅ 3 plists em ~/Library/LaunchAgents/ (master-loop, cartorio-yolo-100t, master-watchdog)
✅ launchctl list mostra os 3 carregados
✅ ~/Library/Logs/master-loop.{out,err}.log crescendo
✅ ~/PROGRESS.md unificado com 1 entrada por round
✅ ~/GOALS.md round v24+ appendados
✅ ~/MEMORY.md cross-session appends
✅ .brain/loop-state.json patch leve por round
✅ Round counter em .brain/memory/yolo-100t-round-counter incrementando
✅ Watchdog detecta crash em <5min
✅ TRAE session reload retoma do loop-state.json
✅ Gustavo pode sumir = loop continua
```

Modified by Gustavo Almeida