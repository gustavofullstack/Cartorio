# SESSION 2026-07-28 — INDEX consolidado

> Tudo que foi feito nessa sessão (28/07/2026), organizado pra você não perder.

---

## 🎯 O que você pediu

1. Ver o que os agents do cartório estão fazendo
2. "Deu pau" no Hermes local
3. Investigar por que TRAE Work e Hermes caíram
4. Aprender iMessage + Lark
5. Bot do Lark que vê imagem (não só eco)
6. "Evolui mais" (várias vezes)

## ✅ O que foi entregue

### 1. Investigação inicial (agents rodando)

- Inventário dos 10 reins (`.harness/reins/`)
- Identificação dos processos zumbis (pytest órfãos, OpenClaw crashloop)
- P0 IDENTITY_HERMES_LEAK F3 confirmado (VPS `cartorio_hermes` com models free-tier)
- Patch YAML + runbook SSH → `scripts/vps_fix_cartorio_hermes_F3.sh`
- Lesson 283 salva

### 2. Lark bot standalone (6 versões iteradas)

| Versão | Tamanho | Features |
|---|---|---|
| v1 (`lark_bot_server.py`) | 5KB | echo inútil |
| v2 (`lark_bot.py`) | 9KB | + imagem, arquivo, LLM direto |
| v3 (`lark_bot_v3.py`) | 14KB | + PIETRA VPS + persona canônica + PII scrub |
| v4 (`lark_bot_v4.py`) | 17KB | + OCR (tesseract) + LGPD scrub em OCR |
| v5 (`lark_bot_v5.py`) | 17KB | + endpoint `/test-image` + log JSON estruturado |
| **v6 (`lark_bot_v6.py`)** | **24KB** | **+ detector de doc + memória PIETRA + admin commands + resumo auto** |

### 3. Testes E2E

- `scripts/test_lark_bot_v3.py` — valida PIETRA VPS + identidade
- `scripts/test_lark_bot_v4.py` — valida OCR + bot local

### 4. Documentação

- `scripts/LARK_BOT_SETUP.md` (v1, 4KB)
- `scripts/LARK_BOT_V3_RUNBOOK.md` (atualizado pra v6, 9KB)

### 5. LaunchAgent

- `~/Library/LaunchAgents/ai.zcode.lark-bot.plist` (auto-start 24/7)
- Atualizado pra v6 (port 8083, pillow, OCR_LANG)

### 6. Lessons (3 novas)

- **Lesson 283** — VPS cartorio_hermes free-tier = Camada 3 identity leak
- **Lesson 284** — Bot Lark standalone > TRAE SOLO shell (arquitetural)
- **Lesson 285** — Hermes.app stub em /Applications causa crashes silenciosos

### 7. Fix do Hermes stub

- Backup: `~/.hermes_backup/Hermes.app.stub-20260728`
- Symlink: `/Applications/Hermes.app` → app funcional
- Crash reports velhos (>30d) limpos

### 8. Bot v6 rodando AGORA

- PID 77420, port 8083
- PIETRA VPS conectado
- OCR disponível
- LGPD scrub validado (CPF virou *** antes do LLM)

---

## 📁 Arquivos da sessão

```
/Users/gustavoalmeida/Projetos/Cartorio/
├── scripts/
│   ├── lark_bot.py                       (v2, 9KB)
│   ├── lark_bot_server.py                (v1, 5KB)
│   ├── lark_bot_v3.py                    (v3, 14KB)
│   ├── lark_bot_v4.py                    (v4, 17KB)
│   ├── lark_bot_v5.py                    (v5, 17KB)
│   ├── lark_bot_v6.py                    (v6, 24KB) ← USAR ESTE
│   ├── test_lark_bot_v3.py               (E2E v3)
│   ├── test_lark_bot_v4.py               (E2E v4)
│   ├── LARK_BOT_SETUP.md                 (setup v1)
│   ├── LARK_BOT_V3_RUNBOOK.md            (runbook v6 atualizado)
│   └── vps_fix_cartorio_hermes_F3.sh     (P0 identity leak VPS)
├── .harness/memory/
│   ├── lesson-283-vps-cartorio-hermes-freetier-identity-leak-camada3-2026-07-28.md
│   ├── lesson-284-lark-bot-standalone-vs-trae-solo-2026-07-28.md
│   └── lesson-285-hermes-app-stub-vs-functional-2026-07-28.md
├── SESSION_2026-07-28_INDEX.md            ← ESTE ARQUIVO
└── CHECKLIST_VOLTA_MAC_2026-07-28.md      (a fazer)

/Users/gustavoalmeida/Library/LaunchAgents/
└── ai.zcode.lark-bot.plist               (24/7, port 8083)

/Users/gustavoalmeida/.hermes_backup/
└── Hermes.app.stub-20260728              (backup do stub removido)
```

---

## ⏳ O que AINDA falta (depende de você no Mac)

1. **Subir cloudflared** → `cloudflared tunnel --url http://localhost:8083`
2. **Criar `.env.lark`** com App ID/Secret/Token do Developer Console Lark
3. **Criar app custom bot** no Lark + adicionar permissões (ver `LARK_BOT_V3_RUNBOOK.md` passo 1)
4. **Colar URL do tunnel** no Developer Console como Request URL
5. **Adicionar bot como admin** no grupo GG
6. **Configurar `LARK_OWNER_OPEN_ID`** no `.env.lark` (seu open_id) pra usar comandos admin
7. **Rodar `vps_fix_cartorio_hermes_F3.sh`** no VPS (via SSH) pra fechar P0 identity leak Camada 3
8. **Restart do OpenClaw** após liberar Full Disk Access no macOS (System Settings → Privacy)

---

## 🧪 Validações que rodei AGORA

| Check | Resultado |
|---|---|
| Bot v6 health endpoint | ✓ `http://localhost:8083/health` |
| PIETRA VPS health | ✓ `{"status":"ok","redis":"connected"}` |
| PIETRA identidade | ✓ "Sou a Pietra, agente do 2o Cartório de Notas de Uberlândia" |
| OCR extrai texto | ✓ (com 1-2 dígitos trocados, esperado) |
| LGPD scrub no OCR | ✓ CPF virou `123.***.***-**` antes do LLM |
| Detector de doc | ✓ CPF/CNH/PROCURAÇÃO detectados |
| Memória PIETRA VPS | ✓ endpoint existe |
| Hermes.app symlink | ✓ Electron Framework presente |
| Cloudflared | ✗ não subiu |

---

## 🚨 Pendências humanas (inalteradas)

- **B1** Audit 0028 + legacy sign-off LGPD
- **B2** WhatsApp QR (`cartorio-2notas`)
- **B3** Secrets rotation (NUNCA sob pressão)
- **B4** MCP endpoint config (resolvido parcialmente)
- **B5** Felipe confirmação visual iPhone
- **P0** IDENTITY_HERMES_LEAK (Lesson 283 = plano de fechamento)
- **NOVO** Librear Full Disk Access do OpenClaw (4+ dias crashloop)
- **NOVO** Adicionar bot Lark no grupo GG

Modified by Gustavo Almeida · 2026-07-28 (sessão ZCode com Kimi K3)