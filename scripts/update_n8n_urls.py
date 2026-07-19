import os
import sys
import requests
import time

BASE = "https://flow.2notasudi.com.br"

def login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(
        BASE + "/rest/login",
        json={"emailOrLdapLoginId": email, "password": password},
        timeout=20,
    )
    if r.status_code != 200:
        sys.exit(f"Login falhou: {r.text[:200]}")
    return s

def main():
    email = os.environ.get("N8N_LOGIN_EMAIL", "")
    password = os.environ.get("N8N_LOGIN_PASS", "")
    if not email or not password:
        raise SystemExit("N8N_LOGIN_EMAIL e N8N_LOGIN_PASS devem ser injetados pelo secret manager")
    
    # Tentativa de login
    try:
        s = login(email, password)
    except Exception as e:
        print(f"Login error with {email}: {e}")
        return
            
    print("Login successful. Checking credentials...")
    r = s.get(BASE + "/rest/credentials")
    if r.ok:
        creds = r.json().get("data", [])
        print(f"Found {len(creds)} credentials.")
        for cred in creds:
            print(f"Credential: {cred.get('name')} (ID: {cred.get('id')})")
            # Obter detalhes completos para ver dados
            c_detail = s.get(f"{BASE}/rest/credentials/{cred.get('id')}").json().get("data", {})
            data = c_detail.get("data", {})
            needs_update = False
            # O URL pode estar nas props da credential
            # Em custom API credentials, pode estar em data
            for k, v in data.items():
                if isinstance(v, str) and ("localhost" in v or "http://api:" in v or "http://cartorio" in v):
                    print(f"  Found stale URL in '{k}': {v}")
                    data[k] = v.replace("http://api:8000", "https://api.2notasudi.com.br")\
                               .replace("http://localhost:8000", "https://api.2notasudi.com.br")\
                               .replace("http://cartorio:8000", "https://api.2notasudi.com.br")
                    needs_update = True
            
            if needs_update:
                print(f"  Updating credential {c_detail.get('name')}...")
                upd = s.patch(f"{BASE}/rest/credentials/{cred.get('id')}", json={"data": data})
                print(f"  Update result: {upd.status_code}")
    else:
        print(f"Failed to get credentials: {r.text}")

    print("Checking workflows...")
    r = s.get(BASE + "/rest/workflows?limit=200")
    if r.ok:
        wfs = r.json().get("data", [])
        print(f"Found {len(wfs)} workflows.")
        for wf in wfs:
            needs_update = False
            nodes = wf.get("nodes", [])
            for node in nodes:
                params = node.get("parameters", {})
                for k, v in params.items():
                    if isinstance(v, str) and ("localhost" in v or "http://api:" in v or "http://cartorio" in v or "http://host.docker.internal" in v):
                        print(f"  Found stale URL in workflow {wf.get('name')} node {node.get('name')} param {k}: {v}")
                        params[k] = v.replace("http://api:8000", "https://api.2notasudi.com.br")\
                                     .replace("http://localhost:8000", "https://api.2notasudi.com.br")\
                                     .replace("http://cartorio:8000", "https://api.2notasudi.com.br")\
                                     .replace("http://host.docker.internal:8000", "https://api.2notasudi.com.br")
                        needs_update = True
            if needs_update:
                print(f"  Updating workflow {wf.get('name')}...")
                upd = s.patch(f"{BASE}/rest/workflows/{wf.get('id')}", json={"nodes": nodes})
                if upd.status_code == 405:
                    print("  PATCH not allowed, you must use POST or DB update (N8N 2.x)")
                else:
                    print(f"  Update result: {upd.status_code}")
    else:
        print(f"Failed to get workflows: {r.text}")

if __name__ == "__main__":
    main()
