#!/bin/bash
set -euo pipefail

echo "Aplicando fix deepseek-v4-flash (1M + thinking) via SSH"

ssh root@100.99.172.84 "python3 << 'PYEOF'
import json
from pathlib import Path

config_path = Path('/home/node/.openclaw/openclaw.json')
if config_path.exists():
    data = json.loads(config_path.read_text())

    # Update model default
    if 'agents' in data and 'defaults' in data['agents']:
        data['agents']['defaults']['model'] = 'openai/deepseek-v4-flash'
        data['agents']['defaults']['contextTokens'] = 1048576
        data['agents']['defaults']['thinkingDefault'] = 'adaptive'

    # Update models list
    if 'models' in data and 'providers' in data['models'] and 'openai' in data['models']['providers']:
        models = data['models']['providers']['openai'].get('models', [])
        for m in models:
            if m.get('id') == 'deepseek-v4-flash':
                m['contextWindow'] = 1048576
                m['reasoning'] = True

    config_path.write_text(json.dumps(data, indent=2))
    print('openclaw.json updated')
PYEOF"

echo "Restarting service..."
ssh root@100.99.172.84 "docker service update --force cartorio_openclaw-gateway" || echo "Failed to restart service, but ignoring for now"
echo "Done!"
