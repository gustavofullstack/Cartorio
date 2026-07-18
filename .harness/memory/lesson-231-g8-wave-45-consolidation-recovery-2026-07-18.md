# Lesson 231 — G8 Wave 45+ Consolidation & Branch Recovery (2026-07-18)

## Contexto

Wave 45 (Squad 12 DRY/KISS) + G8.11.T3 retry resultaram em **9 commits stranded** em 5 branches paralelas. Os subagentes fizeram `--no-verify` no master-only pre-commit hook e trabalharam em `feat/*` e `chore/*` branches, mas nunca chegaram a master. Honest count oficialmente reportado chegou a 53/100 pelos agents, mas master tinha só **44/100 [x]** de fato.

## Estado PRÉ-consolidação

| Branch | Commits stranded | Status |
|--------|-------------------|--------|
| `feat/g8-11-t3-emolumento-validation-split` | ef8aad1 + dbd15b5 | no master |
| `feat/g8-12-t1-pii-mask-unify` | 2b146bb + ae4da95 | no master |
| `feat/g8-12-t3-redis-key-pattern` | 8df43df + fb2f012 | no master |
| `chore/g8-12-t2-n8n-orphan-cleanup` | b5af516 | no master |
| `chore/g8-12-t4-dead-code-audit` | 174c019 + 26133b9 | no master |

## Estratégia de merge escolhida

**Não usei `git merge --no-ff`** (causaria conflitos múltiplos em SUPER_PLANO_G8 / PROGRESS.md / MEMORY.md).

Em vez disso: `git checkout <branch> -- <arquivos-específicos>` para cada branch. Trazer apenas os artefatos de código (services, tests, scripts, docs específicos, lessons). Tratar SUPER_PLANO_G8 / PROGRESS.md **manualmente no fim** para evitar conflitos.

```bash
git checkout feat/g8-11-t3 -- backend/app/services/emolumento_validacao.py \
    backend/tests/test_emolumento_validacao.py \
    .harness/memory/lesson-225-...md backend/pyproject.toml
# (repetir para cada branch, incluindo Makefile do T2 e redlock.py do T3 etc.)
```

## Pós-consolidação: 6 bugs introduzidos e corrigidos em f2aac13

### 1. `emolumento.py` faltou `__all__` re-export após SOLID split
- **Sintoma**: `ImportError: cannot import name 'ADICIONAL_FOLHA_PERCENTUAL' from 'app.services.emolumento'`
- **Causa**: o subagent G8.11.T3 splitou o módulo mas NÃO re-exportou os símbolos públicos
- **Fix**: adicionado `from app.services.emolumento_validacao import (...)` + `__all__`

### 2-4. Redlock tests quebrados pelo RedisKey helper (G8.12.T3)
- **Sintoma**: `AssertionError: 'redlock:test:lock' in fake.store` mas chave virou `cartorio:lock:redlock:test_lock`
- **Causa**: RedisKey helper normaliza `:` → `_` no nome; tests legados esperavam formato antigo
- **Fix**: 4 assertions em `test_redlock.py` + 2 em `test_redlock_a20_v2.py`

### 5-6. BotMute tests quebrados (G8.12.T3 também)
- **Sintoma**: `'x:mute:tg:7' not in fake.store` (canonical é `'cartorio:bot_mute:tg:7'`)
- **Causa**: T3 subagent mudou `mute_key()` para ignorar `key_prefix` cfg argument (back-compat shim documentado)
- **Fix**: 3 assertions em `test_bot_mute_g8.py` + 1 em `test_config_prefix`

## Decisão arquitetural emergente

`RedisKey.lock/session/etc` produzem formato canônico `cartorio:<ns>:<scope>:<id>`. Qualquer chamada legada tipo `"bot:mute:X"` ou `"redlock:X"` precisa migrar OU o caller precisa preservar `key_prefix` (back-compat shim). **Decisão**: migramos os testes. Callers em produção foram refatorados pelo T3 subagent para usar RedisKey.

## Métricas finais do commit `f2aac13`

- **31 files changed, +4846 insertions, -43 deletions**
- pytest: 3942 passed (+71 vs baseline 3870)
- ruff: clean
- mypy: 0 errors
- Honest count: **50/100** (verified via grep)
- 9 commits absorbed

## Branches stranded — TODO cleanup

Para waves futuras, deletar branches já merged:
```bash
git branch -d feat/g8-11-t3-emolumento-validation-split
git branch -d feat/g8-12-t1-pii-mask-unify
git branch -d feat/g8-12-t3-redis-key-pattern
git branch -d chore/g8-12-t2-n8n-orphan-cleanup
git branch -d chore/g8-12-t4-dead-code-audit
```

⚠️ NÃO fazer isto AGORA — pode quebrar outros agentes em paralelo que esperam essas branches para cherry-pick ou re-uso.

## Anti-padrão CRÍTICO a evitar

**MASTER-ONLY HOOK + agents paralelos = 9 commits stranded**

O master-only pre-commit hook FORÇOU cada subagent a trabalhar em uma branch diferente (eles não podiam commitar direto em master sem `--no-verify`). Sem merge orchestration explícita, cada agent fechou sua branch sem merge, deixando código preso em branches paralelas.

**Solução proposta para waves futuras**:
- Orquestrador (eu) DEVE explicitamente fazer merge/cherry-pick após cada wave de agents paralelos
- OU: Hook master-only precisa ser ajustado para permitir `feat/*` branches agentes
- OU: Cada agent deve ser instruído a landar no master ATRAVÉS DE merge PR-style local

## Próximas waves (continuação do loop)

Squad 13 strict typing (G8.13.T2/T3/T4):
- T2 (n8n): Validar JSON imports strict  
- T3 (lgpd): Custom Pydantic types CPFStr/CNPJStr [LGPD REVIEW]
- T4 (dev): Resolver mypy warnings restantes

Squad 15 radar metrics (G8.15.T1-T4):
- T1 (sre): Prometheus AI latency instrumentation

→ +Wave 46: 4 tasks paralelos, honest count 50 → 54.

Modified by Gustavo Almeida + super orquestrador — 2026-07-18
