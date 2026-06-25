# E07 — Fix OpenClaw Context 131k → 1M (URGENTE)

> **SQUAD E P0** | **Super Prompt v4.0.0** Bloco 12.5
> **L155**: OpenClaw MiniMax-M3 1M context + thinking adaptive

## 🎯 Problema

OpenClaw Agent (Pietra) está rodando com **contexto limitado a 131.1k tokens** quando deveria estar com **1M tokens**. Isso impacta:

- Memória de conversas longas (perda de contexto após ~10 mensagens)
- Capacidade de processar documentos extensos
- Thinking adaptativo limitado
- Qualidade geral das respostas

## 🔧 Solução

Editar 2 arquivos de configuração em `/home/node/.openclaw/agents/main/agent/` na VPS:

1. `models.json` — `max_tokens: 1000000` (1M)
2. `agent.json` — atualizar chave OpenCode-Go + thinking adaptive

## 🚀 Execução Rápida (RECOMENDADO — Gustavo ou agente com SSH)

### Opção A: Script automatizado

```bash
# Do MacBook Pro (com Tailscale ativo)
ssh root@100.99.172.84 "bash -s" < /Users/gustavoalmeida/projetos/Cartorio/scripts/fix_openclaw_context_1M.sh
```

**OU** copiar o script para a VPS primeiro:

```bash
scp scripts/fix_openclaw_context_1M.sh root@100.99.172.84:/tmp/
ssh root@100.99.172.84 "bash /tmp/fix_openclaw_context_1M.sh"
```

### Opção B: Manual (passo-a-passo)

```bash
# 1. SSH na VPS
ssh root@100.99.172.84

# 2. Backup dos arquivos
mkdir -p /home/node/.openclaw/backups/fix_1M_$(date +%Y%m%d_%H%M%S)
cd /home/node/.openclaw/agents/main/agent
cp models.json /home/node/.openclaw/backups/fix_1M_$(date +%Y%m%d_%H%M%S)/
cp agent.json /home/node/.openclaw/backups/fix_1M_$(date +%Y%m%d_%H%M%S)/

# 3. Editar models.json — set max_tokens=1000000
python3 -c "
import json
from pathlib import Path
p = Path('models.json')
d = json.loads(p.read_text())
if 'models' in d:
    for m, c in d['models'].items():
        c['context_length'] = 1000000
        c['max_tokens'] = 1000000
        if 'max_output_tokens' in c:
            c['max_output_tokens'] = 32000
else:
    d['max_tokens'] = 1000000
    d['context_length'] = 1000000
p.write_text(json.dumps(d, indent=2))
print('models.json updated')
"

# 4. Editar agent.json — nova chave OpenCode-Go
python3 -c "
import json
from pathlib import Path
p = Path('agent.json')
d = json.loads(p.read_text())
NEW_KEY = 'sk-xcRwExjQjqmlc5swP8umqK2YqWUfVt23H3Xl6dpd9TqEyi16ssJXzHeUFGNNIfsJ'
if 'providers' in d:
    for name, c in d['providers'].items():
        if 'openai' in name or 'opencode' in name.lower():
            if 'api_key' in c and 'xcRwExjQ' not in c.get('api_key', ''):
                c['api_key'] = NEW_KEY
if 'thinking' in d:
    d['thinking']['enabled'] = True
    d['thinking']['mode'] = 'adaptive'
p.write_text(json.dumps(d, indent=2))
print('agent.json updated')
"

# 5. Restart do container
docker service update --force cartorio_openclaw-gateway

# 6. Validar
sleep 10
curl https://agent.2notasudi.com.br/health
```

## ✅ Validação Pós-Fix

```bash
# 1. Health check
curl https://agent.2notasudi.com.br/health
# Esperado: {"ok":true,"status":"live"}

# 2. Testar contexto real (enviar mensagem longa)
# Use o Telegram bot @test_cartorio_bot
# Ou faça um POST /v1/messages com payload extenso
```

## 📊 Mudanças Esperadas

| Item | Antes | Depois |
|------|-------|--------|
| Contexto | 131.1k tokens | 1M tokens |
| Thinking | ON (pode estar limitado) | Adaptive ON |
| Chave OpenCode-Go | Antiga (limitada) | Nova (sk-xcRwExjQ) |
| Capacidade de conversa | ~10 mensagens | 50+ mensagens |

## 🔍 Troubleshooting

Se após o fix o contexto continuar limitado:

1. Verificar logs: `docker service logs cartorio_openclaw-gateway --tail 50`
2. Verificar config: `cat /home/node/.openclaw/agents/main/agent/models.json`
3. Confirmar restart: `docker service ps cartorio_openclaw-gateway`
4. Re-rodar script (idempotente)

## 📝 Após Fix

1. Atualizar `.harness/memory/MEMORY.md`:
   ```markdown
   ## L155 — OpenClaw 1M context FIX
   - Data: 2026-06-26
   - Antes: 131.1k
   - Depois: 1M
   - Commit: 88f7b87 (script) + <novo-commit-ps>
   - Status: ✅ DONE
   ```

2. Marcar E07 como DONE em `.harness/TASKS.md`
3. Atualizar `.brain/loop-state.json`: `current_squad: E`
4. Reportar para Gustavo: contexto fixado ✅

## 🔗 Arquivos Relacionados

- `scripts/fix_openclaw_context_1M.sh` — Script principal (149 linhas)
- `.harness/memory/MEMORY.md` — Lessons 155, 178, 179
- `backend/tests/` — Tests integração OpenClaw (1211 passing)

---

**Criado em**: 2026-06-26 (ZCode/Mavis)
**Status**: Script pronto, aguardando execução por Gustavo/agente com SSH
**Commit**: `88f7b87` (scripts/fix_openclaw_context_1M.sh)
