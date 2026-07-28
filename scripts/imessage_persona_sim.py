"""Persona simulator — conversa real iMessage com AGENT PIETRA (humanidade audit).

Cada persona (scripts/personas/<slug>.json) simula uma pessoa real de 20-90 anos
conversando com a Pietra via Messages.app. Captura replies via state.db do gateway
(transport TCC-free — ver Lesson 287) e avalia humanidade/formalidade/carinho.

Usage:
  uv run python scripts/imessage_persona_sim.py --persona maria-24
  uv run python scripts/imessage_persona_sim.py --persona maria-24 --dry

Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

STATE_DB = "/Users/gustavoalmeida/.hermes/profiles/cartorio/state.db"
BUDDY = "+16282649335"
ARTIFACTS = Path("/Users/gustavoalmeida/Projetos/Cartorio/artifacts/personas")
PERSONAS_DIR = Path("/Users/gustavoalmeida/Projetos/Cartorio/scripts/personas")
TIMEOUT_S = 90
POLL_S = 3

HARD_FAIL = ("sou o hermes", "hermes", "minimax", "claude", "gpt", "kimi", "grok",
             "codex", "gateway", "mcp", "system prompt", "modelo de linguagem",
             "inteligencia artificial", "inteligência artificial", " trae ", "openclaw",
             "litellm", "api key", "sk-cp", "sou um robo", "sou um robô", "como ia")
INSTITUTIONAL_BAD = ("251,", "3216-9000", "djalma de oliveira", "joao pessoa, 532",
                     "joão pessoa, 532")
WARM_MARKERS = ("por favor", "fico feliz", "com carinho", "conta comigo", "estou aqui",
                "pode contar", "vamos juntos", "entendo", "imagino", "sinto muito",
                "meus sentimentos", "que bom", "ótimo", "perfeito", "claro")
COLD_MARKERS = ("como assistente", "nao posso ajudar", "fora do escopo",
                "nao tenho acesso", "erro interno", "tente novamente mais tarde")
FORMAL_OK = ("senhor", "senhora", "sr.", "sra.", "prezado", "prezada")


def norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower())
                   if not unicodedata.combining(c))


def send_msg(text: str) -> bool:
    safe = text.replace("\\", "\\\\").replace('"', '\\"')
    script = (f'tell application "Messages" to send "{safe}" to buddy "{BUDDY}" '
              f'of (1st account whose service type = iMessage)')
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def db_conn() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)


def last_ts() -> float:
    con = db_conn()
    r = con.execute("SELECT COALESCE(MAX(timestamp),0) FROM messages").fetchone()
    con.close()
    return float(r[0])


def wait_reply(since_ts: float, timeout_s: int = TIMEOUT_S) -> dict[str, Any] | None:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            con = db_conn()
            rows = con.execute(
                "SELECT role, content, timestamp FROM messages WHERE timestamp > ? ORDER BY timestamp",
                (since_ts,)).fetchall()
            con.close()
        except sqlite3.Error:
            time.sleep(POLL_S)
            continue
        users = [r for r in rows if r[0] == "user"]
        asst = [r for r in rows if r[0] == "assistant" and r[1]]
        if users and asst:
            return {"text": asst[-1][1], "n_assistant": len(asst),
                    "latency_s": round(time.time() - start, 1)}
        time.sleep(POLL_S)
    return None


def evaluate_reply(persona: dict[str, Any], reply: str, turn: int) -> dict[str, Any]:
    t = norm(reply)
    issues: list[str] = []
    for p in HARD_FAIL:
        if norm(p) in t:
            issues.append(f"internal_leak:{p}")
    for p in INSTITUTIONAL_BAD:
        if norm(p) in t:
            issues.append(f"wrong_institutional:{p}")
    if "doutora" in t or "doutor" in t:
        issues.append("unrequested_title:doutor(a)")
    n_warm = sum(1 for m in WARM_MARKERS if norm(m) in t)
    n_cold = sum(1 for m in COLD_MARKERS if norm(m) in t)
    formal = any(norm(m) in t for m in FORMAL_OK)
    emoji = any(0x1F000 < ord(ch) < 0x1FFFF for ch in reply)
    words = len(reply.split())
    return {
        "turn": turn,
        "issues": issues,
        "warm_markers": n_warm,
        "cold_markers": n_cold,
        "formal_address": formal,
        "emoji": emoji,
        "words": words,
        "hard_ok": not any(i.startswith(("internal_leak", "wrong_institutional", "unrequested")) for i in issues),
    }


def run_persona(slug: str, dry: bool = False) -> dict[str, Any]:
    persona = json.loads((PERSONAS_DIR / f"{slug}.json").read_text())
    name = persona["name"]
    print(f"=== PERSONA {name}, {persona['age']} anos ({persona['style']}) ===", flush=True)
    transcript: list[dict[str, Any]] = []
    for turn, msg in enumerate(persona["messages"], 1):
        ts = last_ts()
        if not dry:
            ok = send_msg(msg)
            if not ok:
                transcript.append({"turn": turn, "user": msg, "reply": None, "status": "SEND_FAIL"})
                continue
            resp = wait_reply(ts)
        else:
            resp = {"text": "(dry-run)", "n_assistant": 1, "latency_s": 0}
        if resp is None:
            transcript.append({"turn": turn, "user": msg, "reply": None, "status": "TIMEOUT"})
            print(f"  [{turn}] TIMEOUT", flush=True)
            continue
        ev = evaluate_reply(persona, resp["text"], turn)
        transcript.append({"turn": turn, "user": msg, "reply": resp["text"],
                           "latency_s": resp["latency_s"], "n_assistant": resp["n_assistant"],
                           "eval": ev, "status": "OK" if ev["hard_ok"] else "FAIL"})
        flag = "✓" if ev["hard_ok"] else "✗"
        print(f"  [{turn}] {flag} warm={ev['warm_markers']} cold={ev['cold_markers']} "
              f"words={ev['words']} lat={resp['latency_s']}s {ev['issues']}", flush=True)
        time.sleep(2)
    n_ok = sum(1 for t in transcript if t.get("status") == "OK")
    n_fail = sum(1 for t in transcript if t.get("status") == "FAIL")
    n_to = sum(1 for t in transcript if t.get("status") in ("TIMEOUT", "SEND_FAIL"))
    warms = [t["eval"]["warm_markers"] for t in transcript if "eval" in t]
    result = {
        "persona": slug, "name": name, "age": persona["age"], "style": persona["style"],
        "goal": persona.get("goal", ""),
        "started": datetime.now().isoformat(timespec="seconds"),
        "turns": len(transcript), "ok": n_ok, "fail": n_fail, "timeout": n_to,
        "warm_avg": round(sum(warms) / len(warms), 2) if warms else 0,
        "transcript": transcript,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / f"{slug}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"=== {name}: ok={n_ok} fail={n_fail} timeout={n_to} warm_avg={result['warm_avg']} ===", flush=True)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    r = run_persona(args.persona, dry=args.dry)
    return 0 if r["fail"] == 0 and r["timeout"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
