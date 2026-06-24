# OpenClaw Persona Reload Procedure

OpenClaw agents load persona files (`SOUL.md`, `IDENTITY.md`, `USER.md`, `TOOLS.md`, `AGENTS.md`) at **session wake**, not continuously. So if you change the files, the **next NEW session** will read the updated content. Existing sessions keep the cached version.

## When to reload

- After editing any of: `SOUL.md`, `IDENTITY.md`, `USER.md`, `TOOLS.md`, `AGENTS.md`
- After changing the LLM provider config
- After adding a new skill

## Reload procedure (3 opções, em ordem de eficiência)

### Opção 1: New session (RECOMENDADO, sem restart)

1. No OpenClaw Control UI (`https://vps-cartorio.tail2fe279.ts.net/?token=...`)
2. Clicar **`+ New session`** no menu esquerdo
3. Dar um nome (ex: "CartorioBot v2")
4. Enviar primeira mensagem — o agent vai ler os arquivos novos no wake

**Vantagem**: Zero downtime, não desconecta outros clients pareados.
**Desvantagem**: A sessão antiga continua com a persona antiga.

### Opção 2: Restart do gateway (FORÇADO)

```bash
ssh cartorio 'docker service update --force cartorio_openclaw-gateway'
sleep 10
ssh cartorio 'docker exec $(docker ps -q --filter "name=cartorio_openclaw-gateway") curl -s http://127.0.0.1:18789/health'
# {"ok":true,"status":"live"}
```

**Vantagem**: Todas as sessões leem a persona nova.
**Desvantagem**: Desconecta todos os clients pareados (precisam re-aprovar device pairing).

### Opção 3: Reiniciar apenas o container (MAIS AGRESSIVO)

```bash
ssh cartorio 'OCID=$(docker ps -q --filter "name=cartorio_openclaw-gateway"); docker kill $OCID; sleep 5; docker service ps cartorio_openclaw-gateway'
```

**Vantagem**: Limpa cache em memória.
**Desvantagem**: Mesmo impacto do Opção 2, mais agressivo.

## Verificar que a persona foi carregada

```bash
ssh cartorio 'OCID=$(docker ps -q --filter "name=cartorio_openclaw-gateway"); docker exec $OCID ls -la /home/node/.openclaw/workspace/SOUL.md'
# Verifica: SOUL.md com 4786 bytes = cartório persona
# Verifica: SOUL.md com 7835 bytes = default template (não carregou)
```

Ou, no chat, envie: `"Quem é você?"` e veja se responde como **CartórioBot** com tom mineiro-cordial.

## Editar persona (workflow)

1. Editar arquivo em `infra/openclaw-agent/workspace/` (este repo)
2. `git commit -m "chore(openclaw-agent): update SOUL.md <motivo>"`
3. `git push` (se aplicável) — ou só pro master local
4. Deploy:
   ```bash
   scp infra/openclaw-agent/workspace/SOUL.md cartorio:/tmp/
   ssh cartorio 'OCID=$(docker ps -q --filter "name=cartorio_openclaw-gateway"); docker cp /tmp/SOUL.md $OCID:/home/node/.openclaw/workspace/SOUL.md'
   ```
5. New session no Control UI para carregar
6. Testar: enviar mensagem, ver se persona é a nova

## Última migração de persona

- **Data:** 2026-06-23
- **De:** default template (SOUL.md 7835 bytes, sem contexto cartório)
- **Para:** CartórioBot persona (SOUL.md 4786 bytes, contexto cartório + LGPD + Tabela MG 2026)
- **Trigger:** Gustavo abriu OpenClaw Control UI, viu que o agent não tinha identidade
- **Pendência:** Old sessions (`agent:main:heartbeat-recov` 4h, `Main Session` 2m) ainda usam persona antiga até fechar

---

## Arquivos de persona (atualizado 2026-06-24)

- `SOUL.md` - proposito existencial (4786 bytes)
- `IDENTITY.md` - quem sou, tools, limites (2155 bytes)
- `USER.md` - sobre Gustavo (2415 bytes)
- `TOOLS.md` - notas tecnicas (4161 bytes)
- `GOALS.md` - objetivos do agent
- `AGENTS.md` - **NOVO 2026-06-24** - regras operacionais (thinkings, contexto 1M, modelo deepseek-v4-flash)
- `TELEGRAM.md` - **NOVO 2026-06-24** - bot Telegram 8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q

## Contexto 1M (NAO 131k)

OpenClaw UI pode mostrar "131.1k tokens" mas o **modelo real (deepseek-v4-flash) suporta 1M de contexto**. O que aparece na UI e' tokens consumidos NA sessao atual, NAO o maximo do modelo.

Para garantir contexto maximo:
```bash
openclaw config set max_context_tokens 1000000
openclaw config set max_output_tokens 8192
```

## Thinkings ADAPTATIVO

Thinkings (raciocinio explicito) liga automaticamente para:
- keywords: "calcular", "validar", "analisar", "debug", "LGPD", "PII", "erro", "exception"
- complexidade do prompt > 0.7
- tarefas de decisao critica (handoff, validacao juridica)

Para saudacoes e FAQ, fica desligado (economia de tokens).

Ver `AGENTS.md` para detalhes de implementacao.

Modified by ZCode/Mavis - 2026-06-24
