# Lark Bot v4 — Runbook completo (com visão OCR)

> Quando você voltar do Mac, segue esses passos na ordem. **15min totais.**

## TL;DR

Bot standalone que escuta o grupo GG do Lark, manda pergunta pro PIETRA VPS (`api.2notasudi.com.br`), responde no grupo. Roda 24/7 via LaunchAgent. **v4 tem OCR** — quando você manda foto de documento, ele extrai texto (tesseract) e manda pro PIETRA analisar.

---

## 0. Pré-requisitos (já tem, só conferir)

- ✓ Python 3.11+ (no Mac)
- ✓ uv instalado
- ✓ Conta Lark/Feishu
- ✓ Acesso ao Developer Console do Lark

## 1. Criar app custom bot no Lark

**Lark global:** https://open.larksuite.com → Developer Console → Create App → Custom App
**Feishu China:** https://open.feishu.cn → Developer Console → Create App → Custom App

Nome sugerido: **"Pietra Lark Bot"** ou **"Cartorio 2 Notas"**

### Permissões (Permissions tab)

| Permissão | Pra quê | Obrigatório |
|---|---|---|
| `im:message` | Mandar e ler mensagens | ✓ |
| `im:message.group_at_msg` | Receber @ no grupo | ✓ |
| `im:message.group_msg` | Ler TUDO no grupo (sem @) | ✓ (pra responder tudo) |
| `im:message.p2_msg` | DM | opcional |
| `im:chat` | Listar chats | opcional |
| `im:media` | Receber/enviar imagem | ✓ |
| `im:media:download` | Baixar arquivos | ✓ |

Clica **Save** → aguarda nova aprovação.

## 2. Event Subscription

Menu lateral → **Event Subscriptions**:

- **Request URL:** `https://<TUNNEL>/lark/webhook` (preencher depois do passo 4)
- **Verification Token:** copia e salva
- **Encrypt Key:** copia e salva (opcional)

Em **Add Events**, marca:
- `im.message.receive_v1`

Clica **Save** (sem URL válida ainda, vai dar erro — tudo bem).

## 3. Credenciais

Menu lateral → **Basic Information** → **Credentials**:

- **App ID** (começa com `cli_...`)
- **App Secret** (string longa)

## 4. Subir o tunnel (cloudflared named tunnel)

**Named tunnel = URL fixa que não muda.** Sem isso, URL temporária muda a cada restart e você precisa atualizar o Developer Console.

```bash
# Login uma vez (abre browser)
cloudflared tunnel login

# Cria tunnel nomeado
cloudflared tunnel create lark-bot

# Cria config
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml <<'EOF'
tunnel: lark-bot
credentials-file: /Users/gustavoalmeida/.cloudflared/<UUID>.json

ingress:
  - hostname: lark-bot.seudominio.com  # ou use *.trycloudflare.com (temporário)
    service: http://localhost:8080
  - service: http_status:404
EOF

# Sobe o tunnel (deixa rodando)
cloudflared tunnel run lark-bot
```

**Se não tem domínio**: usa `--url` temporário:
```bash
cloudflared tunnel --url http://localhost:8080
# Copia URL https://xxx.trycloudflare.com que aparecer
```

## 5. Configurar `.env.lark`

```bash
cat > /Users/gustavoalmeida/Projetos/Cartorio/scripts/.env.lark <<'EOF'
LARK_APP_ID=cli_xxxxxxxx
LARK_APP_SECRET=xxxxxxxxxxxxxxxx
LARK_VERIFICATION_TOKEN=xxxxxxxxxxxxxxxx
# LARK_ENCRYPT_KEY=opcional
LARK_QUIET_GROUP=false          # true = só @; false = responde tudo
PIETRA_BASE=https://api.2notasudi.com.br
LARK_BOT_PORT=8080
EOF
chmod 600 /Users/gustavoalmeida/Projetos/Cartorio/scripts/.env.lark
```

**Pra carregar o .env em cada run**, o LaunchAgent já tem vars hardcoded. Pra rodar manual:
```bash
set -a && source /Users/gustavoalmeida/Projetos/Cartorio/scripts/.env.lark && set +a
```

## 6. Teste manual (1 min)

```bash
cd /Users/gustavoalmeida/Projetos/Cartorio/scripts
uv run --with flask --with requests --with pillow python3 lark_bot_v4.py
```

Saída esperada:
```
[..] [INFO] lark bot v4 starting port=8081 ocr=True lang=por+eng
 * Running on http://0.0.0.0:8081
```

Outro terminal:
```bash
curl http://localhost:8081/health
# {"bot":"v4 ok","lark_configured":true,"pietra_ok":true,"ocr_available":true,...}
```

## 7. Colar URL no Lark

Pega URL do cloudflared (`https://xxx.trycloudflare.com/lark/webhook` ou `https://lark-bot.seudominio.com/lark/webhook`) e cola no **Event Subscription → Request URL** no Developer Console.

Clica **Save** — Lark vai mandar challenge pro seu server. Se respondeu, fica verde ✓.

## 8. Instalar LaunchAgent (24/7)

Já tá criado em `~/Library/LaunchAgents/ai.zcode.lark-bot.plist`.

```bash
# Carregar
launchctl load ~/Library/LaunchAgents/ai.zcode.lark-bot.plist

# Verificar
launchctl list | grep lark-bot

# Subir agora
launchctl kickstart -k gui/$(id -u)/ai.zcode.lark-bot

# Logs
tail -f ~/.lark_bot_v3.log
tail -f ~/.lark_bot_v3.err.log
```

## 9. Adicionar bot no grupo GG

No Lark:
1. Abre grupo **GG**
2. **Settings** (engrenagem) → **Bots** → **Add Bot**
3. Procura "Pietra Lark Bot"
4. Adiciona
5. **Promove a admin** (Members → Bot → Set as Admin) — **essencial** pra ouvir tudo

## 10. Testar

No grupo GG:
- Manda `!ajuda` → lista comandos
- Manda `!saude` → status bot + PIETRA
- Manda `oi, qual seu nome?` → PIETRA responde "Sou a Pietra..."
- Manda uma foto → bot baixa, manda pro PIETRA, ecoa resposta

---

## Troubleshooting

### Bot não responde
1. `curl http://localhost:8080/health` — bot vivo?
2. `launchctl list | grep lark-bot` — LaunchAgent rodando?
3. `tail ~/.lark_bot_v3.err.log` — erro python?
4. `cloudflared tunnel info lark-bot` — tunnel ativo?
5. Developer Console → Event Subscriptions → URL tem ✓?

### Bot responde "Pietra indisponível"
1. `curl https://api.2notasudi.com.br/api/v1/pietra/health` — VPS ok?
2. Se VPS down → aguardar, bot retenta sozinho
3. Se VPS ok mas bot fala indisponível → ver log do server (WARN/ERR)

### Bot não vê mensagens sem @
1. Bot não é admin do grupo → promover
2. Permissão `im:message.group_msg` não liberada → Developer Console
3. App não foi "released" → App Launch → Create Version → Release

### URL do tunnel mudou
- Named tunnel: não muda (é o ponto de usar named)
- Temporário: muda a cada restart. Refazer passo 7.

---

## Comandos úteis depois

```bash
# Status
launchctl list | grep lark-bot
curl http://localhost:8080/health

# Logs ao vivo
tail -f ~/.lark_bot_v3.log

# Restart
launchctl kickstart -k gui/$(id -u)/ai.zcode.lark-bot

# Parar
launchctl unload ~/Library/LaunchAgents/ai.zcode.lark-bot.plist

# Ver audit log
sqlite3 ~/.lark_bot_v3.sqlite "SELECT datetime(ts,'unixepoch'), sender, msg_type, content_in FROM events ORDER BY id DESC LIMIT 20"

# Ver inbox (arquivos/imagens recebidos)
ls -lat ~/Downloads/lark_inbox/ | head
```

---

## O que o bot FAZ (v6 com detector + memória + admin)

- ✓ Recebe msg no grupo GG
- ✓ Encaminha pro PIETRA VPS
- ✓ Responde com persona canônica "Sou a Pietra..."
- ✓ PII scrub feito pelo backend (LGPD)
- ✓ Identity guard HARD-STOP (sem leak "Sou o Hermes")
- ✓ Tools MCP funcionam (cálculo emolumento, protocolo, agendamento)
- ✓ Audit log local
- ✓ **Imagem: baixa + OCR (tesseract) + LGPD scrub + detector de tipo**
- ✓ **Detector automático**: CPF, RG, CNH, PROCURAÇÃO, ESCRITURA, CONTRATO, RECEITA, FATURA, PROTOCOLO
- ✓ **Resumo automático** se msg > 500 chars
- ✓ **Memória por chat** salva no Postgres do cartório (PIETRA VPS)
- ✓ Arquivo: baixa pra `~/Downloads/lark_inbox/`, mostra conteúdo se for texto/code
- ✓ Rate limit: 10 msg/min por chat
- ✓ Comandos: `!ajuda`, `!saude`, `!modelo`, `!ocr <lang>`, `!stats`, `!doc`, `!reset`
- ✓ **Owner only**: `!bot stop`, `!bot restart`, `!broadcast <msg>`

## Detector de tipo de documento

Quando bot recebe msg com OCR ou texto, detecta automaticamente:

| Padrão no texto | Tipo detectado |
|---|---|
| `123.456.789-00` | CPF |
| `RG: 12.345.678-9` | RG |
| `CNH` / `habilitacao` | CNH |
| `procuracao` / `substabelecimento` | PROCURAÇÃO |
| `escritura` / `compra e venda` | ESCRITURA |
| `contrato` / `clausula` | CONTRATO |
| `receita` / `medicamento` | RECEITA MÉDICA |
| `fatura` / `boleto` / `vencimento` | FATURA |
| `protocolo 12345` | PROTOCOLO CARTÓRIO |

PIETRA recebe `[DOC DETECTADO: PROCURAÇÃO — procuração]` no contexto, e adapta a resposta.

## Comandos novos (v6)

```
!stats                    — n_msgs, n_chats, n_ocr
!doc <texto>              — testa detector sem mandar imagem
!broadcast <msg>          — owner only: envia pra todos os chats
!bot stop / !bot restart  — owner only
```

Setar owner: export `LARK_OWNER_OPEN_ID=ou_seu_id_aqui` no .env.lark

## O que NÃO faz (limitações conhecidas)

- ✗ Não envia imagem de volta (só eco da recebida)
- ✗ Não edita mensagem enviada
- ✗ Não faz thread/reply estruturado
- ✗ Não reage com emoji
- ✗ Memória curta (10 msgs no contexto) — longa é no Postgres da VPS
- ✗ Não fala em canal DM se bot não tiver `im:message.p2_msg`

Modified by Gustavo Almeida · 2026-07-28