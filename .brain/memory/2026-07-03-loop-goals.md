# LOOP INFINITO — 1-Pager (2026-07-03)

> Compilado por TRAE session `loop-infinito-goals-cron-meta-progresso-2026-07-03`.
> Estado operacional + goals + meta + progresso + cron. Append-only.

## 🎯 Meta única
**100% production-ready + multi-canal + LGPD ANPD-ready + auto-retomar**

## 📊 Progresso global
- **MZ NET PROJETO SENTINELA**: 76% (20/26 letras + 5 parciais) — `~/GOALS.md` round v22
- **Cartório 100 tasks**: 60% (squads A-J + Brain8 + crwal4ai + SUI)
- **LGPD ANPD**: 30% (DPA + RIPD + privacy v2 + DPO pendentes)
- **Testes extras**: 0% (mutation + property + load k6)

## 🔁 Loops ativos

| Loop | Cron | Path | Função |
|---|---|---|---|
| **master-loop** | 5min | `~/bin/master-loop.sh` + plist | orquestrador unificado |
| **cartorio-yolo-100t** | 10min | `~/bin/cartorio-yolo-100t.sh` + plist | 100 tasks backlog |
| **master-watchdog** | 1min | `~/bin/master-watchdog.sh` + plist | auto-recuperação |
| **netloop** (existente) | 5min | `~/bin/netloop.sh` + plist | MZ NET já rodando |
| **caddy** (existente) | KeepAlive | `~/Library/LaunchAgents/com.gustavo.caddy.plist` | reverse proxy |
| **cron schedule tool** | 10min | `LOOP-ENGINEER-MZNET f083006d` | goal auto-reactivate |

## 📁 Arquivos canônicos

| Arquivo | Função |
|---|---|
| `~/MEMORY.md` | cross-session lessons (414 linhas) |
| `~/AGENTS.md` | convenções globais |
| `~/GOALS.md` | objetivos A→Z (round v22+v23+v24+) |
| `~/PROGRESS.md` | log unificado por round |
| `~/bin/master-loop.sh` | loop master 5min |
| `~/bin/master-watchdog.sh` | watchdog 1min |
| `~/bin/cartorio-yolo-100t.sh` | loop YOLO 100 tasks |
| `~/bin/netloop.sh` | loop MZ NET |
| `~/Library/LaunchAgents/com.gustavo.*.plist` | 3 plists novos + 2 existentes |
| `~/Library/Logs/master-loop.{out,err}.log` | logs do master |
| `~/Library/Logs/master-watchdog.*.log` | logs do watchdog |
| `/Users/gustavoalmeida/projetos/Cartorio/.brain/loop-state.json` | runtime state |
| `/Users/gustavoalmeida/projetos/Cartorio/.brain/memory/*.md` | brain append-only |
| `/Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md` | cross-rein lessons (956 linhas) |
| `/Users/gustavoalmeida/projetos/Cartorio/.harness/PLAN_100_TASKS_LOOP.md` | plan canônico |
| `/Users/gustavoalmeida/projetos/Cartorio/.harness/task-bank.json` | 100 tasks (21% done) |
| `/Users/gustavoalmeida/projetos/Cartorio/.trae/documents/yolo-super-plano-100t-cartorio-2026-07-03.md` | plan gerado nesta sessão |
| `/Users/gustavoalmeida/projetos/Cartorio/.trae/documents/loop-infinito-goals-cron-meta-progresso-2026-07-03.md` | plan gerado nesta sessão |

## ✅ Done criteria do loop infinito
```
✅ master-loop.sh em ~/bin/ (executável)
✅ 3 plists em ~/Library/LaunchAgents/
✅ launchctl list mostra os 3 carregados
✅ ~/Library/Logs/master-loop.{out,err}.log crescendo
✅ ~/PROGRESS.md unificado com 1 entrada por round
✅ ~/GOALS.md round v24+ appendados
✅ ~/MEMORY.md cross-session appends
✅ .brain/loop-state.json patch leve por round
✅ Round counter incrementando
✅ Watchdog detecta crash em <6min
✅ TRAE session reload retoma do loop-state.json
✅ Gustavo pode sumir = loop continua
```

## 🚀 Como Gustavo controla
- **Status**: `launchctl list | grep gustavo` (mostra todos os loops ativos)
- **Log live**: `tail -f ~/Library/Logs/master-loop.out.log`
- **Parar tudo**: `for p in com.gustavo.master-loop com.gustavo.cartorio-yolo-100t com.gustavo.master-watchdog; do launchctl unload ~/Library/LaunchAgents/$p.plist; done`
- **Restart**: substituir `unload` por `load`
- **Status Cartório**: `curl https://api.2notasudi.com.br/health`
- **Status MZ NET**: `tail -50 ~/Library/Logs/netloop.out.log`

Modified by Gustavo Almeida