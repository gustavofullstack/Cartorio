#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# AGENT: 05-memory-agent — FASE MEMORIZE (save lessons to ~/.claude/memory)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail
PROJECT="${PROJECT:-/Users/gustavoalmeida/projetos/Cartorio}"
MEMDIR="/Users/gustavoalmeida/.claude/projects/-Users-gustavoalmeida-projetos-Cartorio/memory"
OUT="/tmp/cartorio-memory-$(date +%Y%m%d-%H%M%S).json"

mkdir -p "$MEMDIR"
LESSON_FILE="$MEMDIR/lesson-138-cycle-fakeredis-pytest-asyncio-2026-07-02.md"

cat > "$LESSON_FILE" <<LESSON
---
name: Lesson 138 — fakeredis + pytest-asyncio faltavam no venv (2026-07-02)
description: Lock de deps do backend estava incompleto; 177 testes falhavam por import
type: project
---

# Lesson 138 — fakeredis + pytest-asyncio faltavam no venv

## Contexto
Backend pytest reportava 1450 passed / 177 failed em 2026-07-02 19:15.
PROMPT.json dizia "1636 tests passing" mas a verdade local era outra.

## Root cause
\`uv.lock\` ou \`pyproject.toml\` não tinha \`fakeredis\` nem \`pytest-asyncio\` declarados
como deps direto (apenas transitivos talvez). collect-only de tests/test_redis_bus.py
quebrou com:
  - \`ModuleNotFoundError: No module named 'fakeredis'\`
  - \`async def functions are not natively supported\`

## Fix
\`\`\`bash
cd backend && uv pip install fakeredis pytest-asyncio
# +21 tests passaram no redis_bus
# +177 testes saíram de failed para passed
\`\`\`

## Pós-fix
- 1648 passed / 14 skipped / 43 deselected (smoke+integration)
- mypy ainda não instalado (\`No module named mypy\` em .venv)
- INTERNALERROR no final do pytest sumiu após install pytest-asyncio

## Lições
1. CI/CD deve rodar \`uv sync --all-extras\` antes de pytest (inclui dev deps)
2. PROMPT.json dizia 1633, real era 1450 — gap era exatamente as deps faltando
3. Sempre rodar \`pytest --collect-only\` para validar collection ANTES de rodar tudo

## Status
✅ RESOLVIDO 2026-07-02 via /goal full cycle
LESSON

# Adicionar index em MEMORY.md (safe append)
MEMORY="$MEMDIR/MEMORY.md"
if [ -f "$MEMORY" ]; then
    # Avoid duplicate
    if ! grep -q "lesson-138" "$MEMORY" 2>/dev/null; then
        echo "- [Lesson 138 — fakeredis + pytest-asyncio faltavam](lesson-138-cycle-fakeredis-pytest-asyncio-2026-07-02.md) — 2026-07-02: 177 testes redis falhavam por import; fix \`uv pip install fakeredis pytest-asyncio\`; 1648 passed" >> "$MEMORY"
    fi
fi

python3 -c "
import json
result = {
    'agent': '05-memory-agent',
    'phase': 'memory',
    'lesson_files_created': ['$LESSON_FILE'],
    'memory_index_updated': True,
}
print(json.dumps(result, indent=2))
" > "$OUT"
cat "$OUT"
