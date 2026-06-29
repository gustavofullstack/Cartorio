# Traefik certs + Render preview — 2026-06-24

> Sessão: ZCode + MiniMax-M3 (orquestrador).
> **Descobertas: 1 BLOCKED + 1 INFO**.

## Traefik Certs (Let’s Encrypt)

ACHEI: Os certs já são **Let's Encrypt wildcard** (não self-signed como pensei)!
- **Válidos até**: 20-21 set 2026 (~3 meses)
- **Domínios cobertos**: api, flow, supabase, easypanel, agent, vps, whatsapp.2notasudi.com.br
- **Localização**: `/etc/easypanel/traefik/dump/{domain}/certificate.crt`
- **Renovação**: Automática via Traefik (acme.sh / certbot)

**POR QUE o navegador deu SSL error então?** Provavelmente:
- Traefik usa **cert 1 (api.2notasudi.com.br)** mas o cliente conectou via `wss://api.2notasudi.com.br/ws/atendimentos`
- WebSocket upgrade via Traefik pode usar **cert default** (não o específico do subdomínio)
- Workaround funcionou (disable verify) então não é problema crítico

**Workaround atual**:
- Python: `sslopt={"cert_reqs": ssl.CERT_NONE}`
- Browsers: usuário aceita cert manualmente (1x)
- **Solução real**: configurar SNI no Traefik (manual via Easypanel UI)

## Render Pull Request Previews — BLOCKED

**Status**: `pullRequestPreviewsEnabled: "no"`, `previews.generation: "off"`
**Causa**: Plano **FREE** não suporta PR previews
**Solução**: Upgrade para plan `starter` ou `standard` ($7-15/mês) — **decisão Gustavo**

**Alternativa sem upgrade**:
- Render free tem `autoDeploy: yes` em master (já funciona)
- Cada commit em master → deploy automático
- Não tem preview per-PR, mas o flow de prod é confiável

## DNS Cloudflare — MANUAL (precisa Gustavo)

**NÃO tem Cloudflare API key** no repo / .secrets / .mavis.
**Pendências**:
- `n8n.2notasudi.com.br` (A record → IP VPS)
- `supabase.2notasudi.com.br` (A record → IP VPS)

**Ação**: Gustavo criar manualmente no painel Cloudflare (5 min)
**IPs VPS**:
- Tailscale: `100.99.172.84`
- Público: `148.230.75.172`

## Certs expirando (próximo renewal em 20-21 set 2026)

**Ação recomendada**: configurar SNI no Traefik
- **Manual**: Easypanel UI → Traefik config
- **Auto**: deixar Traefik renovar (já está fazendo)

## Próximos passos

### Curto prazo
- [ ] Configurar SNI no Traefik (resolver SSL warning no WS)
- [ ] Adicionar `pullRequestPreviewsEnabled` quando Gustavo upgradar Render
- [ ] DNS manual no Cloudflare (precisa ação humana)
- [ ] Parear WhatsApp Evolution (precisa QR)

### Médio prazo
- [ ] Setup CI/CD preview deployments (GitHub Actions)
- [ ] Implementar Sentry monitoring (DPA Sentry — CAR-107)
- [ ] Migrar para Render plan pago (se quiser previews)

Modified by Gustavo Almeida
