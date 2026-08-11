"""backup_whatsapp_connection.py - snapshot de conexão da instância WhatsApp Evolution.

Objetivo: guardar um snapshot operacional da sessão antes de qualquer ajuste de
autonomia, sem persistir segredos.

Uso:
  cd backend
  uv run python scripts/backup_whatsapp_connection.py

Saída:
  backups/whatsapp-connection-<timestamp>.json
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path

import httpx


def _load_env_file(path: Path) -> dict[str, str]:
    """Carrega variáveis simples de um .env sem executar nada."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _env_value(key: str, env: dict[str, str]) -> str:
    return os.getenv(key, "") or env.get(key, "")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    dotenv = repo_root / ".." / ".env"
    if dotenv.is_file():
        env = _load_env_file(dotenv)
    else:
        env = _load_env_file(repo_root / ".env")

    base_url = (
        _env_value("EVOLUTION_PUBLIC_URL", env)
        or _env_value("EVOLUTION_BASE_URL", env)
        or "https://whatsapp.2notasudi.com.br"
    ).rstrip("/")
    api_key = _env_value("EVOLUTION_API_KEY", env)
    instance = _env_value("EVOLUTION_INSTANCE", env) or "cartorio-2notas"
    webhook_url = _env_value("EVOLUTION_WEBHOOK_URL", env)

    if not api_key:
        print("ERRO: EVOLUTION_API_KEY não encontrada. Defina no ambiente ou no .env.")
        return 2

    base_candidates = [
        _env_value("EVOLUTION_BASE_URL", env),
        _env_value("EVOLUTION_PUBLIC_URL", env),
        base_url,
    ]
    fallback_urls = []
    for candidate in base_candidates:
        if candidate and candidate not in fallback_urls:
            fallback_urls.append(candidate.rstrip("/"))

    headers = {"apikey": api_key}

    backup: dict[str, object] = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "instance": instance,
        "base_url": base_url,
        "manager_url": f"{base_url}/manager",
        "webhook_url": webhook_url,
        "webhook_configured": bool(webhook_url),
        "lark_app_id_set": bool(_env_value("LARK_APP_ID", env) or _env_value("lark_app_id", env)),
        "lark_verification_token_set": bool(_env_value("LARK_VERIFICATION_TOKEN", env)),
        "lark_encrypt_key_set": bool(_env_value("LARK_ENCRYPT_KEY", env)),
    }

    connection_errors: list[str] = []
    for endpoint_base in fallback_urls:
        endpoint = f"{endpoint_base}/instance/connectionState/{instance}"
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(endpoint, headers=headers)
                response.raise_for_status()
                payload = response.json()
                instance_data = payload.get("instance") if isinstance(payload, dict) else None
                if isinstance(instance_data, dict):
                    backup["connection_state"] = instance_data.get("state")
                    backup["connection_number"] = instance_data.get("number")
                    backup["connection_retry_count"] = instance_data.get("retry_count")
                    backup["pairing_code"] = instance_data.get("pairingCode")
                else:
                    backup["connection_state"] = (
                        payload.get("state") if isinstance(payload, dict) else None
                    )
                backup["connection_state_source"] = endpoint_base
                break
        except Exception as exc:
            connection_errors.append(f"{endpoint}: {type(exc).__name__}: {exc}")
    if "connection_state" not in backup:
        backup["connection_state_error"] = "; ".join(connection_errors)

    serialized = json.dumps(backup, sort_keys=True, ensure_ascii=False)
    snapshot_key = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
    backup_file = repo_root / "backups" / f"whatsapp-connection-backup-{snapshot_key}.json"
    backup_file.parent.mkdir(parents=True, exist_ok=True)

    with backup_file.open("w", encoding="utf-8") as handle:
        handle.write(serialized)

    print(f"BACKUP_OK file={backup_file}")
    print(json.dumps(backup, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
