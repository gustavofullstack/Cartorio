# F1 — Health Radar Evidence

**Data**: 2026-07-13 19:44:04 UTC
**Owner**: Gustavo Almeida
**Executor**: TRAE SOLO M3 (batch F1)

## F1.1 health/radar
```json
{
    "status": "red",
    "services": {
        "database": "online",
        "redis": "online",
        "n8n": "offline",
        "openclaw": "online",
        "evolution": "offline",
        "chatwoot": "online",
        "supabase": "online"
    }
}
```

## F1.4 openclaw
```json
{
    "ok": true,
    "status": "live"
}
```

## F1.5 webhook chatwoot (test payload)
```
{"status":"processed","event_type":"message_created","event_id":""}```

## F1.5 webhook evolution (test payload)
```
{"status":"ok","response":"Recebi uma mensagem sem texto util. Vou transferir para um atendente humano para que possamos ajudar melhor.","scrubbed":"","pii_blocked":false,"needs_human_handoff":true,"handoff_reason":"payload_empty_message"}```

## F1.3 chatwoot sim stats (10 conversas inbox=2)
```
CONTACTS sinteticos total: 10
  agent=ANTIGRAV count=5
    #  8 slot=sim-06 Carlos Mendes                  35 anos cenario=divorcio
    # 10 slot=sim-08 Roberto Carlos                 71 anos cenario=testamento
    #  9 slot=sim-07 Ana Beatriz Rocha              19 anos cenario=emancipacao
    # 11 slot=sim-09 Sofia Martins                  40 anos cenario=compra_venda_imovel
    # 12 slot=sim-10 Antonio José                   90 anos cenario=inventario
  agent=TRAE count=5
    #  3 slot=sim-01 Maria Silva Santos             67 anos cenario=certidao_casamento
    #  5 slot=sim-03 Helena Costa Oliveira          82 anos cenario=escritura_imovel
    #  4 slot=sim-02 José Pereira Souza             28 anos cenario=procuracao
    #  7 slot=sim-05 Lucia Ferreira                 55 anos cenario=certidao_obito
    #  6 slot=sim-04 Pedro Almeida Lima             45 anos cenario=registro_nascimento

CONVERSATIONS inbox=2 total (open+resolved+pending): 10
  conv# 12 contact=None status=open     incoming=3 outgoing=3 total=6
  conv# 11 contact=None status=open     incoming=3 outgoing=3 total=6
  conv# 10 contact=None status=open     incoming=2 outgoing=2 total=4
  conv#  9 contact=None status=open     incoming=3 outgoing=3 total=6
  conv#  8 contact=None status=open     incoming=3 outgoing=3 total=6
  conv#  7 contact=None status=open     incoming=2 outgoing=2 total=4
  conv#  6 contact=None status=open     incoming=3 outgoing=3 total=6
  conv#  5 contact=None status=open     incoming=3 outgoing=3 total=6
  conv#  4 contact=None status=open     incoming=3 outgoing=3 total=6
  conv#  3 contact=None status=open     incoming=3 outgoing=3 total=6
```
