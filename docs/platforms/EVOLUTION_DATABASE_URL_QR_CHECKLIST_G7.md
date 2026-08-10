# Evolution DATABASE_URL + WhatsApp QR (G7.04.T1 + G7.04.T2)

**Status prod 2026-07-16:** Evolution **offline** no radar · whatsapp.2notasudi.com.br **502**  
**Root cause típico (Lesson 176):** `DATABASE_URL` apontando IP/creds antigas; Postgres recriado com `admin`/DB atual.

---

## G7.04.T1 — DATABASE_URL (Easypanel UI ~10 min)

### Checklist

1. EasyPanel → serviço `evolution-api` (ou nome stack cartorio)
2. Env `DATABASE_URL` / `DATABASE_CONNECTION_URI`:
   - Host: **DNS Swarm interno** do Postgres Supabase (não `10.11.211.12` externo)
   - User/pass: **credenciais atuais** do container Postgres (não `supabase_admin:e999…` legado)
   - DB name: conferir `POSTGRES_DB` real
3. Mesma correção se Evolution tiver Redis URL quebrada
4. Deploy / scale: se host-mode port conflict → scale **0 → 1**
5. Validar:
   ```bash
   curl -sS https://api.2notasudi.com.br/api/v1/health/radar | jq .services.evolution
   curl -sS -o /dev/null -w '%{http_code}\n' https://whatsapp.2notasudi.com.br/
   ```

### Anti-padrões

- `docker service update --force` **sem** corrigir env (não resolve)
- Alias DNS Swarm inválido entre stacks (preferir service name documentado no compose EasyPanel)

---

## G7.04.T2 — QR scan helper

| Artefato | Path |
|----------|------|
| N8N WF | `infra/n8n-workflows/33-whatsapp-qr-scan-helper.json` |
| Manager UI | `https://whatsapp.2notasudi.com.br/manager` |
| Instância | `cartorio-2notas` (state close→open) |

### Passos Gustavo

1. Evolution UP (após T1)
2. Abrir manager → instância cartorio-2notas
3. Escanear QR no WhatsApp Business do cartório
4. State deve ir `close` → `open` / `connected`
5. Smoke: enviar msg teste → webhook API → resposta emolumento

### WF helper

Webhook/cron que aponta link do manager + checa state via Evolution API  
(export em `33-whatsapp-qr-scan-helper.json` — ativar no N8N quando flow UP).

---

## Cross-refs

- Lesson 176 SRE 502 · CANAL_HEALTH_MATRIX · G7_SUI_WAVE14_CHECKLIST  
- Dual-format webhook: `parse_evolution_payload` (G7.04.T3 Wave 17)

**Modified by Gustavo Almeida + cartorio-sre/n8n — G7 Wave 20**
