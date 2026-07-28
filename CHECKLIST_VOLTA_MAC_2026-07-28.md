# ✅ Checklist — quando voltar no Mac

> Ordem importa. Cada passo depende do anterior.

---

## 🚨 30 segundos — Restart do bot Lark

```bash
# Bot v6 já está rodando (PID 77420, port 8083)
# Se caiu, restart:
launchctl kickstart -k gui/$(id -u)/ai.zcode.lark-bot

# Validar
curl http://localhost:8083/health
# esperado: {"bot":"v6 ok", "pietra_ok": true, ...}
```

---

## 🦊 5 min — Fechar P0 identity leak no VPS

```bash
# 1. SSH pro VPS
ssh root@187.77.236.77

# 2. Rodar patch (dentro do repo no VPS, se existir)
bash /caminho/scripts/vps_fix_cartorio_hermes_F3.sh

# OU manual (ver Lesson 283):
# - Editar /opt/data/config.yaml: trocar *free → minimax/m1-m3
# - Adicionar guard: model_allow_free_tier_fallback: false
# - docker service update --force cartorio_hermes

# 3. Validar (bot responde "Sou a Pietra" sem fallback free-tier)
```

---

## 📨 10 min — Bot Lark no grupo GG

### Passo 1: Developer Console

1. https://open.larksuite.com → Developer Console → Create App → Custom App
2. Nome: **"Pietra Lark Bot"**
3. Permissions → marcar:
   - `im:message`, `im:message.group_at_msg`, `im:message.group_msg`
   - `im:message.p2_msg`, `im:chat`
   - `im:media`, `im:media:download`
4. Salvar → aprovar permissões

### Passo 2: Credenciais

Basic Information → Credentials:
- App ID (`cli_...`)
- App Secret
- **Copiar também Verification Token** (Event Subscriptions)

### Passo 3: Configurar `.env.lark`

```bash
cat > /Users/gustavoalmeida/Projetos/Cartorio/scripts/.env.lark <<'EOF'
LARK_APP_ID=cli_xxxx
LARK_APP_SECRET=xxxx
LARK_VERIFICATION_TOKEN=xxxx
LARK_QUIET_GROUP=false
LARK_OWNER_OPEN_ID=ou_seu_id_aqui
PIETRA_BASE=https://api.2notasudi.com.br
LARK_BOT_PORT=8083
EOF
chmod 600 /Users/gustavoalmeida/Projetos/Cartorio/scripts/.env.lark
```

### Passo 4: Tunnel público

```bash
# Temporário (pra teste rápido):
cloudflared tunnel --url http://localhost:8083
# Copiar URL https://xxx.trycloudflare.com

# OU permanente (recomendado, ver runbook):
cloudflared tunnel login
cloudflared tunnel create lark-bot
# ... (ver LARK_BOT_V3_RUNBOOK.md)
```

### Passo 5: Registrar URL no Lark

Event Subscriptions → Request URL: `<URL-DO-TUNNEL>/lark/webhook` → Save
(Se ficar verde ✓ = handshake OK)

### Passo 6: Adicionar no grupo GG

1. Abrir grupo **GG** no Lark
2. Settings → Bots → Add Bot → **Pietra Lark Bot**
3. **Promover a admin** (Settings → Members → Bot → Set as Admin)

### Passo 7: Testar

No grupo GG:
```
!ajuda        → lista comandos
!saude        → status bot
oi, qual seu nome?  → "Sou a Pietra, agente do 2o Cartório..."
[manda foto de CPF]  → OCR + LGPD scrub + resposta
```

---

## 🔓 2 min — Liberar OpenClaw iMessage

System Settings → Privacy & Security → Full Disk Access:
1. Remover `/Applications/OpenClaw.app` (se tiver)
2. Readicionar (botão +)
3. Ativar toggle

Depois:
```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
tail -f /Users/gustavoalmeida/.openclaw/logs/gateway.log
# Esperado: "channel imsg connected" sem crashloop
```

---

## 🧹 30 min (opcional) — Limpeza do Mac

```bash
# Limpar caches pesados (~10GB)
rm -rf ~/.cache/uv  # recria quando precisar
rm -rf ~/Library/Caches/*
brew cleanup

# Remover installers duplicados em Downloads
rm ~/Downloads/Antigravity.dmg
rm ~/Downloads/Antigravity\ IDE.dmg
rm ~/Downloads/ChatGPT.dmg  # se já instalado
rm ~/Downloads/Hermes-Setup.dmg  # versão antiga
# Mantém: Hermes-Setup (1).dmg (mais recente)
```

---

## 📝 Git commit (pra registrar tudo)

```bash
cd /Users/gustavoalmeida/Projetos/Cartorio
git add scripts/lark_bot*.py scripts/test_lark_bot*.py scripts/LARK_BOT*.md
git add scripts/vps_fix_cartorio_hermes_F3.sh
git add .harness/memory/lesson-283-* .harness/memory/lesson-284-* .harness/memory/lesson-285-*
git add SESSION_2026-07-28_INDEX.md CHECKLIST_VOLTA_MAC_2026-07-28.md

git commit -m "feat(lark-bot): standalone v6 com OCR + detector + memoria + admin

- v3: bot plugado em PIETRA VPS (persona canonica, PII scrub, identity guard)
- v4: + OCR tesseract + LGPD scrub no OCR extraido
- v5: + endpoint /test-image standalone + log JSON estruturado
- v6: + detector tipo doc (CPF/CNH/procuracao/escritura/...) + memoria PIETRA
       + admin commands (!stats, !doc, !bot stop, !broadcast)
- LaunchAgent ai.zcode.lark-bot auto-start 24/7 (port 8083)
- Runbook completo em LARK_BOT_V3_RUNBOOK.md
- 3 lessons (283 P0 identity leak VPS, 284 standalone vs TRAE SOLO,
  285 Hermes.app stub vs functional)
- SESSION_2026-07-28_INDEX.md consolidado

Tested: OCR extrai CPF, LGPD scrub mascara antes do LLM,
PIETRA responde com persona canonica + HITL quando aplicavel.

Modified by Gustavo Almeida"
```

---

## 📊 Quando tudo acima estiver OK

- [ ] Bot Lark respondendo no grupo GG (responde "Sou a Pietra")
- [ ] OCR funciona em fotos de documentos
- [ ] P0 IDENTITY_HERMES_LEAK fechado (N≥30 pós-fix)
- [ ] OpenClaw iMessage conectado (cliente consegue mandar msg pro bot)
- [ ] `.env.lark` salvo no 1Password (não no repo!)
- [ ] Cloudflared tunnel rodando 24/7

Modified by Gustavo Almeida · 2026-07-28