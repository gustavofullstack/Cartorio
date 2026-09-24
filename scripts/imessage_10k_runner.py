"""Runner 10K — campanha iMessage real-transport p/ AGENT PIETRA.

Escala os 100 casos base de imessage_e2e_runner.py para 10.000 via gerador
deterministico de variantes (seed fixa). Transporte TCC-free:
  SEND: osascript -> Messages.app (Automation permission, nao FDA)
  READ: poll sqlite state.db do gateway Hermes (reply = row assistant apos user)

Features:
- Waves resumiveis (checkpoint json) — default 20 waves x 500 casos
- Higiene de memoria: snapshot/restore USER.md+MEMORY.md por wave
- Circuit breaker: 3 timeouts seguidos -> pausa + arquivo ALERT
- Deteccao de duplicata (2+ assistant p/ 1 user) e latencia por caso
- Artefatos: artifacts/imessage/10k/wave_XX.jsonl + summary.json + checkpoint

Usage:
  uv run python scripts/imessage_10k_runner.py --wave 1        # 1 wave (500)
  uv run python scripts/imessage_10k_runner.py --all           # todas as waves
  uv run python scripts/imessage_10k_runner.py --status        # progresso

Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from imessage_e2e_runner import TEST_CASES, evaluate  # noqa: E402

ARTIFACTS = Path("/Users/gustavoalmeida/Projetos/Cartorio/artifacts/imessage/10k")
STATE_DB = "/Users/gustavoalmeida/.hermes/profiles/cartorio/state.db"
MEM_DIR = Path("/Users/gustavoalmeida/.hermes/profiles/cartorio/memories")
BUDDY = "+16282649335"
VARIANTS_PER_CASE = 100
WAVE_SIZE = 500
TIMEOUT_S = 90
POLL_S = 3
MAX_CONSEC_TIMEOUTS = 3

PREFIXES = [
    "",
    "oi, ",
    "ola, ",
    "bom dia, ",
    "boa tarde, ",
    "boa noite, ",
    "pietra, ",
    "ei, ",
    "por favor, ",
    "uai, ",
    "desculpa, ",
    "opa, ",
]
SUFFIXES = ["", "?", " por favor", " por gentileza", " pf", "!!", " valeu", " obrigado"]
CONTEXTS = [
    "",
    "sou cliente e ",
    "preciso de ajuda: ",
    "me tira uma duvida: ",
    "primeira vez aqui: ",
    "to com pressa: ",
]


def strip_accents(s: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def swap_typo(s: str, rng: random.Random) -> str:
    letters = [i for i, c in enumerate(s) if c.isalpha()]
    if len(letters) < 4:
        return s
    i = rng.choice(letters[2:-2])
    lst = list(s)
    lst[i], lst[i + 1] = lst[i + 1], lst[i]
    return "".join(lst)


def gen_variant(msg: str, rng: random.Random) -> str:
    v = msg
    r = rng.random()
    if r < 0.25:
        v = strip_accents(v)
    elif r < 0.35:
        v = swap_typo(v, rng)
    elif r < 0.45:
        v = v.rstrip("?!.")
    elif r < 0.52:
        v = v.upper() if len(v) < 40 else v
    pre = rng.choice(PREFIXES)
    suf = rng.choice(SUFFIXES)
    ctx = rng.choice(CONTEXTS) if rng.random() < 0.15 else ""
    v = f"{pre}{ctx}{v}{suf}".strip()
    return v if v and v.lower() != msg.lower() else f"{v}?"


def build_plan() -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for tc in TEST_CASES:
        rng = random.Random(f"{tc['id']}:10k")
        seen = {tc["msg"].lower()}
        variants = [tc["msg"]]
        attempts = 0
        while len(variants) < VARIANTS_PER_CASE and attempts < VARIANTS_PER_CASE * 5:
            attempts += 1
            v = gen_variant(tc["msg"], rng)
            if v.lower() in seen or len(v) > 180:
                continue
            seen.add(v.lower())
            variants.append(v)
        for n, v in enumerate(variants):
            plan.append(
                {
                    "id": f"{tc['id']}-V{n:03d}",
                    "base": tc["id"],
                    "cat": tc["cat"],
                    "msg": v,
                    "expected": tc.get("expected", []),
                    "forbidden": tc.get("forbidden", []),
                    "require_identity": tc.get("require_identity", False),
                }
            )
    return plan


def send_msg(text: str) -> bool:
    safe = text.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        f'tell application "Messages" to send "{safe}" to buddy "{BUDDY}" '
        f"of (1st account whose service type = iMessage)"
    )
    try:
        r = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=60
        )
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


def wait_reply(
    since_ts: float, sent_msg: str, timeout_s: int = TIMEOUT_S
) -> dict[str, Any] | None:
    token = sent_msg.split()[-1].strip("?!.,")[:20] if sent_msg.split() else ""
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            con = db_conn()
            rows = con.execute(
                "SELECT role, content, timestamp FROM messages WHERE timestamp > ? ORDER BY timestamp",
                (since_ts,),
            ).fetchall()
            con.close()
        except sqlite3.Error:
            time.sleep(POLL_S)
            continue
        users = [r for r in rows if r[0] == "user"]
        saw_user = any(
            token and token.lower() in (r[1] or "").lower() for r in users
        ) or bool(users)
        asst = [r for r in rows if r[0] == "assistant" and r[1]]
        if saw_user and asst:
            return {
                "text": asst[-1][1],
                "n_assistant": len(asst),
                "latency_s": round(time.time() - start, 1),
            }
        time.sleep(POLL_S)
    return None


def snapshot_memory() -> dict[str, str]:
    snap = {}
    for name in ("USER.md", "MEMORY.md"):
        p = MEM_DIR / name
        snap[name] = p.read_text() if p.exists() else ""
    return snap


def restore_memory(snap: dict[str, str]) -> None:
    for name, content in snap.items():
        p = MEM_DIR / name
        try:
            if content:
                p.write_text(content)
            elif p.exists():
                p.write_text("")
        except OSError:
            pass


def load_checkpoint() -> dict[str, Any]:
    cp = ARTIFACTS / "checkpoint.json"
    if cp.exists():
        return json.loads(cp.read_text())
    return {"next_index": 0, "wave": 1, "done": 0, "pass": 0, "fail": 0, "timeout": 0}


def save_checkpoint(cp: dict[str, Any]) -> None:
    (ARTIFACTS / "checkpoint.json").write_text(json.dumps(cp, indent=1))


def run_wave(
    plan: list[dict[str, Any]], cp: dict[str, Any], wave_n: int
) -> dict[str, Any]:
    start_idx = cp["next_index"]
    end_idx = min(start_idx + WAVE_SIZE, len(plan))
    wave_file = ARTIFACTS / f"wave_{wave_n:02d}.jsonl"
    mem_snap = snapshot_memory()
    stats: dict[str, Any] = {
        "wave": wave_n,
        "start_idx": start_idx,
        "cases": 0,
        "pass": 0,
        "fail": 0,
        "timeout": 0,
        "dups": 0,
        "latencies": [],
        "started": datetime.now().isoformat(timespec="seconds"),
    }
    consec_timeout = 0
    print(
        f"=== WAVE {wave_n} | casos {start_idx}..{end_idx - 1} ({end_idx - start_idx}) ===",
        flush=True,
    )
    for idx in range(start_idx, end_idx):
        case = plan[idx]
        ts = last_ts()
        t0 = time.time()
        sent = send_msg(case["msg"])
        if not sent:
            result = {"id": case["id"], "status": "SEND_FAIL", "cat": case["cat"]}
        else:
            reply = wait_reply(ts, case["msg"])
            if reply is None:
                result = {
                    "id": case["id"],
                    "status": "TIMEOUT",
                    "cat": case["cat"],
                    "input": case["msg"],
                }
            else:
                ev = evaluate(
                    case["id"],
                    reply["text"],
                    case["expected"],
                    case["forbidden"],
                    require_identity=case["require_identity"],
                )
                ev.update(
                    {
                        "id": case["id"],
                        "base": case["base"],
                        "cat": case["cat"],
                        "input": case["msg"],
                        "response": reply["text"][:600],
                        "n_assistant": reply["n_assistant"],
                        "latency_s": reply["latency_s"],
                    }
                )
                if reply["n_assistant"] > 1:
                    ev.setdefault("issues", []).append(
                        f"duplicate_response:n={reply['n_assistant']}"
                    )
                    stats["dups"] += 1
                result = ev
                stats["latencies"].append(reply["latency_s"])
        st = result.get("status", "FAIL")
        stats["cases"] += 1
        stats[
            "pass"
            if st == "PASS"
            else "timeout"
            if st in ("TIMEOUT", "SEND_FAIL")
            else "fail"
        ] += 1
        consec_timeout = consec_timeout + 1 if st in ("TIMEOUT", "SEND_FAIL") else 0
        with open(wave_file, "a") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        cp["next_index"] = idx + 1
        cp["done"] += 1
        cp[
            "pass"
            if st == "PASS"
            else "timeout"
            if st in ("TIMEOUT", "SEND_FAIL")
            else "fail"
        ] += 1
        if stats["cases"] % 25 == 0:
            save_checkpoint(cp)
            print(
                f"  [{stats['cases']}/{end_idx - start_idx}] "
                f"P={stats['pass']} F={stats['fail']} T={stats['timeout']} "
                f"({time.time() - t0:.0f}s last)",
                flush=True,
            )
        if consec_timeout >= MAX_CONSEC_TIMEOUTS:
            (ARTIFACTS / "ALERT").write_text(
                f"{datetime.now().isoformat()} — {MAX_CONSEC_TIMEOUTS} timeouts seguidos no idx {idx}\n"
            )
            print("  !! ALERT: timeouts consecutivos — pausando wave", flush=True)
            break
        time.sleep(1.5)
    restore_memory(mem_snap)
    lats = stats.pop("latencies")
    stats["latency_avg_s"] = round(sum(lats) / len(lats), 1) if lats else None
    stats["latency_p95_s"] = sorted(lats)[int(len(lats) * 0.95)] if lats else None
    stats["ended"] = datetime.now().isoformat(timespec="seconds")
    save_checkpoint(cp)
    with open(ARTIFACTS / "summary.jsonl", "a") as f:
        f.write(json.dumps(stats, ensure_ascii=False) + "\n")
    print(
        f"=== WAVE {wave_n} FIM: P={stats['pass']} F={stats['fail']} "
        f"T={stats['timeout']} dups={stats['dups']} lat_avg={stats['latency_avg_s']}s ===",
        flush=True,
    )
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", type=int, default=0, help="roda 1 wave (numero livre)")
    ap.add_argument("--all", action="store_true", help="roda ate o fim do plano")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    plan = build_plan()
    total = len(plan)
    cp = load_checkpoint()

    if args.status:
        print(json.dumps({"total_plan": total, **cp}, indent=1))
        return 0

    print(
        f"Plano 10K: {total} casos ({len(TEST_CASES)} base x {VARIANTS_PER_CASE})",
        flush=True,
    )
    print(
        f"Checkpoint: next={cp['next_index']} done={cp['done']} "
        f"P={cp['pass']} F={cp['fail']} T={cp['timeout']}",
        flush=True,
    )

    if not args.all and args.wave <= 0:
        ap.error("use --wave N ou --all")

    while cp["next_index"] < total:
        wave_n = cp["next_index"] // WAVE_SIZE + 1
        cp["wave"] = wave_n
        run_wave(plan, cp, wave_n)
        if (ARTIFACTS / "ALERT").exists():
            print(
                "ALERT ativo — encerrando loop. Remova artifacts/imessage/10k/ALERT p/ continuar."
            )
            return 2
        if not args.all:
            break
    print(
        f"=== CAMPANHA: done={cp['done']}/{total} "
        f"P={cp['pass']} F={cp['fail']} T={cp['timeout']} ===",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
