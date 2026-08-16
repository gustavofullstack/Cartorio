# Prompt Cartório

**Objetivo:** Integrar e testar tudo! API, Chatwoot, Chatwoot-Sidekiq, Evolution-API, N8N, N8N-Runner, OpenClaw-Gateway, Redis e Supabase. O bot do Telegram deve estar funcionando para testes.

**Diretrizes Principais:**
1. **NUNCA rotacionar chaves:** Somente Gustavo e eu (Jules) temos acesso. Nunca mais falar sobre rotacionar chaves.
2. **Economia de Tokens:** Gaste a menor quantidade de tokens possível via endpoint Coding Plan e entregue o melhor resultado.
3. **Sem Erros:** Não deixar warnings, erros, etc., nem em dev nem em prod.
4. **Melhorias, não Refatoração:** Melhorar o que temos, nada de refazer do zero. Criar um super plano de 100 tarefas de melhoria.
5. **Orquestração Consciente:** Usar agents de 1 ou 2 no máximo por vez. Fazer as tasks aos poucos.
6. **Centrais do Sistema:** A API e o N8N são os hubs centrais. Ambos devem estar centralizados e integrados. Testar tudo.
7. **Banco de Dados Central:** Supabase. Utilizar completamente (API, MCP, Cron, Webhooks, GraphQL, Queues, Vault).
8. **Agent AI Cartório:** Destinado ao WhatsApp via Evolution-API. Conectar somente após 100% pronto. Configuração principal fica no OpenClaw Agent. Respostas diretas, curtas, sérias, sem emojis.
9. **Chatwoot:** CRM para integrar WhatsApp e Agent AI (possibilidade de pausar bot no Chatwoot). Explorar suas ferramentas.
10. **Redis:** Memória rápida.
11. **Fluxo Principal:** `EVOLUTION-API -> API -> N8N -> CHATWOOT -> REDIS -> SUPABASE -> REDIS -> CHATWOOT -> N8N -> API -> EVOLUTION-API`
12. **Documentação:** Baixar/ler documentação de tudo (Evolution, N8N, Chatwoot, Supabase, Redis) e continuar a da API.
13. **Memória e Cérebro:** Construir memória local/produção para vias rápidas de análise e testes. Organizar o repositório (`.jules`, `.brain`).
14. **Monitoramento de Tokens:** Usar `codex-bar.app` ou `codex-bar CLI`.
15. **OpenClaw Agent Config:** Modelo `deepseek-v4-flash`, pensar (`thinking: true`), contexto 1M. **(Feito)**
16. **Múltiplos Modelos:** Usar Mavis/Pietra, OpenCode Zen, Qwen Coder, etc., para tarefas simples (documentar, etc.), economizando o Coding Plan.
17. **EasyPanel/VPS:** Central de deploy e VPS disponíveis via SSH/Tailscale e API.
18. **Planos Duplos:** Criar os planos grandes (`SUPER_PLANO`) em `.md` e `.json` (compacto) para poupar tokens.
