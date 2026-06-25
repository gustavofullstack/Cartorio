#!/bin/bash
# =============================================================================
# RUN E2E Tests (E2E Telegram / N8N / Evolution)
# Uso: bash scripts/run_e2e_tests.sh
# =============================================================================

set -euo pipefail

cd /Users/gustavoalmeida/projetos/Cartorio/backend

echo "=========================================="
echo "RUN E2E Tests (Telegram / N8N / Evolution)"
echo "=========================================="
echo ""

echo "[1/3] test_e1_s1_t7_e2e_evolution (Evolution webhook)"
uv run pytest --no-cov ../backend/tests/integration/test_e1_s1_t7_e2e_evolution.py -v 2>&1 | tail -5

echo ""
echo "[2/3] test_webhook_evolution_e2e (Evolution webhook PII scrub)"
uv run pytest --no-cov ../backend/tests/test_webhook_evolution_e2e.py -v 2>&1 | tail -5

echo ""
echo "[3/3] test_smoke/test_whatsapp_e2e (PII zero, production smoke)"
echo "       (requer SMOKE_TARGET=prod - skip se nao setado)"
if [ -n "${SMOKE_TARGET:-}" ]; then
    uv run pytest --no-cov ../backend/tests/smoke/test_whatsapp_e2e.py -v 2>&1 | tail -5
else
    echo "  ⏭️  Pulado (SMOKE_TARGET nao setado)"
fi

echo ""
echo "=========================================="
echo "E2E Tests Resumido:"
echo "  - test_e1_s1_t7_e2e_evolution: 13 tests (Webhook E1.S1.T7)"
echo "  - test_webhook_evolution_e2e:   12 tests (Webhook PII scrub)"
echo "  - test_smoke/test_whatsapp_e2e:   9 tests (PRODUCTION smoke)"
echo "=========================================="

echo ""
echo "NOTAS:"
echo "  - Se algum falhar, verifique o .env (CHATWOOT_API_KEY, EVOLUTION_API_KEY)"
echo "  - Se OpenClaw/Evolution offline, E2E sera skipped (graceful degradation)"
echo "  - Logs em /tmp/e2e.log se redirect aplicado"