# INDEX — Master Documentação (Cartório)

## 📂 Estrutura

```
docs/
├── INDEX/                    # Este diretório (master docs)
│   ├── INDEX.md              # este arquivo
│   ├── STATUS.md             # snapshot atual
│   ├── ROADMAP.md            # 12 semanas
│   ├── BACKLOG.md            # 317 tasks abertas
│   ├── BLOCKERS.md           # 6 pendências P0/P1/P2
│   ├── DECISIONS.md          # 24 ADRs
│   └── RUNBOOK_DNS_HOSTINGER.md  # SUI Gustavo
├── RIPD.md                   # Relatório Impacto Proteção Dados
├── LGPD.md                   # Política privacidade
├── ARCHITECTURE.md           # C4 diagrams + ADRs completos
├── API.md                    # 50+ endpoints
├── DB.md                     # 20+ tabelas + ER
├── DEPLOYMENT.md             # Docker Swarm
├── RUNBOOK_VPS.md            # Operação VPS
├── CONTRIBUTING.md           # Conventional commits
└── platforms/                # docs técnicas por vendor
    ├── n8n.md
    ├── evolution.md
    ├── chatwoot.md
    ├── supabase.md
    ├── redis.md
    └── INDEX.md
```

## 🎯 Ordem de leitura (Tier 1-4)

1. **Tier 1 (decisor)**: STATUS.md → ROADMAP.md → BLOCKERS.md → DECISIONS.md
2. **Tier 2 (arquiteto)**: ARCHITECTURE.md → RIPD.md → LGPD.md → API.md
3. **Tier 3 (dev)**: DB.md → BACKLOG.md → DEPLOYMENT.md → RUNBOOK_VPS.md
4. **Tier 4 (vendor)**: platforms/*.md

Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-06 17:50 BRT
