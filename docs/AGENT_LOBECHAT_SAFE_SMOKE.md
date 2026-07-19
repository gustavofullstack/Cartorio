# Smoke seguro — Agente Cartório / LobeChat

Este smoke valida exclusivamente disponibilidade e configuração de borda. Ele **não autentica**, **não cria atendimento**, **não chama tools/MCP**, **não envia mensagem de chat** e **não inclui PII**. Assim, pode ser executado contra o ambiente público de teste sem registrar dados pessoais em OpenClaw, LobeChat ou provedores de modelo.

```bash
python3 scripts/smoke_cartorio_agent.py
# Para um gate que exige também o DNS/branded proxy:
python3 scripts/smoke_cartorio_agent.py --strict-canonical --json
```

## Domínios e responsabilidade

| Finalidade | URL | Estado esperado hoje | Uso no smoke |
|---|---|---|---|
| Teste EasyPanel | `https://cartorio-lobechat.dfgdxq.easypanel.host` | rota transitória do serviço | obrigatório; `/api/health`, com fallback explícito `/health` quando o proxy não expõe o primeiro path |
| DNS canônico | `https://lobe.2notasudi.com.br` | alvo de produção; depende de Cloudflare + router Traefik | observado como aviso por padrão; obrigatório com `--strict-canonical` |
| Gateway OpenClaw | `https://agent.2notasudi.com.br` | gateway canônico | `/health`, OPTIONS CORS e conexão WSS até `connect.challenge` |

O hostname EasyPanel **não substitui** o DNS canônico e não deve ser apresentado como URL pública final. A ativação do canônico requer uma alteração explícita de infraestrutura: criar o registro DNS, aplicar o router Traefik e configurar CORS para a origem final. Este smoke não executa nenhuma dessas alterações.

## Critérios validados

1. `GET /health` do OpenClaw responde 200.
2. A rota EasyPanel do LobeChat responde em endpoint de health sem entrar no chat autenticado.
3. O DNS/proxy canônico é reportado separadamente, para não mascarar a pendência de branding.
4. O preflight `OPTIONS /v1/chat/completions` aceita a origem EasyPanel e devolve `Access-Control-Allow-Origin` compatível. Nenhum `Authorization` é enviado.
5. O cliente abre `wss://agent.2notasudi.com.br/v1/chat`, apenas recebe `connect.challenge` e fecha. Ele não responde o desafio, não envia `auth.challenge` e não envia conteúdo de usuário.

Falha de CORS ou do desafio WSS é erro essencial; DNS/proxy canônico é aviso até a decisão/aplicação de DNS e vira erro com `--strict-canonical`.

## Evidência e próximo passo seguro

O comando produz somente nomes de checks, códigos HTTP, paths e categorias de exceção. Não imprime corpo de resposta, headers recebidos, tokens, nonces ou dados de usuário. Após o smoke verde, o próximo passo é um teste de chat com uma conta de serviço de escopo mínimo, usando texto sintético sem PII e consentimento/HITL; isso é deliberadamente outro teste.

Cross-references: [STATUS.md](../infra/lobechat/STATUS.md), [Traefik template](../infra/traefik/lobechat-openclaw-routing-g8.yaml), [CORS remediation runbook](../infra/scripts/openclaw_fix_lobechat_cors_timeout.sh).
