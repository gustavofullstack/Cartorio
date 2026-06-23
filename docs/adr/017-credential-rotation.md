# ADR-017: Política de rotação de credenciais

**Data:** 2026-06-23
**Status:** PROPOSTA (aguarda aprovação Gustavo)
**Autor:** ZCode (Mavis)
**Sprint:** 3 (Bloco 3)

## Contexto

Diversas credenciais foram expostas no chat/log/git ao longo do projeto:

- OpenCode-Go `sk-j03KVdV6rDkSW1D2KmrmbCL8zRjhBw0IkOes2BNCEetOokTnbLJXwc7AyltoRscr`
- N8N MCP HTTP JWT
- N8N public API JWT
- OpenClaw Gateway Token + Password
- Redis default password
- Supabase DB password
- Easypanel API key (marcada MORTA mas ainda em uso)
- OpenClaw Tailnet bind token (Tailscale)

LiteLLM foi hackeado uma vez por causa disso. CVSS de um único segredo vazado
em chat público = catastrophic (acesso a dados de clientes de fé pública, infra
inteira da VPS, billing da OpenAI/etc).

## Decisão

Política de **rotação trimestral (90 dias)** de TODAS as credenciais de produção,
com **rotação imediata** sempre que houver suspeita de exposição (chat, log,
screenshot, commit, email).

### Padrão de rotação

1. **Geração**: usar `openssl rand -hex 32` (256 bits) ou ferramenta equivalente.
2. **Distribuição**: cada segredo vira env var de Docker service (NUNCA hardcoded).
3. **Backup off-band**: 1Password / Bitwarden com 2FA, share entre Gustavo + DPO.
4. **Reaplicação**: `docker service update --env-add/rm` rolling restart sem downtime.
5. **Validação**: smoke test do serviço (healthcheck 200 + endpoint real).
6. **Audit log**: registrar `credential.rotated` (sem expor o valor) no audit chain.

### Cadência

| Credencial | Cadência | Responsável |
|------------|----------|-------------|
| OpenCode-Go sk- | 90d + imediato se exposto | Gustavo |
| N8N JWTs (MCP + public) | 90d | Gustavo |
| OpenClaw Gateway Token/Password | 90d | Gustavo |
| Redis default | 90d | Gustavo |
| Supabase DB | 90d | Gustavo |
| Easypanel API key | 90d | Gustavo |
| CARTORIO_API_KEY (inter-service) | 90d | Gustavo |
| Tailscale auth keys | 180d | Gustavo |
| SSH chaves (MacBook/VPS) | 365d | Gustavo |
| `audit_hmac_key` (Settings) | 365d + compromete chain se exposto | ZCode (com Gustavo) |

### Mecanismo de detecção de exposição

- Grep em chat history por prefixos: `sk-`, `Bearer eyJ`, `@Techno`, `Techno832466`
- TruffleHog ou `gitleaks` em CI (Sprint 3.5)
- Revisão semanal do `.harness/memory/MEMORY.md` procurando "credencial"

## Consequências

**Positivas**
- Reduz janela de exposição se um segredo vazar.
- Força revisão periódica das integrações.
- Histórico de rotações fica no audit log (sem expor valor).

**Negativas**
- Custo operacional: ~30min/rotação × 4× ao ano = 2h/ano. Aceitável.
- Risco de lockout se Gustavo esquecer de atualizar .env. Mitigação: smoke
  test automatizado após cada rotação.
- Se rotação trimestral for pulada por motivo de sprint, a próxima deve
  acontecer em 60d (não 90d) — regra documented.

## Não-objetivos

- Vault central (HashiCorp Vault, AWS Secrets Manager) — overkill para 9 segredos.
- Auto-rotação (sem humano) — segredos rotacionados sem revisão manual
  tendem a quebrar integrações silenciosamente.
- MFA em serviços Docker (não aplicável).

## Referências

- LGPD art. 46 (medidas de segurança adequadas)
- LGPD art. 50 (boas práticas e governança)
- PCI-DSS 8.2.4 (90-day rotation guideline, inspiração)
- NIST SP 800-57 parte 1 (key management)
