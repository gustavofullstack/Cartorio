# Lark Bot Setup — passo-a-passo

> Pra você (Gustavo) colocar o bot que eu escrevi (`scripts/lark_bot_server.py`)
> no grupo **GG** que você criou.

## 0. Pré-requisitos

- Python 3.11+ ✓ (já tem no Mac)
- `pip install flask requests` ✓ (rode `uv pip install flask requests` se não tiver)
- Conta Lark ou Feishu

## 1. Criar app no Developer Console

**Lark global:**
https://open.larksuite.com → **Developer Console** → **Create App** → **Custom App**

**Feishu China:**
https://open.feishu.cn → **Developer Console** → **Create App** → **Custom App**

Dá um nome tipo **"Gustavo Bot"** ou **"ZCode Assistant"**.

## 2. Configurar permissões

Menu lateral → **Permissions** → procura e adiciona:

| Permissão | Scope | Pra quê |
|---|---|---|
| `im:message` | `im:message` | Mandar e ler mensagens |
| `im:message:readonly` | — | Ler histórico |
| `im:message.group_at_msg` | — | Receber evento quando @mencionado no grupo |
| `im:message.p2_msg` | — | Mensagens diretas (DM) |
| `im:chat` | — | Listar chats e membros |
| `im:chat:readonly` | — | Ler info de chats |

**Pra ouvir SEM @** no grupo GG (mais agressivo, pode precisar aprovação):
- Adiciona também `im:message.group_msg`
- **OU** promove o bot a **admin** do grupo (Group Settings → Members → Bot → Set as Admin)

Clique **Save** → vai aparecer um pop-up pedindo nova aprovação de permissões.

## 3. Event Subscription

Menu lateral → **Event Subscriptions**:

- **Request URL:** `https://<SEU-TUNNEL>/lark/webhook` (você preenche depois de subir o tunnel)
- **Verification Token:** copia e salva (vai pro .env)
- **Encrypt Key** (opcional): copia e salva

Em **Add Events**, marca:
- `im.message.receive_v1` — recebe mensagens
- `im.message.message_read_v1` — quando alguém lê (opcional)

## 4. Credenciais

Menu lateral → **Basic Information** → **Credentials**:
- Copia **App ID** (começa com `cli_...`)
- Copia **App Secret** (string longa)

## 5. Preencher `.env`

Cria/edita `/Users/gustavoalmeida/Projetos/Cartorio/scripts/.env.lark`:

```bash
LARK_APP_ID=cli_xxxxxxxxxxxxxxxx
LARK_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
LARK_VERIFICATION_TOKEN=xxxxxxxxxxxxxxxx
# LARK_ENCRYPT_KEY=opcional
LARK_BOT_PORT=8080
```

## 6. Subir o bot

```bash
cd /Users/gustavoalmeida/Projetos/Cartorio/scripts
uv pip install flask requests
set -a && source .env.lark && set +a
python3 lark_bot_server.py
```

Saída esperada:
```
[..] [INFO] starting lark bot server port=8080 app_id_set=True
 * Running on http://0.0.0.0:8080
```

## 7. Expor pro Lark (tunnel público)

O Lark precisa alcançar seu `localhost:8080`. Use `cloudflared` (grátis, sem cadastro):

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8080
```

Ele vai printar algo tipo:
```
https://xxxx-xxxx-xxxx.trycloudflare.com
```

**Copia essa URL** e volta no passo 3:
- Cola `https://xxxx.trycloudflare.com/lark/webhook` em **Request URL**
- Clica **Save** — Lark vai mandar um `url_verification` challenge pro seu server
- Se o server respondeu com `{"challenge": "..."}`, vai ficar verde ✓

## 8. Adicionar bot ao grupo GG

1. Abre o Lark
2. Vai no grupo **GG**
3. **Group Settings** (engrenagem) → **Bots** → **Add Bot**
4. Procura **"Gustavo Bot"** (ou o nome que você deu)
5. Adiciona
6. **Importante:** marca permissão **"Read all messages"** se quiser que eu ouça tudo (não só @mencionado)

## 9. Testar

No grupo GG, manda:
```
@Gustavo Bot oi
```

OU (se você ativou "read all"):
```
!oi
```

Deve responder com o echo + timestamp.

## Troubleshooting

**Bot não responde:**
- Verifica que o cloudflared tá rodando
- Verifica que o server tá no ar: `curl http://localhost:8080/health`
- Verifica que Request URL tá exatamente `https://...trycloudflare.com/lark/webhook`
- Verifica o log do server (tem que aparecer "event received")

**Bot não recebe mensagem do grupo:**
- Falta permissão `im:message.group_at_msg` ou `im:message.group_msg`
- Bot precisa ser adicionado manualmente nas settings do grupo
- Versão do app precisa estar **released** (não só em dev)

**Erro "tenant_access_token failed":**
- App ID/Secret errado
- App não publicado (precisa App Launch → Release)

## Próximos passos (depois de funcionando)

- Plugar LLM real no `handle_message` (chamar PIETRA via MCP ou outro agent)
- Persistir contexto (Redis ou Postgres)
- Salvar mensagens no audit_log
- LGPD: mascarar PII antes de logar

Modified by Gustavo Almeida · 2026-07-28