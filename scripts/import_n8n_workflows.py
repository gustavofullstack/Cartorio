#!/usr/bin/env python3
"""Reimporta workflows via /rest/workflows (login cookie session).

Uso: python3 scripts/import_n8n_workflows.py [--dry-run] [--only <substr>] [--activate]
     python3 scripts/import_n8n_workflows.py --login email password
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = "https://flow.2notasudi.com.br"
DIR = Path(__file__).parent.parent / "infra" / "n8n-workflows"

ALLOWED_SETTINGS = {
    "executionOrder",
    "saveExecutionProgress",
    "saveDataSuccessExecution",
    "saveDataErrorExecution",
    "saveManualExecutions",
    "timezone",
    "errorWorkflow",
    "callerPolicy",
    "availableInMCP",
    "executionTimeout",
}

ALLOWED_NODE_KEYS = {
    "name",
    "type",
    "typeVersion",
    "position",
    "parameters",
    "credentials",
    "disabled",
    "notes",
    "notesInFlow",
    "retryOnFail",
    "maxTries",
    "waitBetweenTries",
    "alwaysOutputData",
    "executeOnce",
    "onError",
    "continueOnFail",
    "pinData",
}


def login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(
        BASE + "/rest/login",
        json={"emailOrLdapLoginId": email, "password": password},
        timeout=20,
    )
    if r.status_code != 200 or "data" not in r.text:
        sys.exit(f"Login falhou {r.status_code}: {r.text[:300]}")
    print(f"✓ Login OK como {email}")
    return s


def list_workflows(s: requests.Session):
    r = s.get(BASE + "/rest/workflows?limit=200", timeout=30)
    if r.status_code != 200:
        sys.exit(f"List falhou: {r.text[:300]}")
    return r.json().get("data", [])


def sanitize_node(n: dict) -> dict:
    return {k: v for k, v in n.items() if k in ALLOWED_NODE_KEYS}


def sanitize_settings(s: dict) -> dict:
    return {k: v for k, v in (s or {}).items() if k in ALLOWED_SETTINGS}


def extract_tag_names(tags) -> list[str]:
    if not tags:
        return []
    if isinstance(tags, list) and tags and isinstance(tags[0], dict):
        return [t.get("name") for t in tags if t.get("name")]
    if isinstance(tags, list):
        return [str(t) for t in tags]
    return []


def create_or_update(s: requests.Session, name: str, body: dict, wid: str | None):
    if wid:
        # N8N 2.x usa PATCH /rest/workflows/:workflowId (não PUT)
        r = s.patch(f"{BASE}/rest/workflows/{wid}", json=body, timeout=30)
        action = "updated"
    else:
        r = s.post(f"{BASE}/rest/workflows", json=body, timeout=30)
        action = "created"
    return r.status_code, r.text[:300] if not r.ok else r.json().get("data", {}), action


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--activate", action="store_true")
    ap.add_argument(
        "--login-email",
        default=os.environ.get("N8N_LOGIN_EMAIL", "gustavomar.fullstack@gmail.com"),
    )
    ap.add_argument(
        "--login-pass", default=os.environ.get("N8N_LOGIN_PASS", "@Techno832466")
    )
    args = ap.parse_args()

    s = login(args.login_email, args.login_pass)
    existing = {w["name"]: w for w in list_workflows(s)}
    print(f"Existentes: {len(existing)}\n")

    files = sorted(p for p in DIR.glob("*.json"))
    if args.only:
        files = [p for p in files if args.only in p.name]

    created = updated = failed = skipped = 0
    for fp in files:
        try:
            wf = json.loads(fp.read_text())
        except Exception as e:
            print(f"  [skip] {fp.name}: JSON invalido: {e}")
            skipped += 1
            continue
        nodes = wf.get("nodes", [])
        if not nodes:
            print(f"  [skip] {fp.name}: sem nodes")
            skipped += 1
            continue

        name = wf.get("name") or fp.stem
        body = {
            "name": name,
            "nodes": [sanitize_node(n) for n in nodes],
            "connections": wf.get("connections", {}),
            "settings": sanitize_settings(wf.get("settings", {})),
            "staticData": wf.get("staticData"),
        }

        if args.activate:
            body["active"] = True

        match = existing.get(name)
        wid = match["id"] if match else None
        if args.dry_run:
            print(
                f"  [dry-{('update' if wid else 'create')}] {fp.name}: {name} (tags={extract_tag_names(wf.get('tags'))})"
            )
            continue

        code, res, action = create_or_update(s, name, body, wid)
        if code in (200, 201):
            if wid:
                updated += 1
                print(f"  [{action}] {fp.name}: {name} (id={wid[:8]})")
            else:
                new_id = (res or {}).get("id") if isinstance(res, dict) else None
                created += 1
                print(f"  [created] {fp.name}: {name} (id={str(new_id)[:8]})")
                # tags
                for tag in extract_tag_names(wf.get("tags")):
                    tr = s.put(
                        f"{BASE}/rest/workflows/{new_id}/tags",
                        json=[{"name": tag}],
                        timeout=15,
                    )
                    if tr.status_code not in (200, 201):
                        print(f"    [warn] tag {tag}: {tr.status_code}")
        else:
            failed += 1
            print(f"  [FAIL {code}] {fp.name}: {name} -> {res}")
        time.sleep(0.4)

    print(
        f"\n=== RESUMO === created={created} updated={updated} failed={failed} skipped={skipped}"
    )


if __name__ == "__main__":
    main()
