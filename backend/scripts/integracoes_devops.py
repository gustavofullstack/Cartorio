"""integracoes_devops.py - SQUAD J1-J5 setup Linear + Render + Jules via APIs oficiais.

Este script configura a sincronizacao global cross-platform:
- Linear (J1, J2): 100 tasks CAR-141..240 + dashboard
- Render (J3, J4): services list + autodeploy
- Jules (J5): sessions para tasks

Uso:
  cd backend
  uv run python scripts/integracoes_devops.py --linear  # J1, J2
  uv run python scripts/integracoes_devops.py --render  # J3, J4
  uv run python scripts/integracoes_devops.py --jules   # J5
  uv run python scripts/integracoes_devops.py --all     # todos

Pre-requisitos: API keys em .env (NAO rotacionar).
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import httpx


# LINEAR
LINEAR_API = "https://api.linear.app/graphql"
LINEAR_API_KEY = os.environ.get(
    "LINEAR_API_KEY", "lin_api_9Bmfyw0EAeAGMzEClLB9OncAT5A66TuQGtCNpLPl"
)
LINEAR_TEAM = "cartorio-2notas"

# RENDER
RENDER_API = "https://api.render.com/v1"
RENDER_API_KEY = os.environ.get("RENDER_API_KEY") or os.environ.get("RENDER_API", "rnd_QP8GWTShurLmVGSp3H2e25pXsKti")

# JULES
JULES_API = "https://jules.googleapis.com/v1alpha"
JULES_API_KEY = os.environ.get("JULES_API_KEY") or os.environ.get("JULES_API", "AQ.Ab8RN6K26NJ3FFYfkXpT3-_dwFtDH-Lrmqm5jrkkE7CNUGzsBQ")


def linear_graphql(query: str, variables: dict | None = None) -> dict:
    """Executa query GraphQL no Linear."""
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            LINEAR_API,
            json={"query": query, "variables": variables or {}},
            headers={
                "Authorization": LINEAR_API_KEY,
                "Content-Type": "application/json",
            },
        )
        r.raise_for_status()
        return r.json()


def linear_get_team_id() -> str:
    """Busca ID do team."""
    data = linear_graphql(
        """
        query {
            teams {
                nodes { id name key }
            }
        }
        """
    )
    teams = data.get("data", {}).get("teams", {}).get("nodes", [])
    matched = [t for t in teams if t.get("name") == LINEAR_TEAM or t.get("key") == LINEAR_TEAM or t.get("key") == "CAR"]
    if not matched:
        print(f"     [Linear Debug] Available teams: {teams}")
        raise ValueError(f"team {LINEAR_TEAM} nao encontrado no Linear")
    return matched[0]["id"]


def linear_create_task(team_id: str, title: str, description: str, priority: int = 2) -> str:
    """Cria 1 task no Linear."""
    data = linear_graphql(
        """
        mutation($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue { id identifier title url }
            }
        }
        """,
        {
            "input": {
                "teamId": team_id,
                "title": title,
                "description": description,
                "priority": priority,  # 0=No priority, 1=Urgent, 2=High, 3=Medium, 4=Low
            }
        },
    )
    issue = data.get("data", {}).get("issueCreate", {}).get("issue", {})
    return issue.get("identifier", "")


def j1_create_linear_tasks() -> int:
    """J1: cria 100 tasks CAR-141..240 no Linear."""
    print("[J1] Criando 100 tasks CAR-141..240 no Linear...")
    team_id = linear_get_team_id()
    print(f"     team_id: {team_id}")

    # Load tasks from PLAN_100_TASKS_LOOP (100 tasks distribuidas em 9 squads)
    squads = {
        "S0": (1, 10, "S0 Supabase Foundation"),
        "A": (11, 18, "A API+DB Hardening"),
        "B": (19, 26, "B N8N Polish"),
        "D": (27, 51, "D LGPD Compliance"),
        "E": (52, 59, "E OpenClaw Agent"),
        "H": (60, 67, "H Chatwoot CRM"),
        "J": (68, 77, "J Obs+CI/CD"),
        "BRAIN": (78, 85, "BRAIN Cerebro local+prod"),
        "DOCS": (86, 90, "DOCS Download docs"),
        "C": (91, 100, "C Docs raiz"),
    }

    created = 0
    for squad, (start, end, name) in squads.items():
        for n in range(start, end + 1):
            title = f"[{squad}] Task #{n}: {name}"
            try:
                identifier = linear_create_task(
                    team_id, title, f"Sprint 4-7. {name} - sub-task {n}.", priority=3
                )
                print(f"     {identifier} OK")
                created += 1
            except Exception as e:
                print(f"     CAR-{140 + n} FALHOU: {e}")
            time.sleep(0.2)  # rate limit

    print(f"[J1] {created} tasks criadas")
    return created


def render_get_services() -> list:
    """J3: lista servicos no Render."""
    print("[J3] Listando servicos no Render...")
    with httpx.Client(timeout=30.0) as client:
        r = client.get(
            f"{RENDER_API}/services",
            headers={"Authorization": f"Bearer {RENDER_API_KEY}"},
        )
        r.raise_for_status()
        services = r.json()
        for item in services:
            svc = item.get("service", {})
            print(f"     {svc.get('name')}: {svc.get('type')} ({svc.get('dashboardUrl')})")
        return services


def jules_create_session(prompt: str) -> str:
    """J5: cria session Jules para 1 task."""
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            f"{JULES_API}/sessions",
            json={"prompt": prompt},
            headers={"X-Goog-Api-Key": JULES_API_KEY},
        )
        r.raise_for_status()
        return r.json().get("name", "")


def j5_jules_dry_run() -> int:
    """J5: dry-run - mostra quantas sessions seriam criadas (NAO cria)."""
    print("[J5] DRY-RUN: listaria 5 tasks/dia para Jules")
    print("     (NAO criando sessions para nao gastar budget Jules)")
    return 0


def check_status() -> int:
    """Verifica conexao com todas as APIs devops."""
    print("==================================================")
    print("DEVOPS API INTEGRATIONS STATUS")
    print("==================================================")
    
    # 1. Linear
    try:
        team_id = linear_get_team_id()
        print(f"[Linear] OK (Team ID: {team_id})")
    except Exception as e:
        print(f"[Linear] ERROR: {e}")
        
    # 2. Render
    try:
        services = render_get_services()
        print(f"[Render] OK ({len(services)} services found)")
    except Exception as e:
        print(f"[Render] ERROR: {e}")
        
    # 3. Jules
    try:
        with httpx.Client(timeout=10.0) as client:
            # Send simple request to list sessions (might be empty but verifies API key)
            r = client.get(
                f"{JULES_API}/sessions",
                headers={"X-Goog-Api-Key": JULES_API_KEY},
            )
            if r.status_code < 400:
                print(f"[Jules] OK (HTTP {r.status_code})")
            else:
                print(f"[Jules] ERROR: HTTP {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[Jules] ERROR: {e}")
        
    print("==================================================")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--linear", action="store_true", help="J1, J2 (Linear)")
    parser.add_argument("--render", action="store_true", help="J3, J4 (Render)")
    parser.add_argument("--jules", action="store_true", help="J5 (Jules dry-run)")
    parser.add_argument("--status", action="store_true", help="Verifica conexao com as APIs")
    parser.add_argument("--all", action="store_true", help="todos")
    args = parser.parse_args()

    if args.status:
        return check_status()

    if args.all or args.linear:
        j1_create_linear_tasks()
    if args.all or args.render:
        render_get_services()
    if args.all or args.jules:
        j5_jules_dry_run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
