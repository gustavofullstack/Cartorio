# Tailscale internal latency probe (G8.09.T1)

Dedicated TCP latency probe for the Tailscale mesh, complementary to
`health_radar_expanded` (`RADAR_TAILSCALE_HOST=100.99.172.84:22`).

## Module

- `backend/app/services/tailscale_probe.py`
- Tests: `backend/tests/test_tailscale_probe_g8.py`

## API

| Symbol | Role |
| --- | --- |
| `TailscaleProbeResult` | `host`, `port`, `ok`, `latency_ms`, `detail` |
| `probe_tcp(host, port, timeout=2.0)` | Pure `socket.create_connection` |
| `probe_tailscale_defaults()` | Defaults + env overrides |
| `format_report(results)` | Markdown table + GREEN/YELLOW/RED |

## CLI

```bash
cd backend
# Markdown report (exit 0 if all OK)
.venv312/bin/python -m app.services.tailscale_probe

# Single host
.venv312/bin/python -m app.services.tailscale_probe --host 100.99.172.84 --port 22

# JSON
.venv312/bin/python -m app.services.tailscale_probe --json
```

## Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `RADAR_TAILSCALE_HOST` | `100.99.172.84` | Mesh SSH host |
| `RADAR_TAILSCALE_PORT` | `22` | Mesh SSH port |
| `TAILSCALE_API_HOST` | _(unset)_ | Optional internal API IP |
| `TAILSCALE_API_PORT` | `8000` | Optional API port |

## Notes

- Probe is **TCP connect only** (no SSH auth, no ICMP).
- Fail-open: exceptions become `ok=False` results, never raise.
- Aligns with radar category `tailscale` in `/api/v1/health/radar/expanded`.
