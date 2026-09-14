import sys
import subprocess
import os
import json

env = os.environ.copy()
env.setdefault("APP_ENV", "development")
env.setdefault("BRAIN_API_ENABLED", "1")
env.setdefault("LLM_DEFAULT_PROVIDER", "opencode_go")
env.setdefault("AUDIT_HMAC_KEY", "a" * 64)
env.setdefault("CARTORIO_API_KEY", "a" * 64)
env.setdefault("PIETRA_CONVERSATION_HMAC_KEY", "a" * 64)
env.setdefault("PYTHONPATH", ".")

try:
    result = subprocess.run(
        [
            "uv", "run", "python", "-c",
            "from app.main import app; import json; "
            "print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))",
        ],
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
        check=True
    )
    data = json.loads(result.stdout)
    print("Paths:", len(data["paths"]))
except subprocess.CalledProcessError as e:
    print(e.stderr)
