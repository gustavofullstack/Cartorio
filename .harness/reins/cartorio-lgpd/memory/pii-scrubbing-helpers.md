---
description: Helpers de PII para compliance — IP /24 truncation helper (IPv4 + IPv6 edge cases), lista de 14 formatos PII brasileiros (comum + sensível art. 5 II), hash chain integrity (o que está/não está no hash + 5 perguntas para QUALQUER audit log). Carrega quando auditar IP em logs, escrever/scrubber PII, revisar design de audit log append-only, ou checar cobertura de regex BR.
---

# PII helpers — IP truncation + 14 formatos BR + hash chain

## 1. IP truncation helper (LGPD art. 5 I)

IP puro identifica pessoa. Padrão: truncar em `/24` (IPv4) ou `/32` (IPv6) para display/audit, persistir completo com retenção curta (2y).

### Implementação canônica

```python
def _truncate_ip_to_24(ip: str) -> str:
    if not ip or ip == "unknown":
        return ip or "unknown"
    # IPv4
    if "." in ip and ":" not in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    # IPv6 (truncado em /32)
    if ":" in ip:
        groups = ip.split(":")
        if len(groups) >= 2:
            return f"{groups[0]}:{groups[1]}::/32"
    return ip  # formato nao reconhecido, retorna como veio
```

### Edge cases verificados

| Input | Output | OK? |
|-------|--------|-----|
| `192.168.1.123` | `192.168.1.0/24` | ✓ |
| `127.0.0.1` (loopback) | `127.0.0.0/24` | ✓ |
| `10.0.1.0/24` (já truncado) | `10.0.1.0/24` | ✓ (idempotente) |
| `2001:db8::1` | `2001:db8::/32` | ✓ |
| `fe80::1` | `fe80::/32` | ✓ |
| `::1` (IPv6 loopback) | `::/32` | ✓ |
| `localhost` | `localhost` | ✓ (sem PII) |
| `""` (vazio) | `unknown` | ✓ |
| `unknown` | `unknown` | ✓ |
| `fe80::1%eth0` (zone ID) | `fe80::/32` | ✓ |

### Por que /24 vs /32 vs /16 vs /20

| Granularidade | Uso |
|---------------|-----|
| /24 (IPv4) / /32 (IPv6) | Audit log (art. 37), painel admin — preserva util operacional |
| /16 (IPv4) / /48 (IPv6) | Compartilhamento com terceiro — anonimização mais forte |
| Remover IP | Dataset público, estatísticas |

**Atenção:** IPv4 /24 AINDA permite identificar pessoa em rede pequena (empresa, prédio) — usar /16 ou /20 se contexto exigir.

### Severidade do gap se mal implementado

- **P0:** NÃO trunca (vaza PII no audit log) — viola art. 37 + art. 5 I
- **P1:** Trunca mas retorna string malformada — dificulta investigação
- **P2:** Trunca parcialmente (preserva host identifier) — anonimização insuficiente

## 2. 14 formatos PII brasileiros

Lista canônica para QUALQUER regex/scrubber em projeto BR.

### Comuns (art. 5 I)

- CPF (formato 3-3-3-2 + 11 dígitos soltos)
- CNPJ (formato 2-3-3-4-2 + 14 dígitos soltos)
- PIS/PASEP (3-5-3 + 11 solto; **ATENÇÃO:** regex bug histórico confundia 3-6-2 com 3-5-3)
- RG (formatos variam por estado)
- Título de eleitor (12 dígitos)
- Email (regex padrão)
- Telefone BR (com DDD, vários formatos)
- CEP (8 dígitos)
- Cartão (15/16 dígitos — bandeira detecta)
- Placa veículo (formato antigo + Mercosul)
- Data BR (DD/MM/YYYY) + ISO (YYYY-MM-DD)

### Sensíveis (art. 5 II — agravante)

- **CNH (11 dígitos E 9 antigo)** — atenção: casa como CPF em regex limitado, falso positivo perigoso
- **CNS (15 dígitos ou 15+2)** — vazamento para LLM externa = violação GRAVE (dado de saúde)
- Passaporte BR (AB + 6 dígitos)

### Heurística ao auditar QUALQUER serviço de PII

1. Listar todos os regex ativos
2. Rodar `detect_only()` contra os 14 formatos BR canônicos (script rápido)
3. Verificar response shape de endpoint principal — signal de compliance intacto? (`status=pii_blocked`, `needs_human_handoff`)
4. Verificar audit log — DETECÇÃO E BLOQUEIO E HANDOFF logados separadamente?
5. Verificar RIPD/doc LGPD — CNS, CNH mencionados?

## 3. Hash chain integrity — 5 perguntas para QUALQUER audit log

Quando revisar QUALQUER sistema com audit log append-only + hash chain:

- **Q1.** O que está no hash? (ler `_compute_hash` ou equivalente)
- **Q2.** Posso atualizar metadados pós-insert sem quebrar a chain?
- **Q3.** Há race conditions no padrão de enriquecimento (SELECT after INSERT)?
- **Q4.** A biblioteca expõe kwargs para os metadados? (`request_id`, `ip`, `user_agent`, `canal`)
- **Q5.** Os testes de chain integrity (`verify_chain`) testam isso?

### Insight fundamental

`hash = H(prev_hash, payload, timestamp)` — **NAO inclui** `request_id`, `ip`, `user_agent`, `canal`.

- Posso atualizar esses metadados **DEPOIS** do insert (via UPDATE direto) **SEM quebrar o hash chain**
- O hash garante integridade do payload + posição na cadeia (prev_hash) + timestamp
- Metadados podem ser enriquecidos pós-fato (by design)

**Sinal amarelo:** SELECT-after-INSERT para "enriquecer" é frágil em multi-thread. Melhor design: passar `request_id`/`ip` DIRETO para `AuditService.log()` (kwargs).

### Severidade típica do gap

- **P0:** hash inclui metadados E são atualizados pós-insert (chain quebrada)
- **P1:** hash NAO inclui metadados mas padrão fragil (race condition)
- **P2:** design aceitável mas doc não explica

### Cross-project

Esse pattern aparece em:
- Blockchain-like logs (Hyperledger, Ethereum-like)
- Audit trail systems (SOC 2, ISO 27001)
- Database triggers que logam + enriquecem
- Event sourcing (CQRS)

## Cross-project application

Esses patterns aparecem em QUALQUER sistema com compliance (LGPD, GDPR, CCPA, HIPAA):
- IP truncation → udiapods, futuros SaaS B2B
- 14 formatos BR → qualquer chatbot/scrubber BR
- Hash chain → qualquer sistema com audit log
