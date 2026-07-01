import re
import sys

import httpx

base = "http://cartorio_openclaw-gateway:18789"
hdr = {
    "Authorization": "Bearer fz1qzo2xka8n82rn62irscuqws75mm1e17mpsnxzqlp13z1p35skrbg2ck8yg8pg"
}

# 1) GET root para ver UI
r = httpx.get(f"{base}/", headers=hdr, timeout=10)
# pegar paths em JS/HTML
paths = set(re.findall(r'["\']/(v\d+/[a-z\-/_]+|api/[a-z\-_/]+)["\']', r.text))
print("Found paths:")
for p in sorted(paths)[:30]:
    print(f"  {p}")

# 2) GET /v1/chat com OPTIONS para ver métodos
print("\nOPTIONS /v1/chat:")
r = httpx.options(f"{base}/v1/chat", headers=hdr, timeout=5)
print(f"  {r.status_code} Allow={r.headers.get('allow', '')}")

# 3) Tentar /v1/chat POST com diferentes métodos
print("\nProbing POST:")
for p in ["/v1/chat", "/v1/chat/completions", "/v1/messages", "/v1/completions"]:
    r = httpx.post(
        f"{base}{p}",
        headers=hdr,
        json={"model": "openclaw", "messages": [{"role": "user", "content": "oi"}]},
        timeout=5,
    )
    print(f"  POST {p}: {r.status_code} | {r.text[:120]}")
