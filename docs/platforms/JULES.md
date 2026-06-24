# Jules - Google Gemini 3.1 Pro (Coding Agent)

> **Integracao com Jules (coding agent autonomo do Google) para auxiliar nas tasks.**
> API key: `AQ.Ab8RN6K26NJ3FFYfkXpT3-_dwFtDH-Lrmqm5jrkkE7CNUGzsBQ`
> **NAO ROTACIONAR** - Gustavo + ZCode unicos com acesso.
> Doc: https://developers.google.com/jules/api

## Visao geral

Jules e' um **coding agent autonomo** do Google baseado em **Gemini 3.1 Pro**. Roda em sandbox isolada. Tem acesso a:
- **Git** (clona, le, escreve, commita)
- **MCP servers** (Linear, Stitch, Context7, v0, Render)
- **Render** (deploy previews automaticos)

**Por que usamos**: 2o agente AI independente para tasks mais complexas (UI/UX, refactor grande, debug profundo). Complementa o ZCode (eu) com visao diferente.

## MCPs integrados (5)

| MCP | Proposito | Quando usar |
|---|---|---|
| **Linear** | Project management (issues, sprints) | Sync de tasks com Linear (se aplicavel) |
| **Stitch** | UI/UX design (Figma-like) | Gerar mockups de UI antes de implementar |
| **Context7** | Docs atualizadas de bibliotecas | Quando precisar de doc oficial recente |
| **v0** | Gerador de UI React/Vue | Para prototipos rapidos de UI |
| **Render** | Deploy previews + MCP | Auto-fix de build errors em PRs |

## Como usar Jules

### 1. Criar sessao Jules

```bash
curl -X POST "https://jules.googleapis.com/v1alpha/sessions" \
  -H "Authorization: Bearer $JULES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Implementar feature X no projeto Cartorio",
    "source": "github:gustavofullstack/Cartorio",
    "branch": "feat/jules-implementar-x"
  }'
```

### 2. Polling status

```bash
curl "https://jules.googleapis.com/v1alpha/sessions/SESSION_ID" \
  -H "Authorization: Bearer $JULES_API_KEY"
```

### 3. Workflow tipico

1. Gustavo/ZCode cria task
2. Se for complexa (UI/UX, refactor grande), spawna Jules
3. Jules le codigo, planeja, implementa, testa
4. Jules cria PR
5. ZCode revisa PR, commita na master, ou deleta se nao for bom

### 4. Boas praticas com Jules

- **SEMPRE** dar contexto rico: arquivos, padroes, LGPD, LGPD art. 6 VIII (prevencao)
- **SEMPRE** pedir para Jules rodar testes ANTES de commitar
- **SEMPRE** revisar PR de Jules (NAO confiar cegamente)
- **DELETAR** branch de Jules se resultado nao for bom (explicar motivo)
- **DOCUMENTAR** o que Jules fez em MEMORY.md (cross-rein)

## Comparacao Jules vs ZCode (eu)

| Criterio | Jules (Gemini 3.1 Pro) | ZCode (MiniMax-M3) |
|---|---|---|
| Velocidade | Mais lento (sandbox) | Mais rapido (in-process) |
| Custo | Pago (Google) | Coding Plan (subscription) |
| Skills | 5 MCPs integrados | 50+ skills locais |
| Acesso a prod | Nenhum (sandbox) | Nenhum (sem MCPs) |
| Quando usar | UI/UX, refactor grande | Tudo (especialmente LGPD, backend) |
| Linguagens | Forte em React/Vue | Forte em Python/FastAPI |
| LGPD compliance | Confia no caller | LGPD-by-design |

## Tasks ideais para Jules

- **UI/UX**: telas novas, mockups, componentes React/Vue
- **Refactor grande**: migrar 100+ arquivos de padrao A para B
- **Documentacao**: gerar 50+ paginas de doc a partir do codigo
- **Testes E2E complexos**: Playwright/Cypress em multiplas paginas
- **Build errors em Render**: deixar Jules resolver deploy issues

## Tasks NAO ideais para Jules

- **LGPD-by-design code** (PII scrubber, audit log): precisa entender contexto
- **Backend critico** (rate limit, middleware): testar exaustivamente
- **Telegram bot, N8N workflow**: integracao especifica
- **Anything que precise contexto 1M** (esta sessoes longas)

## Auto-fix de build errors (Render MCP)

Jules + Render MCP = ciclo automatico:
1. Jules cria PR com feature
2. Render detecta codigo novo, dispara preview deploy
3. Build falha? Render envia erro pro Jules via MCP
4. Jules corrige, push, Render rebuilda
5. Loop ate build passar

Economiza tempo de Gustavo (senao teria que investigar build errors manualmente).

## Verificacao de uso (sessao 3+)

Jules API key foi disponibilizada em 2026-06-24. **NAO foi usada** ainda nesta sessao (ZCode esta fazendo todas as tasks). Gustavo pode spawnar Jules para tasks complexas (UI/UX) em paralelo.

## Limitacoes conhecidas

- Jules NAO tem acesso ao nosso `.env` (segredo, NUNCA dar)
- Jules NAO pode fazer deploy direto (precisa Render MCP)
- Jules NAO pode rotacionar chaves (NAO pedir)
- Jules NAO pode acessar prod sem sandbox

## Referencias

- Doc oficial: https://developers.google.com/jules/api
- Pricing: https://jules.google/pricing
- MCP servers: Linear, Stitch, Context7, v0, Render
- Render MCP: https://render.com/docs/coding-agents
- Comparacao AI agents: https://github.com/gustavofullstack/Cartorio/blob/master/.harness/AGENTS.md

Modified by ZCode/Mavis - 2026-06-24
