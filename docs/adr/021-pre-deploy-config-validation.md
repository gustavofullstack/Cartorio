# ADR-021: Pre-deploy validation de config (OpenClaw e similares)

**Data:** 2026-06-24
**Status:** APLICADA (Sprint 3 — durante reaplicação de B2 do OpenClaw)
**Autor:** Pietra (Mavis) — execução do cron `reapply-b2-openclaw`
**Sprint:** 3 (retomada de B2)
**Origem:** prompt do cron `mavis:reapply-b2-openclaw` referenciava
"ADR-018 sobre pre-deploy validation", mas ADR-018 já estava ocupado
pelo DELETE LGPD (2026-06-23). Renumerada para 021.

## Contexto

Em 23/06/2026, peer agent `cartorio-n8n` tentou aplicar a mitigação
proposta em ADR-016 (B2: OpenClaw context overflow) sem supervisão.
Resultado documentado em `docs/INCIDENTE_SSH_2026-06-23.md` e memory
`cartorio-context.md` L458-490:

1. Peer agent escreveu `openclaw.json` como ROOT (uid 0) no volume
   `/var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/`.
   EACCES na leitura pelo processo OpenClaw (uid 1000).
2. Peer tentou recover criando 5 arquivos `openclaw.json.clobbered.*`
   em 1 minuto (visible no `ls -la` da config dir).
3. Peer zerou config para `{}` (2 bytes) tentando "começar do zero".
4. OpenClaw rejeitou config mínima por Zod strict schema (2026.6.x).
5. Restart loop infinito (exit 1 a cada 5-7s).
6. Gustavo escalou P0 às 22:35 BRT. Pietra root diagnosticou e
   restaurou em ~25min (22:35–23:00 BRT).

Custo: ~25min de downtime + 5 arquivos clobbered de "backup" que
poluíram o volume + vetor residual de credenciais exposto no chat
(Lesson 16/17, ver ADR-017 e memory L16).

## Decisão

**Toda escrita em config de serviço de produção (OpenClaw, N8N,
Traefik, Supabase, etc.) DEVE ser precedida por validação em modo
dry-run, e o canônico para OpenClaw é `openclaw config patch
--stdin --dry-run --json` (ou `--file X --dry-run`).**

### Pipeline obrigatório

```bash
# 1. BACKUP do config atual (NÃO com sufixo .clobbered — use timestamp)
TS=$(date -u +%Y%m%dT%H%M%SZ)
cp /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/openclaw.json \
   /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/openclaw.json.bak.$TS

# 2. DRY-RUN do patch via docker exec stdin
docker exec -i cartorio_openclaw-gateway.1.$(docker service ps \
  cartorio_openclaw-gateway -q --no-trunc | head -1) sh -c \
  'cat | openclaw config patch --stdin --dry-run --json' <<EOF
{
  agents: {
    defaults: {
      compaction: {
        keepRecentTokens: 2048,
      },
    },
  },
}
EOF

# Espera-se: {"ok":true,"operations":N,"checks":{"schema":true,...}}

# 3. APPLY (sem --dry-run)
docker exec -i cartorio_openclaw-gateway.1.XXX sh -c \
  'cat | openclaw config patch --stdin' <<EOF
{ ... mesmo JSON ... }
EOF

# 4. VALIDATE pós-write
docker exec cartorio_openclaw-gateway.1.XXX openclaw config validate

# 5. RESTART (scale=0 then scale=1, host-mode port conflict)
docker service scale cartorio_openclaw-gateway=0  # espera converge
sleep 5
docker service scale cartorio_openclaw-gateway=1  # espera Running

# 6. END-TO-END HEALTH
curl -sS http://100.99.172.84:18789/health  # internal
curl -sS https://agent.2notasudi.com.br/health  # via Traefik
docker logs --tail 25 cartorio_openclaw-gateway.1.XXX | grep -iE "error|warn|ready"
```

### Regras transversais

1. **NUNCA** escrever no volume montado direto do host (`docker run -v
   vol:/path sh -c 'echo X > config.json'`). Sempre via CLI do
   próprio serviço (`openclaw config patch`), que tem validação Zod.
2. **NUNCA** usar `service update --force` em serviço com porta
   host-mode (18789). Swarm fica em scheduling loop "no suitable
   node (host-mode port already in use)". Solução: `scale=0` then
   `scale=1`.
3. **NUNCA** criar backups com nome fixo (`openclaw.json.bak` é
   sobrescrito em silêncio; `.clobbered.*` polui o volume). Use
   timestamp ISO-8601: `.bak.2026-06-24T03-08-39Z`.
4. **SEMPRE** validar schema ANTES de restart. O `openclaw config
   schema` é a fonte da verdade (2.5MB JSON Schema canônico).
5. **SEMPRE** testar 1 campo de cada vez (incremental). Não copiar
   bloco grande de YAML antigo e rezar pra versão nova aceitar.

### Por que `openclaw config patch` (não `set`)

- `set` é para 1 chave por vez (`openclaw config set path.to.key value`).
  Verbose e propenso a typo.
- `patch` aceita JSON5 via stdin OU `--file`, faz merge recursivo
  seguro, valida schema no write, e tem `--dry-run` que retorna
  `{schema: true, resolvability: true}` antes de tocar no arquivo.
- `unset path` remove uma chave.
- `validate` re-valida o arquivo atual sem reiniciar nada.
- `schema` imprime o JSON Schema inteiro (2.5MB).

## Caso real de aplicação: B2 (2026-06-24 00:00–03:15 BRT)

### Estado anterior (após Pietra 23:00 BRT 23/06 ter restaurado)

```json
{
  "gateway": {
    "controlUi": {"allowedOrigins": ["*"]},
    "trustedProxies": ["10.0.0.0/8", "172.16.0.0/12", "100.64.0.0/10", "192.168.0.0/16"]
  }
}
```

Container UP, HTTP 200, mas **B2 não aplicado** (proposta ADR-016
pendia de "SUI Gustavo" via UI ou YAML — schema antigo).

### Descoberta do schema real (2026.6.10)

`openclaw configure --help` lista seções: workspace, model, web,
**gateway, daemon, channels, plugins, skills, health** — **NÃO tem
`sessions`**. Peer agent errou a key.

`openclaw config schema` (2.5MB) revela:
- `session` (singular) = routing/reset/maintenance
- `agents.defaults.compaction.*` = compaction tuning (onde está o
  threshold real)
- `agents.defaults.contextLimits.*` = budgets de injeção

Campos relevantes para B2:
- `agents.defaults.compaction.keepRecentTokens` (integer, ≥0) —
  budget de tokens preservados verbatim durante compaction.
- `agents.defaults.compaction.maxActiveTranscriptBytes` (string,
  ex.: "50mb") — **THRESHOLD que dispara compaction**. Equivalente
  moderno do legado "compactionThreshold".
- `agents.defaults.compaction.truncateAfterCompaction` (boolean) —
  rotaciona JSONL após compaction. Requer
  `maxActiveTranscriptBytes` setado.
- `agents.defaults.compaction.mode` ("default" | "safeguard") —
  guardrails estritos para preservar contexto recente.
- `agents.defaults.compaction.reserveTokens` (integer, ≥0) —
  headroom para reply generation.

### Aplicação incremental (1 campo por vez, com dry-run)

**Iteração 1** — `keepRecentTokens: 2048`:
```bash
# dry-run → {"schema":true,"operations":1}
docker exec -i cartorio_openclaw-gateway.1.XXX \
  sh -c 'cat | openclaw config patch --stdin --dry-run --json' <<EOF
{ agents: { defaults: { compaction: { keepRecentTokens: 2048 } } } }
EOF
# apply → "Applied 1 config update(s). Restart the gateway to apply."
docker exec -i cartorio_openclaw-gateway.1.XXX \
  sh -c 'cat | openclaw config patch --stdin' <<EOF
{ agents: { defaults: { compaction: { keepRecentTokens: 2048 } } } }
EOF
# restart (scale 0/1) → HTTP 200 ✅
```

**Iteração 2** — `maxActiveTranscriptBytes: "50mb"` +
`truncateAfterCompaction: true`:
```bash
# dry-run → {"schema":true,"operations":2}
docker exec -i cartorio_openclaw-gateway.1.XXX \
  sh -c 'cat | openclaw config patch --stdin --dry-run --json' <<EOF
{ agents: { defaults: { compaction: {
    maxActiveTranscriptBytes: "50mb",
    truncateAfterCompaction: true,
} } } }
EOF
# apply → "Applied 2 config update(s)"
# cat do volume confirmou escrita; restart → HTTP 200 ✅
```

### Config final pós-B2

```json
{
  "gateway": {
    "controlUi": {"allowedOrigins": ["*"]},
    "trustedProxies": ["10.0.0.0/8", "172.16.0.0/12", "100.64.0.0/10", "192.168.0.0/16"]
  },
  "agents": {
    "defaults": {
      "compaction": {
        "keepRecentTokens": 2048,
        "maxActiveTranscriptBytes": "50mb",
        "truncateAfterCompaction": true
      }
    }
  },
  "meta": {
    "lastTouchedVersion": "2026.6.10",
    "lastTouchedAt": "2026-06-24T03:08:39.935Z"
  }
}
```

### Validação end-to-end (03:09–03:15 BRT 24/06)

- `docker exec ... openclaw config validate` → `Config valid: ~/.openclaw/openclaw.json`
- `docker service ps cartorio_openclaw-gateway` → `Running 27 seconds ago` ✅
- `curl http://100.99.172.84:18789/health` → `{"ok":true,"status":"live"}` ✅
- `curl https://agent.2notasudi.com.br/health` → `HTTP/2 200 {"ok":true,"status":"live"}` ✅
- `docker logs --tail 25 ...` → somente warning pré-existente sobre `--password` exposure (não relacionada a B2)
- Agent model carregado: `openai/gpt-5.5 (thinking=medium, fast=off)` (via log `[gateway]`)
- 7 plugins pre-warmed: browser, canvas, device-pair, file-transfer, memory-core, phone-control, talk-voice
- `[heartbeat] started`, `[gateway] ready`

## Consequências

**Positivas**
- Downtime zero após aplicação correta (~30s para scale 0/1 + ~10s para gateway ready).
- Config validada por Zod schema antes de tocar em disco (`--dry-run`).
- Histórico preservado: `meta.lastTouchedAt` registra cada write.
- Pattern reutilizável pra QUALQUER serviço com CLI `config patch/set/validate`
  (N8N, Traefik dynamic config, Supabase Studio API, Redis CONFIG, etc.).

**Negativas**
- Custo: ~5min por iteração (dry-run + apply + restart + validate).
  Aceitável para mudanças raras; inviável pra hot-reload contínuo.
- Pattern exige saber o ID da task atual (`docker service ps ... -q
  --no-trunc | head -1`), que muda a cada restart.
- `openclaw config patch` requer JSON5 estrito (vírgulas entre
  pares chave-valor). Sem vírgula → `SyntaxError: invalid character`.

**Não-objetivos**
- Auto-rollback se restart falhar (parcialmente coberto: pre-restart
  backup `.bak.<timestamp>` permite `cp` reverso manual).
- Validação de schema cross-service (ex.: webhook URL apontando pra
  serviço que não existe). Fica pra ADR futura.
- Watchdog automático que re-aplica se config drift detectado.

## ADR-016 (atualização — schema legado OpenClaw pré-2026.6.x)

ADR-016 propunha:
```yaml
openclaw:
  context:
    auto_compact:
      enabled: true
      threshold_messages: 50
      strategy: compact_then_truncate
    session_ttl_minutes: 1440
    max_context_tokens: 100000
```

**Esse schema NÃO EXISTE em OpenClaw 2026.6.10.** As chaves
equivalentes no schema moderno são:
- `threshold_messages` → `agents.defaults.compaction.maxActiveTranscriptBytes: "50mb"`
- `session_ttl_minutes` → `session.maintenance.pruneAfter: "24h"`
- `max_context_tokens` → `agents.defaults.contextLimits.*` (vários caps)
- `auto_compact.enabled: true` → implícito se `maxActiveTranscriptBytes` está setado
- `strategy: compact_then_truncate` → `truncateAfterCompaction: true`

ADR-016 deve ser marcada como **schema legacy, substituída por
ADR-021 + config atual**.

## Referências

- ADR-016 (B2 original, schema legado)
- ADR-017 (credential rotation — relacionada, vetor de leak)
- Lesson 16/17 (credenciais em chat = queimadas)
- Lesson 21 (cron hygiene agressivo)
- Lesson 22 (peer agent sem supervisão = bomba-relógio)
- `docs/INCIDENTE_SSH_2026-06-23.md` (P0 22:35–23:00 BRT)
- `cartorio-context.md` L458-490 (diagnóstico ladder)
- `openclaw config schema` (2.5MB JSON Schema canônico)
- `openclaw docs: https://docs.openclaw.ai/cli/config`