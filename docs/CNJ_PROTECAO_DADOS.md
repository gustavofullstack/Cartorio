# CNJ — Relatório de Proteção de Dados (G9.S4.T9 / E3.08)

Relatório agregado de proteção de dados gerado **a partir do audit log de
produção (somente leitura)**. Formato CNJ-shaped (JSON) + markdown para
anexação em comunicação ao CNJ / prestação de contas LGPD (art. 37 e 48).

## O que o relatório agrega

| Métrica | Origem no audit log |
| --- | --- |
| Total de acessos | contagem de entradas válidas no período |
| Acessos por ação | quebra por `action` (`protocolo.create`, `conversa.handoff`, …) |
| Exportações | ações de export/dump/download (`cnj.export.*`, `*.download`, …) |
| Mascaramentos PII | ações de scrub/mask **ou** payload com marcadores `[*_REDACTED]` / `redaction_count` |
| Falhas de autenticação | ações `auth.*fail/deny` **ou** payload com `status`/`status_code` 401/403 |
| Janela temporal | min/max de `timestamp` das entradas válidas |
| Entradas malformadas | linhas não-dict / sem `action` — toleradas e contadas à parte |

O artefato é classificado como **RESTRICTED_AGGREGATED**: apenas contagens
e janelas. Nunca serializa `actor_id`, payload bruto, IP ou qualquer dado
pessoal da fonte (minimização — LGPD art. 6º, XI).

## Como gerar a partir do audit log prod (read-only)

O serviço é puro (sem I/O): `app/services/cnj_protecao.py`. O chamador
extrai as entradas do banco em modo **read-only** e passa a lista de dicts.

```python
from app.services.cnj_protecao import build_protecao_report, render_protecao_markdown

# 1) Extração read-only (ex.: sessão com transaction mode read only,
#    ou réplica de leitura). NUNCA gravar nada nesta sessão.
entries = [
    {
        "id": row.id,
        "action": row.action,
        "payload": row.payload,          # já mascarado se vier do massive-dump
        "timestamp": row.timestamp.isoformat(),
    }
    for row in query_yield_per_1000  # paginar com yield_per(1000)
]

# 2) Agregação pura (sem DB).
report = build_protecao_report(entries)

# 3) Saídas.
import json
json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
md_path.write_text(render_protecao_markdown(report))
```

Alternativa sem tocar o banco primário: consumir a saída do
`GET /api/v1/lgpd/cnj-exports/massive-dump` (já scrubbed, cadeia SHA256
preservada) como `entries`. O relatório ignora campos de integridade
(`hash`, `prev_hash`, `hmac_*`) — só agrega `action`/`payload`/`timestamp`.

## Garantias (testes)

`backend/tests/test_cnj_protecao_g9.py` cobre: agregação correta, listas
vazias, entradas malformadas toleradas (contadas, nunca derrubam o
pipeline), timestamps ISO/`Z`/naive/inválidos, heurísticas de
export/mask/auth-fail, JSON-serializabilidade e minimização (nenhum dado
pessoal vaza no artefato).

## Sign-off

Geração automatizada: **DONE** (serviço puro + testes). Uso formal do
relatório em procedimento CNJ recorrente: depende de aprovação do DPO
humano a cada remessa (ver `docs/RIPD_MASSIVE_DUMP_NOTE.md` —
**BLOCKED_HUMAN** para sign-off LGPD formal).
