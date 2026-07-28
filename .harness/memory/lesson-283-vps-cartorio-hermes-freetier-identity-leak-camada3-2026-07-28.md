# Lesson 283 — VPS `cartorio_hermes` free-tier fallback = Camada 3 do identity leak

**Data:** 2026-07-28
**Severidade:** P0
**Squad:** cartorio-dev + cartorio-lgpd (review)
**Relacionado:** Lesson 282 (defense-in-depth identity leak), F3 do relatório IMENSAGER 2026-07-28

## Contexto

`cartorio_hermes` (serviço no VPS 187.77.236.77) está configurado com
models **free-tier** como fallback primário:

```yaml
# /opt/data/config.yaml do VPS (achado F3)
models:
  primary: minimax/m1-m3
  fallback:
    - deepseek-v4-flash-free     # ← vaza persona
    - nemotron-3-ultra-free      # ← vaza persona
    - qwen-3-coder-free
    - llama-3.3-70b-free
```

Quando quota do MiniMax estoura (rate-limit 429), `cartorio_hermes`
faz fallback para **deepseek/nemotron free**. Esses modelos:
- Não conhecem a persona PIETRA do SOUL.md
- Não têm `system prompt` reforçado no adapter
- Geram "Sou o Hermes, atendente virtual oficial..." naturalmente

O **identity guard local** (`backend/app/services/pietra_identity_guard.py`,
195 linhas, commit `fce886f7`) pega o leak **em ~85% dos casos** via regex
pós-LLM. Mas:
- **REG-001** (Harness 100): dedup_violation — guard não consegue substituir
  porque a resposta inteira já veio "Sou o Hermes..." em 4 frases antes dele
  agir.
- **REG-003** (Crítico 10): guard pegou mas perdeu contexto canônico
  ("Sou a Pietra, agente do 2º Cartório de Notas de Uberlândia").

## Root cause

A **Camada 3** do defense-in-depth (Lesson 282) estava incompleta:

| Camada | Componente | Estado |
|---|---|---|
| 1 | SOUL.md persona | ✅ OK (131 linhas canônicas) |
| 2 | System prompt reforçado | ✅ OK |
| 3 | **Model binding** | ❌ **Falha — fallback free-tier** |
| 4 | Identity guard pós-LLM | ✅ Mitiga 85% |

## Fix aplicado

Patch script: `scripts/vps_fix_cartorio_hermes_F3.sh`

1. Backup `/opt/data/config.yaml` → `config.yaml.bak-F3fix-YYYYMMDD_HHMMSS`
2. Substitui qualquer `*-free` por `minimax/m1-m3`
3. Adiciona guard no YAML:
   ```yaml
   model_allow_free_tier_fallback: false
   minimax_m3_required: true
   ```
4. `docker service update --force cartorio_hermes`
5. Probe: `curl POST /v1/chat` esperando "Sou a Pietra..."

## Validação (P0 close criteria)

- [ ] Patch aplicado no VPS
- [ ] Probe direto retorna "Sou a Pietra, agente do 2º Cartório..."
- [ ] Campanha IMENSAGER Fase 3 (outbound) N≥30, 0 identity_leak
- [ ] STATUS.md atualizado: `P0 IDENTITY_HERMES_LEAK FECHADO`
- [ ] Lesson 283 mergeada no MEMORY.md

## Rollback

```bash
ssh root@187.77.236.77 "
  cp /opt/data/config.yaml.bak-F3fix-<TIMESTAMP> /opt/data/config.yaml
  docker service update --force cartorio_hermes
"
```

## Lições generalizáveis

1. **Fallback free-tier é anti-padrão em agent de produção** — se a quota
   estourar, melhor dar erro explícito ao cliente do que responder com um
   LLM fraco que vaza persona.
2. **Defense-in-depth incompleto é pior que ausente** — gera falso sinal
   de "está protegido" (o guard pega 85%, parecem seguros) enquanto 15%
   vaza em produção.
3. **P0 não fecha sem N≥30 evidência pós-fix** — regra já existente no
   STATUS.md. Harness 100 (4 fail) + Crítico 10 (3 fail) **NÃO fecham P0**.
4. **VPS-side config é cego para o dev local** — o `~/.hermes/profiles/cartorio/config.yaml`
   é local. O `cartorio_hermes` tem config próprio no VPS. Sempre que mexer
   em identidade/persona, verificar AMBOS os lados.

Modified by Gustavo Almeida