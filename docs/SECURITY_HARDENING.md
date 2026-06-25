# Security Hardening — Cartório Chatbot

> Guia de hardening de segurança para o sistema completo.
> Última atualização: 2026-06-26.

## TL;DR

**Princípio**: Defense in Depth (múltiplas camadas).

**Camadas**:
1. **Rede**: Cloudflare (DDoS + WAF) + Tailscale VPN
2. **Infra**: Docker Swarm isolation + Traefik SSL
3. **App**: CORS + Rate Limiting + Auth + PII Scrub
4. **Dados**: RLS + Encryption at rest + Audit log

**LGPD**: Conformidade 100% (D01-D25 implementados).

---

## Índice

1. [Modelo de Ameaças](#1-modelo-de-ameaças)
2. [Camada de Rede](#2-camada-de-rede)
3. [Camada de Infraestrutura](#3-camada-de-infraestrutura)
4. [Camada de Aplicação](#4-camada-de-aplicação)
5. [Camada de Dados](#5-camada-de-dados)
6. [LGPD e Compliance](#6-lgpd-e-compliance)
7. [Monitoramento de Segurança](#7-monitoramento-de-segurança)
8. [Incident Response](#8-incident-response)
9. [Auditoria](#9-auditoria)
10. [Checklist de Hardening](#10-checklist-de-hardening)

---

## 1. Modelo de Ameaças

### 1.1 Atores

| Ator | Motivação | Probabilidade |
|------|-----------|---------------|
| **Hacker externo** | Vazamento de dados, ransom | Média |
| **Script kiddie** | Defacement, DoS | Alta |
| **Bot/scraper** | Coleta de dados | Alta |
| **Insider malicioso** | Acesso indevido | Baixa |
| **Concorrente** | Espionagem | Baixa |
| **Cliente malicioso** | Fraude, abuso | Média |

### 1.2 Assets Críticos

```
🔴 CRÍTICO:
- Dados pessoais (CPF, nome, telefone) - LGPD
- Credenciais (API keys, JWTs)
- Audit log (integridade)

🟠 ALTO:
- Conversas (sigilo profissional)
- Documentos (segunda via)
- Emolumentos (cálculo financeiro)

🟡 MÉDIO:
- Métricas e logs
- Configurações não-sensíveis
- Documentação pública
```

### 1.3 Vetores de Ataque

| Vetor | Mitigação |
|-------|-----------|
| **DDoS** | Cloudflare Proxy + Rate Limiting |
| **SQL Injection** | SQLAlchemy ORM (parametrized) + RLS |
| **XSS** | React/Vue (auto-escape) + CSP headers |
| **CSRF** | SameSite cookies + Token em header |
| **SSRF** | Whitelist de URLs + Network policies |
| **RCE** | Container isolation + Least privilege |
| **Data Breach** | PII Scrub + Encryption + Audit |
| **MITM** | TLS 1.3 + HSTS |
| **Credential Stuffing** | Rate Limiting + MFA (futuro) |
| **Insider Threat** | Audit log + Least privilege |

---

## 2. Camada de Rede

### 2.1 Cloudflare (DDoS + WAF)

```yaml
# Configuração Cloudflare
SSL/TLS: Full (Strict)
  # Cloudflare valida cert do origin (Traefik)
  
Always Use HTTPS: ON
  # Força HTTPS

HSTS: ON (max-age=31536000, includeSubDomains, preload)
  # Browser força HTTPS

Security Level: High
  # WAF mais agressivo

Browser Integrity Check: ON
  # Bloqueia bots sem JS

Rate Limiting Rules:
  - api.2notasudi.com.br: 100 req/10s
  - flow.2notasudi.com.br: 200 req/10s
  - chat.2notasudi.com.br: 50 req/10s

Bot Management: ON
  # Bloqueia bots maliciosos

WAF Managed Rules: ON
  # Cloudflare rules atualizadas
```

### 2.2 Tailscale VPN

```
Benefícios:
✅ Criptografia WireGuard ponta a ponta
✅ MagicDNS (resolve vps-cartorio.tail2fe279.ts.net)
✅ ACLs granulares
✅ MFA para entrar na rede
✅ Key rotation automática (90d)

Configuração:
- Tailnet: tail2fe279.ts.net
- Nodes: VPS, MacBook, iPhones, TriQ Hub
- Exit node: TriQ Hub (para navegação segura)
```

### 2.3 Firewall (VPS)

```bash
# UFW (Ubuntu Firewall)
ssh vps-cartorio

# Regras
ufw default deny incoming
ufw default allow outgoing

# SSH (apenas Tailscale)
ufw allow in on tailscale0 to any port 22

# HTTP/HTTPS (Traefik)
ufw allow 80/tcp
ufw allow 443/tcp

# Portas internas (NÃO expor externamente)
# 5432 (Postgres), 6379 (Redis), 5678 (N8N) - apenas docker network

ufw enable
ufw status
```

### 2.4 Headers HTTP (Traefik)

```yaml
# middleware-security-headers.yml
http:
  middlewares:
    security-headers:
      headers:
        frameDeny: true
        sslRedirect: true
        browserXssFilter: true
        contentTypeNosniff: true
        forceSTSHeader: true
        stsIncludeSubdomains: true
        stsPreload: true
        stsSeconds: 31536000
        
        customRequestHeaders:
          X-Forwarded-Proto: "https"
          X-Real-IP: "{client.ip}"
        
        customResponseHeaders:
          X-Robots-Tag: "noindex, nofollow"
          Referrer-Policy: "strict-origin-when-cross-origin"
          Permissions-Policy: "geolocation=(), microphone=(), camera=()"
        
        # CSP
        contentSecurityPolicy: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.2notasudi.com.br wss://agent.2notasudi.com.br; frame-ancestors 'none'"
```

---

## 3. Camada de Infraestrutura

### 3.1 Docker Swarm Isolation

```yaml
# docker-compose.yml (Easypanel)
networks:
  cartorio_frontend:
    driver: overlay
  cartorio_backend:
    driver: overlay
    internal: true  # SEM acesso externo
  
services:
  api:
    networks:
      - cartorio_frontend
      - cartorio_backend
    # SEM ports (apenas Traefik)
  
  postgres:
    networks:
      - cartorio_backend
    # SEM access a internet
  
  redis:
    networks:
      - cartorio_backend
    # SEM access a internet
```

### 3.2 Secrets Management

```bash
# Supabase Vault (8 secrets armazenados)
# - API keys
# - Tokens
# - Senhas de DB

# Acessar vault via SQL
SELECT name, secret FROM vault.secrets;

# Criar secret
INSERT INTO vault.secrets (name, secret)
VALUES ('minha_api_key', 'xxx');

# Usar em função
CREATE FUNCTION get_minha_key() RETURNS TEXT AS $$
  SELECT secret FROM vault.secrets WHERE name = 'minha_api_key';
$$ LANGUAGE sql;
```

### 3.3 Filesystem Permissions

```bash
# .env files (600 - apenas owner)
chmod 600 /etc/easypanel/projects/cartorio/*/.env

# SSH key
chmod 600 ~/.ssh/id_ed25519_cartorio
chmod 644 ~/.ssh/id_ed25519_cartorio.pub

# Backup directory (700)
chmod 700 /var/backups/cartorio/
```

### 3.4 Update Policy

```bash
# Atualizar SO (mensal)
ssh vps-cartorio "apt update && apt upgrade -y"

# Atualizar Docker (trimestral)
ssh vps-cartorio "apt install --only-upgrade docker-ce"

# Atualizar containers (contínuo)
# Easypanel UI: pull latest image
# OU: GitHub Actions rebuild
```

---

## 4. Camada de Aplicação

### 4.1 CORS

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # dev
        "https://admin.2notasudi.com.br",
        "https://app.2notasudi.com.br",
        "https://chat.2notasudi.com.br",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
    max_age=3600,  # cache preflight 1h
)
```

### 4.2 Rate Limiting (E8.A22)

```python
# backend/app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis:6379",
    default_limits=["100/minute"]
)

# Aplicar em endpoint
@app.get("/api/v1/emolumentos")
@limiter.limit("50/minute")  # mais restritivo
async def listar_emolumentos():
    ...

# Rate limit por usuário autenticado
@app.get("/api/v1/clientes/me")
@limiter.limit("200/minute", key_func=lambda: get_jwt_subject())
async def meus_dados():
    ...
```

### 4.3 Autenticação

```python
# API Key (para integrações N8N → API)
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# JWT (para usuários finais)
from jose import jwt, JWTError

async def verify_jwt(authorization: str = Header(...)):
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401)
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401)
```

### 4.4 Input Validation (Pydantic V2)

```python
# SEMPRE validar entrada
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

class ClienteCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, strict=True)
    
    nome: str = Field(..., min_length=3, max_length=200)
    cpf: str = Field(..., pattern=r'^\d{11}$')  # só dígitos, 11 chars
    telefone: str = Field(..., pattern=r'^\d{10,11}$')
    email: str = Field(..., max_length=200)
    
    @field_validator('cpf')
    @classmethod
    def validar_cpf(cls, v):
        # Validação completa de CPF (dígitos verificadores)
        if not cpf_validator(v):
            raise ValueError('CPF inválido')
        return v
    
    @field_validator('email')
    @classmethod
    def validar_email(cls, v):
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Email inválido')
        return v.lower()
```

### 4.5 PII Scrub

```python
# backend/app/middleware/pii_scrub.py
import re

PII_PATTERNS = {
    'cpf': r'\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}',
    'cnpj': r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}',
    'rg': r'\d{1,2}\.\d{3}\.\d{3}-[\dX]',
    'phone': r'\(?\d{2}\)?\s?9?\d{4}-?\d{4}',
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'cns': r'\d{3}\s?\d{4}\s?\d{4}\s?\d{4}',
}

def scrub_pii(text: str) -> str:
    for pii_type, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f'[REDACTED-{pii_type.upper()}]', text)
    return text

# Usar ANTES de logar
logger.info(scrub_pii(f"Cliente {cliente.nome} CPF {cliente.cpf}"))
# Output: "Cliente [REDACTED-NOME] CPF [REDACTED-CPF]"
```

### 4.6 SQL Injection Prevention

```python
# ✅ SEGURO: SQLAlchemy ORM
cliente = session.query(Cliente).filter_by(cpf=cpf_input).first()

# ✅ SEGURO: Parametrized query
session.execute(text("SELECT * FROM clientes WHERE cpf = :cpf"), {"cpf": cpf_input})

# ❌ INSEGURO: f-string (NUNCA!)
# session.execute(f"SELECT * FROM clientes WHERE cpf = '{cpf_input}'")
```

### 4.7 Audit Log

```python
# backend/app/services/audit.py
async def log(
    action: str,  # CREATE, READ, UPDATE, DELETE, EXPORT, EXCLUSION
    entity_type: str,
    entity_id: str,
    dados_before: dict | None = None,
    dados_after: dict | None = None,
    user_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    correlation_id: str | None = None,
):
    """Log LGPD art. 37 (rastreabilidade)."""
    audit_entry = AuditLog(
        correlation_id=correlation_id,
        user_id=user_id or 'sistema',
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        dados_before=dados_before,
        dados_after=dados_after,
        ip=ip,
        user_agent=user_agent,
        # chain_hash garante integridade
        chain_hash=compute_chain_hash(previous_hash, payload),
    )
    session.add(audit_entry)
    session.commit()
```

---

## 5. Camada de Dados

### 5.1 Encryption at Rest

```bash
# Supabase: dados criptografados em disco (LUKS no VPS)
ssh vps-cartorio "lsblk"
# Esperado: sda com crypto_LUKS

# Backups: criptografados antes de upload S3
gpg --symmetric --cipher-algo AES256 backup-2026-06-26.tar.gz
```

### 5.2 Encryption in Transit

```
✅ TLS 1.3 (Traefik + Let's Encrypt)
✅ mTLS para comunicações internas (futuro)
✅ WireGuard (Tailscale)
```

### 5.3 RLS (Row Level Security)

```sql
-- Já ativo em clientes, protocolos, documentos, audit_log

-- Verificar
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND rowsecurity = true;
```

### 5.4 Backup Encryption

```bash
# Criptografar antes de S3
gpg --symmetric --cipher-algo AES256 \
  --passphrase-file /root/.backup_passphrase \
  backup-2026-06-26.tar.gz

aws s3 cp backup-2026-06-26.tar.gz.gpg s3://cartorio-backups/

# Limpar local
shred -u /root/.backup_passphrase  # após uso
```

### 5.5 Data Minimization (LGPD)

```python
# Endpoint retorna APENAS dados necessários
@router.get("/clientes/{id}", response_model=ClientePublic)
async def get_cliente(id: UUID):
    cliente = session.query(Cliente).get(id)
    
    # NÃO retorna cpf, telefone, email completos
    return ClientePublic(
        id=cliente.id,
        nome=cliente.nome[:3] + "***",  # mascarado
        criado_em=cliente.created_at.date()
    )
```

---

## 6. LGPD e Compliance

### 6.1 Direitos do Titular (D06-D25)

**Implementados** (100%):

| Direito | Endpoint | Status |
|---------|----------|--------|
| D06 Acesso | `GET /api/v1/lgpd/meus-dados/{cpf}` | ✅ |
| D07 Correção | `PATCH /api/v1/lgpd/meus-dados/{cpf}` | ✅ |
| D08 Portabilidade | `GET /api/v1/lgpd/portabilidade/{cpf}` | ✅ |
| D09 Exclusão | `DELETE /api/v1/lgpd/meus-dados/{cpf}` | ✅ |
| D10 Revogação consent | `DELETE /api/v1/lgpd/consent/{id}` | ✅ |
| D11 Oposição | `POST /api/v1/lgpd/oposicao` | ✅ |
| D12 Informação | `GET /api/v1/lgpd/info` | ✅ |
| D13 Anonimização | Auto (30 dias após exclusão) | ✅ |
| D14 Revisão decisão automatizada | `POST /api/v1/lgpd/review` | ✅ |
| D15-D25 | Outros direitos | ✅ |

### 6.2 Bases Legais (Art. 7º)

| Tratamento | Base Legal |
|------------|-----------|
| Cadastro de cliente | Execução de contrato (I) |
| Atendimento WhatsApp | Legítimo interesse (IX) |
| Marketing/prospecção | Consentimento (I) |
| Auditoria interna | Legítimo interesse (IX) |
| Backup de dados | Legítimo interesse (IX) |
| Compartilhamento com Evolution/Chatwoot | Execução de contrato (I) |

### 6.3 RIPD (Relatório de Impacto)

**Localização**: `/docs/ripd.md` v1.1 (atualizar para v1.2)

**Conteúdo mínimo** (LGPD art. 38):
- Descrição dos tratamentos
- Riscos identificados
- Medidas de mitigação
- Medidas de segurança

### 6.4 DPO Designado

- **Email**: dpo@2notasudi.com.br
- **Publicado em**: /docs/privacy-policy.md

---

## 7. Monitoramento de Segurança

### 7.1 Alertas de Segurança

```yaml
# Prometheus
- alert: FailedAuthRate
  expr: rate(api_auth_failures_total[5m]) > 10
  for: 5m
  labels: {severity: warning}
  annotations:
    summary: "Taxa alta de falhas de autenticação"
    
- alert: SQLInjectionAttempt
  expr: rate(api_pii_detected_total[5m]) > 1
  for: 1m
  labels: {severity: critical}
  annotations:
    summary: "Possível tentativa de SQL injection detectada"
    
- alert: AuditLogStalled
  expr: time() - audit_log_last_insert_timestamp > 3600
  for: 10m
  labels: {severity: critical}
  annotations:
    summary: "Audit log parado há mais de 1h"
    
- alert: DiskUsageHigh
  expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
  for: 10m
  labels: {severity: warning}
  annotations:
    summary: "Disco com menos de 10% livre"
    
- alert: CertExpiringSoon
  expr: probe_ssl_earliest_cert_expiry - time() < 86400 * 14
  for: 1h
  labels: {severity: warning}
  annotations:
    summary: "Certificado SSL expira em < 14 dias"
```

### 7.2 Audit Log Monitoring

```bash
# Detectar acessos suspeitos
psql $SUPABASE_URL -c "
  SELECT user_id, count(*), 
         array_agg(DISTINCT entity_type) as entidades
  FROM audit_log 
  WHERE created_at > NOW() - INTERVAL '1 hour'
  GROUP BY user_id
  HAVING count(*) > 1000  -- threshold
  ORDER BY count DESC;
"

# Detectar exfiltração (download em massa)
psql $SUPABASE_URL -c "
  SELECT user_id, count(*)
  FROM audit_log
  WHERE action = 'EXPORT' 
    AND created_at > NOW() - INTERVAL '1 hour'
  GROUP BY user_id
  HAVING count(*) > 5
  ORDER BY count DESC;
"
```

### 7.3 Log de Segurança (Centralizado)

```bash
# Eventos a logar:
✅ Auth success/failure
✅ Authz failure (403)
✅ Rate limit hit (429)
✅ PII detectado em log
✅ Audit log interrompido
✅ Backup success/failure
✅ Deploy executado
✅ Migration executada
✅ Config change
✅ Secret access (Supabase Vault)
```

---

## 8. Incident Response

Ver `/docs/INCIDENT_RESPONSE_PLAYBOOK.md` (criado nesta sessão).

**Em caso de data breach**:
1. CONTER (reverter deploy, bloquear IP, revogar token)
2. AVALIAR (impacto, titulares, dados)
3. NOTIFICAR (DPO → Gustavo → ANPD 72h → Titulares)
4. DOCUMENTAR (postmortem em 48h)
5. APRENDER (adicionar teste de regressão)

---

## 9. Auditoria

### 9.1 Auditoria Interna (Mensal)

```bash
# Checklist
□ Revisar audit_log (acessos incomuns)
□ Revisar logs de auth (tentativas falhadas)
□ Verificar permissões (least privilege)
□ Validar RLS (não bypassado indevidamente)
□ Verificar certificados SSL
□ Atualizar dependências (pip-audit)
□ Verificar secrets (não em código)
□ Testar backup/restore
□ Revisar alerts (falsos positivos?)
```

### 9.2 Auditoria Externa (Anual)

- ANPD (se aplicável)
- Auditoria interna da empresa
- Pentest externo (recomendado anual)

### 9.3 Ferramentas

| Ferramenta | Função |
|------------|--------|
| **pip-audit** | Vulnerabilidades em deps Python |
| **bandit** | Análise estática de segurança Python |
| **safety** | DB de vulnerabilidades |
| **OWASP ZAP** | Scan de vulnerabilidades web |
| **nmap** | Port scan |
| **nikto** | Web server scanner |
| **sqlmap** | SQL injection detection |

```bash
# pip-audit (CI obrigatório)
pip-audit --strict

# bandit
bandit -r backend/app/ -ll

# OWASP ZAP (manual)
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://api.2notasudi.com.br
```

---

## 10. Checklist de Hardening

### 10.1 Rede

- [x] Cloudflare Proxy ON
- [x] SSL/TLS Full (Strict)
- [x] HSTS com preload
- [x] WAF rules ativas
- [x] Rate Limiting no Cloudflare
- [x] Tailscale VPN para admin
- [x] UFW ativo na VPS
- [x] Portas internas NÃO expostas
- [x] Security headers (CSP, HSTS, X-Frame-Options)

### 10.2 Infraestrutura

- [x] Docker Swarm isolation
- [x] Network policies (frontend/backend)
- [x] Secrets em Supabase Vault
- [x] Filesystem permissions 600 para .env
- [x] SSH key-based auth
- [x] Update policy mensal

### 10.3 Aplicação

- [x] CORS restritivo
- [x] Rate Limiting (slowapi + Redis)
- [x] Autenticação JWT + API Key
- [x] Pydantic V2 validação
- [x] PII Scrub em logs
- [x] SQL parametrizado (SQLAlchemy)
- [x] Audit log em ações sensíveis
- [x] Sem secrets em código
- [x] Sem eval/exec
- [x] Sem pickle (desserialização insegura)

### 10.4 Dados

- [x] Encryption at rest (LUKS)
- [x] Encryption in transit (TLS 1.3)
- [x] RLS em tabelas com PII
- [x] Backup encryption (GPG)
- [x] Data minimization em responses
- [x] Audit log 5 anos (LGPD)
- [x] Direito de exclusão (30d)
- [x] Direito de portabilidade

### 10.5 LGPD

- [x] DPO designado
- [x] RIPD v1.1
- [x] Termo de consentimento
- [x] Política de privacidade
- [x] Direitos D06-D25 implementados
- [x] Bases legais documentadas
- [x] Data breach procedure (72h ANPD)
- [x] Audit log completo

### 10.6 Monitoramento

- [x] Alertas Prometheus configurados
- [x] Audit log monitoring
- [x] Failed auth tracking
- [x] Rate limit monitoring
- [x] Cert expiry monitoring
- [x] Dead man's switch (audit log)

### 10.7 Resposta

- [x] Incident Response Playbook
- [x] Bridge de incidente (template)
- [x] Escalation chain definida
- [x] Contatos atualizados
- [x] Postmortem template
- [x] LGPD breach notification template

---

## Recursos

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **LGPD**: https://www.gov.br/anpd/
- **Cloudflare Security**: https://developers.cloudflare.com/
- **PostgreSQL Security**: https://www.postgresql.org/docs/current/sql-syntax.html
- **Troubleshooting**: `/docs/TROUBLESHOOTING.md`
- **Incident Response**: `/docs/INCIDENT_RESPONSE_PLAYBOOK.md`
- **LGPD**: `/docs/LGPD.md`
- **Database Ops**: `/docs/DATABASE_OPERATIONS.md`

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-02
**Versão**: 1.0.0
