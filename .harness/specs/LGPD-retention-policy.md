# LGPD Política de Retenção — aplicada aos 13 endpoints LGPD

> **Para**: cartorio-dev (implementar job) + Mavis (aprovar)
> **De**: cartorio-lgpd (Pietra) — gatekeeper
> **Base**: LGPD Lei 13.709/2018 + Provimento 74/2018 CNJ + LGPD art. 16 (minimização) + art. 37 (registro)
> **Aplicar**: 7 novos (D26-D32) + 6 stubs migrados (anonimizar, corrigir, oposicao, optout, portabilidade, download)

## Princípio geral

Retenção é determinada pela **base legal** do tratamento (LGPD art. 7º):
- **art. 7º II (obrigação legal)** → retenção MÍNIMA do setor (cartório: 5 anos para protocolo)
- **art. 7º I (consentimento)** → retenção ATÉ REVOGAÇÃO (sem prazo fixo)
- **art. 7º IX (interesse legítimo)** → retenção NECESSÁRIA para a finalidade (limitada)

Quando há conflito (ex: protocolo tem base legal obrigatória MAS dados pessoais têm consentimento revogado), prevalece a base legal mais forte (obrigação legal > consentimento).

---

## §1. Decisão D29 — Export Portabilidade (HÍBRIDO)

### Contexto
D29 (`GET /api/v1/lgpd/export/{cliente_id}`) gera um JSON com PII do titular. Qual a retenção?

### Decisão: HÍBRIDO em 3 camadas

| Camada | Conteúdo | Retenção | Base legal | Após retenção |
|---|---|---|---|---|
| **Payload JSON (com PII)** | `bundle_json` salvo para regeneração do download | Até revogação (consentimento, art. 7 I) | art. 7 I + art. 18 V | Apagar |
| **TTL do link de download** | URL `/export/{id}/download` válida por 90 dias | 90 dias | art. 7 I | Regenerar link mediante solicitação |
| **Audit da solicitação** | `audit_log` entry com `action=lgpd.cliente.export` | 5 anos | art. 37 + 50 | Manter (sem PII puro) |
| **Hash SHA256 do payload** | `export_hash` para verificação de integridade | 5 anos | art. 50 (boas práticas) | Manter (NÃO contém PII) |

### Justificativa jurídica

- **Payload até revogação**: titular pode pedir o export novamente a qualquer momento (consentimento contínuo, art. 7 I). Não há obrigação legal de manter para sempre.
- **TTL 90 dias**: prazo razoável para o titular baixar o arquivo (LGPD não define prazo específico; 90 dias é prática de mercado).
- **Audit 5 anos**: obrigação legal (LGPD art. 37 + art. 50 boas práticas). Não pode ser revogado pelo titular (é registro de operação, não tratamento).
- **Hash 5 anos**: integridade do histórico sem reter PII (LGPD art. 50 — segurança da informação).

### Implementação

```python
# app/jobs/retention.py (NEW)
async def retention_export_portabilidade():
    """D29 retention: apaga payload > 90 dias após exportação SE cliente revogou.
    
    Se cliente NÃO revogou: regenera link.
    Se cliente REVOGOU (consentimento_lgpd=False): apaga payload.
    Audit log da solicitação: SEMPRE mantido 5 anos.
    Hash SHA256: SEMPRE mantido 5 anos.
    """
    ...
```

---

## §2. Decisão D27 — Consentimento Granular

### Retenção por campo

| Campo | Retenção | Base legal |
|---|---|---|
| `consent.granted` (bool) | Enquanto durar relação + 5 anos | art. 7 I + art. 16 |
| `consent.em` (timestamp) | Enquanto durar relação + 5 anos | art. 7 I + art. 16 |
| `consent.ip` (completo) | 2 anos, depois trunca /24 | art. 7 IX (segurança) |
| `consent.canal` | Enquanto durar relação + 5 anos | art. 7 I |
| `consent_history[]` (revogações) | 5 anos (manter prova) | art. 37 + art. 8 §5 |
| `justificativa_dpo` (string) | Enquanto durar relação + 5 anos | art. 7 I |

### Regra prática
- Cliente ATIVO: manter histórico completo (granted + revoked + IP + canal)
- Cliente REVOGOU (TODAS): manter APENAS registro da revogação (5 anos)
- Cliente inativo > 5 anos: anonimizar PII, manter apenas hash + flag revoked/active

---

## §3. Decisão D31 — Revogação de Consentimento

### Retenção

- **Registro da revogação**: 5 anos (LGPD art. 37 + art. 16)
  - Manter: `cliente_id`, `finalidade`, `data_revocacao`, `canal`, `hash_ator`
  - Apagar: `ip` após 2 anos (manter apenas truncado /24)
- **Audit chain entry da revogação**: 5 anos (igual a qualquer audit)
- **Efeitos aplicados** (consentimento_lgpd=False): PERMANENTE (não reverter)

### Edge case — cliente revoga mas tem protocolo ativo
- Atendimento cartorário CONTINUA (base legal art. 7 II — obrigação legal)
- Anonimização NÃO é aplicada automaticamente — apenas SUGERIDA via flag `sugerir_anonimizacao=true`
- Cliente deve exercer D28 separadamente se quiser eliminação completa

---

## §4. Audit log (D26-D32 + stubs) — TODOS

### Retenção: 5 anos (LGPD art. 37)

Campos MANTIDOS 5 anos:
- `id`, `prev_hash`, `hash`, `hmac`, `timestamp`
- `actor_id` (SEM PII — usar hash se necessário)
- `actor_type`, `action`, `resource`
- `payload` (dict — NUNCA string com PII puro)
- `ip_truncated` (/24 IPv4, /48 IPv6)
- `canal`

Campos com retenção REDUZIDA:
- `ip` (completo): 2 anos, depois apagar (manter `ip_truncated`)
- `user_agent`: 2 anos, depois truncar para browser family only

Campos NUNCA armazenados:
- PII puro (CPF, RG, email, telefone) — usar `cpf_hash`, `telefone_hash`

---

## §5. Política Híbrida aplicada aos 13 endpoints

| Endpoint | LGPD art. | Base legal dominante | Retenção específica | Após retenção |
|---|---|---|---|---|
| **D26 GET /lgpd/dashboard** | 41 + 50 + 37 | Obrigação legal (DPO) | Audit 5 anos | Manter |
| **D27 POST /lgpd/consent** | 7 I + 8 | Consentimento | Registro consent = relação+5y; revogação = 5y | Anonimizar PII |
| **D28 DELETE /lgpd/cliente/{id}** | 18 VI + 16 | Mista | Soft 5y (Provimento 74) / Hard imediato | Hard: deletar; Soft: anonimiza cpf_hash 5y |
| **D29 GET /lgpd/export/{cliente_id}** | 18 V + 19 | Consentimento | Payload até revogação + TTL 90d download; Audit 5y; Hash 5y | Ver §1 |
| **D30 POST /lgpd/correct/{cliente_id}** | 18 III | Consentimento | Dados corrigidos: relação+5y; Audit diff 5y | Anonimizar PII |
| **D31 POST /lgpd/revogar-consent** | 18 IX + 8 §5 | Mista | Registro revogação 5y; efeitos permanentes | Manter audit |
| **D32 GET /lgpd/audit/{cliente_id}** | 18 VII + 37 | Obrigação legal | Audit retornado 5y; meta-auditoria 5y | Manter |
| **Stub anonimizar** | 18 IV + 16 | Mista | Hard/soft = D28 | Igual D28 |
| **Stub corrigir** | 18 III | Consentimento | Igual D30 | Igual D30 |
| **Stub oposicao** | 18 IX | Consentimento | Registro 5y | Manter audit |
| **Stub optout** | 18 IX (parcial) | Consentimento | Registro 5y | Manter audit |
| **Stub portabilidade** | 18 V + 19 | Consentimento | Igual D29 | Igual D29 |
| **Stub download** | 18 V + 19 | Consentimento | Igual D29 download | Igual D29 |

---

## §6. Conversas e Protocolos (referência)

| Dado | Retenção | Base legal | Após retenção |
|---|---|---|---|
| Conversa (texto scrubbed) | 365 dias | Consentimento (art. 7 I) | Apagar |
| Conversa (áudio/imagem) | 365 dias | Consentimento | Apagar |
| Protocolo COM ato lavrado | **5 anos** | Obrigação legal (Provimento 74) | Anonimizar (cpf_hash=NULL) |
| Protocolo SEM ato | Até revogação | Consentimento | Deletar |
| Documento jurídico | 20+ anos | Obrigação legal | Manter (anonimizar partes não essenciais) |
| Emolumento snapshot | Indeterminado | Obrigação legal | Manter |

---

## §7. IP de conexão (LGPD art. 37)

### Política de truncamento

| Estágio | IP armazenado | Retenção |
|---|---|---|
| Request chega | `request.client.host` (completo) | efêmero |
| Persistido no audit_log | `ip` (completo) + `ip_truncated` (auto-derivado) | `ip` completo: 2 anos; `ip_truncated`: 5 anos |
| Display ao titular (D32) | `ip_truncated` apenas | 5 anos |
| Display ao DPO (D26, D28, D29, etc) | `ip` completo | enquanto acesso do DPO |
| Métricas/aggregations | `ip_truncated` | 5 anos |

### Helper

```python
# app/utils/ip.py (já existe)
def truncate_ip(ip: str) -> str:
    """IPv4 → /24 (x.y.z.0/24); IPv6 → /48."""
    ...
```

---

## §8. Job diário de retenção (a implementar)

### Escopo

`backend/app/jobs/retention.py` (NEW) deve implementar:

```python
# Cron diário 03:00 BRT (depois do backup 02:00)
async def retention_daily_job():
    """Aplica política de retenção LGPD diariamente.
    
    Ordem de operações:
    1. Apaga conversas > 365 dias
    2. Apaga protocolos SEM ato + cliente revoked > 90 dias (consentimento)
    3. Anonimiza cpf_hash de protocolos COM ato > 5 anos (Provimento 74)
    4. Apaga payload de export > 90 dias (D29 TTL download)
    5. Apaga IP completo > 2 anos (mantém truncated)
    6. Trunca user_agent > 2 anos
    
    Cada operação gera audit chain entry com action='retention.applied'.
    """
```

### LGPD-014 flag

Se DPA DeepSeek não estiver assinado (backend STAGING ONLY), o job de retenção NÃO deve chamar nenhum LLM externo para sumarização/anonimização automatizada. Anonimização é feita por SQL puro (UPDATE tabela SET cpf_hash=NULL WHERE ...).

---

## §9. Comunicação ao titular sobre retenção

A política de retenção DEVE estar publicada em:
- `docs/LGPD.md` seção 8 (já existe)
- Política de privacidade pública (`docs/privacy-policy.md`)
- Bot: mensagem inicial sobre tratamento de dados

Texto padrão (citado em `LGPD-copy-juridica.md`):

```
Seus dados são mantidos por:
• 5 anos para protocolos lavrados (obrigação legal — Provimento 74 CNJ)
• Enquanto durar a relação + 5 anos para consentimentos
• 5 anos para logs de auditoria (LGPD art. 37)
• 365 dias para conversas de atendimento
• 2 anos para IP completo (depois truncado)

Após o prazo, dados pessoais são anonimizados ou eliminados conforme
a base legal aplicável. Você pode solicitar eliminação antecipada via
art. 18, VI (sujeito à retenção legal obrigatória).
```

---

## §10. Resumo de decisões (para revisão por Gustavo)

| # | Decisão | Aplicação | Responsável |
|---|---|---|---|
| 1 | D29 retenção HÍBRIDA (3 camadas) | D29 + stubs portabilidade/download | cartorio-dev implementa |
| 2 | IP completo 2 anos, truncado 5 anos | Audit log + D32 | Já implementado |
| 3 | Soft delete preserva cpf_hash 5 anos | D28 + stub anonimizar | Já implementado |
| 4 | TTL 90 dias para download D29 | D29 + stub download | cartorio-dev implementa |
| 5 | Job retenção diário 03:00 BRT | `backend/app/jobs/retention.py` | cartorio-dev implementa |
| 6 | LGPD-014 STAGING ONLY até DPA | Job retenção não usa LLM | Já documentado |

Modified by cartorio-lgpd (Pietra root mvs_97612f6bb1824cbdaf7c134fa34bf057)