# Inventário seguro de possíveis segredos rastreados — 2026-07-19

Status: **P0 aberto — saneamento e rotação dependem de operador autorizado.**

Este inventário foi gerado localmente a partir de `git ls-files` e dos padrões do
`backend/scripts/check_no_literal_keys.py`. A execução registrou somente caminho,
regra e severidade; nenhum valor, trecho de linha, hash de segredo ou credencial é
incluído neste documento. Um achado é um indício a validar em canal seguro, não uma
prova de que a credencial ainda esteja válida.

## Resultado

- 48 arquivos rastreados tiveram ao menos um achado não coberto pelo baseline.
- 38 têm ao menos um achado de severidade `critical`.
- O scanner local de chaves literais é agora um gate rígido no CI: uma falha encerra
  o job antes de lint e testes. Gitleaks permanece como scanner complementar.
- A saída do scanner identifica caminho, linha e regra, mas redige o valor encontrado
  para não copiar credenciais para logs de CI ou do terminal.

## Arquivos a tratar por canal seguro

| Grupo | Arquivos rastreados com indício | Próxima ação autorizada |
| --- | --- | --- |
| Configuração e memória operacional | `.agents/skills/coding-vps-21/SKILL.md`, `.agents/skills/coding-vps-21/easypanel-audit-2026-07-09-squad4.md`, `.agents/skills/minimax-m3/SKILL.md`, `.brain/memory/2026-06-26.md`, `.brain/memory/2026-07-01.md`, `.brain/memory/2026-07-13-easypanel-lobechat-telegram.md`, `.harness/mcps/coding-vps-orchestrator/server.py`, `.harness/memory/archive-2026-06-24-early-sprint4.md`, `.harness/memory/telegram-squad.md`, `.harness/reins/cartorio-dev/env-consolidated-2026-06-24.env`, `.harness/reins/cartorio-dev/memory/archive/2026-06-29/linear-sync-2026-06-24.md`, `.zcode/skills/chatwoot.md` | Revogar/rotacionar no provedor, substituir por referência de ambiente/cofre e remover conteúdo ativo. |
| Prompts e resumos de sessão | `PROMPT.MD`, `PROMPT.json`, `PROMPT.json.bak.20260702_180541`, `SESSION_SUMMARY_2026-06-25-noite.md`, `SESSION_SUMMARY_2026-06-25-tarde.md`, `SESSION_SUMMARY_2026-06-26-manha.md`, `SESSION_SUMMARY_2026-06-26-tarde2.md`, `SESSION_SUMMARY_2026-06-26.md`, `SESSION_SUMMARY_2026-06-30-1546.md` | Preservar apenas marcadores redigidos; avaliar remoção de backups rastreados após rotação. |
| Infraestrutura e automação | `infra/cron/cartorio-health-check`, `infra/openclaw-agent/RELOAD_PERSONA.md`, `infra/openclaw-agent/gateway-config-snapshot-t49.json`, `infra/openclaw-agent/gateway-config-snapshot-t49.json.bak-pre-fix3-20260624-181820`, `infra/openclaw-agent/workspace/TELEGRAM.md`, `infra/scripts/check_telegram.sh`, `scripts/cartorio-env.sh`, `scripts/cloudflare_tunnel_fallback.sh`, `scripts/coding_vps_mcp_orchestrator.py`, `scripts/deploy_coding_vps_21.sh`, `scripts/diagnose_vps_and_bot.sh`, `scripts/fix_openclaw_context_1M.sh` | Rotacionar primeiro; substituir por variáveis injetadas/secret manager; validar que logs não imprimem ambiente. |
| Documentação e espelhos de fornecedor | `docs/E07_OPENCLAW_CONTEXT_FIX.md`, `docs/GUIA_VALIDACAO_TELEGRAM_1000_PONTOS.md`, `docs/INTEGRATION_GUIDE.md`, `docs/MONITORING_GUIDE.md`, `docs/SECRETS_SCANNER_COMPOSE_G8.md`, `docs/n8n/index.html`, `docs/platforms/n8n-docs/n8n-api.html`, `docs/platforms/n8n-docs/n8n-hosting.html`, `docs/platforms/n8n-docs/n8n-index.html`, `docs/platforms/n8n-docs/n8n-workflows.html`, `docs/platforms/n8n/index.html`, `docs/supabase/llms-full.txt` | Confirmar se exemplos são sintéticos; substituir qualquer valor por placeholder inequívoco e evitar espelhos com conteúdo sensível. |
| Código de scanner e testes | `backend/scripts/check_no_literal_keys.py`, `backend/tests/test_check_no_literal_keys_g8.py`, `backend/tests/test_lobechat_prompt_export_g8.py` | Revisar como possíveis falsos positivos de padrões e fixtures; manter somente dados sintéticos que não atendam ao formato de credenciais reais. |

## Procedimento obrigatório antes de saneamento

1. Abrir incidente de segurança e rotacionar/revogar cada credencial potencialmente real no provedor, fora de Git e fora de chat.
2. Validar o novo segredo com smoke autenticado que não imprima resposta sensível.
3. Redigir/remover valores dos arquivos ativos e backups rastreados; não usar o baseline para aceitar segredo real.
4. Executar `make secrets-scan-strict` e o job `secrets-scan` do CI, mantendo ambos bloqueantes.
5. Avaliar reescrita de histórico somente sob procedimento aprovado de resposta a incidente; esta tarefa não a executa.

## Limites desta evidência

O scanner não substitui validação manual nem varredura do histórico. O resultado é
intencionalmente redigido para não ampliar a exposição. A lista deve ser atualizada
após a rotação e o saneamento por responsável autorizado.
