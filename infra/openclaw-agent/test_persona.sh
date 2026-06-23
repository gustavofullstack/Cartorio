#!/bin/bash
# test_persona.sh
# Roda o CartorioBot via OpenClaw CLI e valida que a persona foi carregada.
# Uso: ./test_persona.sh [pergunta]
#
# Se retornar frase em tom cartorario (mencionando "Cartório", "Uberlândia",
# "Av. Paulo Gracindo", "09h-17h", "Tabela MG"), a persona está ativa.
#
# Gustavo usa isso para verificar o agent sem precisar abrir o Chrome.

set -e

OCID=$(ssh -o ConnectTimeout=5 cartorio 'docker ps -q --filter "name=cartorio_openclaw-gateway" 2>/dev/null' | head -1)

if [ -z "$OCID" ]; then
    echo "ERRO: container cartorio_openclaw-gateway nao encontrado" >&2
    exit 1
fi

QUESTION="${1:-Ola, qual o horario de funcionamento?}"
SESSION_ID="persona-test-$(date +%s)"

echo "=== Triggering fresh OpenClaw session ==="
echo "OCID:    $OCID"
echo "Session: $SESSION_ID"
echo "Q:       $QUESTION"
echo

ssh -o ConnectTimeout=10 cartorio "docker exec $OCID openclaw agent \
    --agent main \
    --session-id $SESSION_ID \
    --message \"$QUESTION\" \
    --json" 2>&1 | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print('Status:    ', d.get('status'))
print('Model:     ', d.get('result', {}).get('meta', {}).get('agentMeta', {}).get('model'))
print('Provider:  ', d.get('result', {}).get('meta', {}).get('agentMeta', {}).get('provider'))
print('Latency:   ', d.get('result', {}).get('meta', {}).get('durationMs'), 'ms')
print('Tokens:    ', d.get('result', {}).get('meta', {}).get('usage', {}).get('total'))
print()
print('--- CartorioBot response ---')
for p in d.get('result', {}).get('payloads', []):
    print(p.get('text', ''))
print()
print('--- Validation ---')
all_text = ' '.join(p.get('text', '') for p in d.get('result', {}).get('payloads', []))
keywords = ['Cartório', 'Uberlândia', 'Paulo Gracindo', '09h', '17h', 'segunda', 'sexta']
found = [k for k in keywords if k.lower() in all_text.lower()]
missing = [k for k in keywords if k.lower() not in all_text.lower()]
if found:
    print(f'  OK persona ativa (encontrou: {found})')
if missing:
    print(f'  WARN keywords nao encontrados: {missing}')
" 2>&1
