# Domain Typo Decision — supbase.2notasudi.com.br

**Data da decisao:** 2026-06-25 | **Reconfirmado:** 2026-07-15 (cartorio-sre F4)
**Owner da decisao:** Gustavo Almeida | **Ref:** cartorio-sre F4 / T053

---

## Contexto

O subdominio canonico para o servico Supabase self-hosted seria supabase.2notasudi.com.br (com 'p' duplo: sup + base). Porem, em 2026-06-24 quando a squad A configurou o primeiro deploy do Supabase via Cloudflare, o subdominio foi digitado como supbase.2notasudi.com.br (typo: 'p' simples). O A record foi criado, o servico subiu, e o dominio typo virou padrao de fato.

---

## Decisao (ACEITO — nao alterar)

O subdominio supbase.2notasudi.com.br (typo) e CANONICO para o servico Supabase. Nao sera renomeado para supabase.2notasudi.com.br no Cloudflare.

---

## Justificativa

1. **Custo de migracao alto vs beneficio baixo.** Alterar agora exige:
   - Criar novo A record para supabase.2notasudi.com.br (UI Cloudflare — Gustavo, ~30s)
   - Adicionar novo Traefik router para Host(supabase.2notasudi.com.br) (merge manual no /etc/traefik/dynamic/main.yaml)
   - Atualizar TODAS as referencias internas no codigo:
     - backend/app/services/* (health checks, DATABASE_URL, storage URLs)
     - backend/app/api/v1/integrations.py (Supabase base URL)
     - backend/.env.example (SUPABASE_URL)
     - infra/n8n-workflows/*.json (HTTP node URLs)
     - docs/*.md (referencias em 6+ arquivos)
     - deploy/secrets.example.env
     - test fixtures (tests/conftest.py)
   - Atualizar links externos:
     - Painel Chatwoot (Evolution channel config)
     - LobeChat agent config
     - Documentacao da API para clientes
   - Fazer deploy coordenado com downtime zero
   - Atualizar audit log + LGPD records (URL do storage conta como recurso de processing)

2. **Risco de breaking change.** Supabase e storage de PII criptografada (cpf_hash, rg_hash). Renomear a URL quebra qualquer link assinado (signed URLs) que ja foi gerado e esta em uso por clientes ativos. Forcaria invalidacao massiva de URLs de download de documentos.

3. **Nenhum valor de negocio adicionado.** O typo supbase nao impede nenhum fluxo. Nao causa confusao em logs (ja que o typo aparece uniformemente). Nao afeta SEO (dominio interno, nao indexado). Nao causa problema de seguranca (mesmo certificado SSL, mesmo proxy Cloudflare).

4. **Principio de menor mudanca.** Regra geral: nao renomear nada em prod sem motivo claro. Custo > beneficio.

---

## Convencao adotada

- supbase.2notasudi.com.br (typo) = servico Supabase self-hosted — CANONICO
- supabase.2notasudi.com.br (correto) = sera criado como ALIAS do mesmo servico, redirecionando 301 para supbase (workaround opcional, NAO planejado para 2026 Q3)

> Nota tecnica: redirecionamento 301 entre subdominios do mesmo apex domain (2notasudi.com.br) e simples via Cloudflare Page Rules ou Workers. Porem, NAO foi implementado. Se for decidido no futuro, ver infra/traefik/ROUTERS_PENDENTES.yaml secao `cartorio-supabase-redirect`.

---

## Implicacoes para o DNS Runbook (T051/T052)

Ao criar os 3 A records pendentes (chatwoot / n8n / supabase) — ver infra/dns/CLOUDFLARE_RUNBOOK.md — o Gustavo vai naturalmente criar o supabase.2notasudi.com.br canonico. Este A record NAO precisa ser usado imediatamente. Pode ficar como reserva para o redirect futuro, ou ser deletado.

**Recomendacao operacional:** criar o A record `supabase` mesmo assim (custo zero) para evitar NXDOMAIN persistente no log do Cloudflare. Manter como reserva.

---

## Cross-refs

- infra/dns/CLOUDFLARE_DNS_RECORDS.md — tabela canonica de A records (linha #10 supabase)
- infra/dns/CLOUDFLARE_RUNBOOK.md — passo-a-passo UI
- infra/traefik/ROUTERS_PENDENTES.yaml — `cartorio-supabase` (pendente, opcional)
- .harness/memory/MEMORY.md — busca por "supbase" ou "typo DNS" para historico completo

Modified by Gustavo Almeida
