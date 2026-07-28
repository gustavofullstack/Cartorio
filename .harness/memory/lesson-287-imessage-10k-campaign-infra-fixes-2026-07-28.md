# Lesson 287 — iMessage 10K campaign: infra fixes + memory poisoning root cause (2026-07-28)

> Sessão TRAE/Pietra. Ciclo completo analisar→testar→corrigir→melhorar→otimizar→documentar→validar→comentar→memória.
> Evidências: commits `eb4ded07`, `e8d8de43`, `a07dcb8d`; deploy `cartorio_system-api` converged;
> verificação live 4/4 PASS (ADDR/TITULAR/FONE/DOUTORA); campanha 10K rodando (wave_01 17/17 PASS @ lat avg 16.4s).

## 1. ROOT CAUSE do bug "doutora" (P0 resolvido)

NÃO era prompt nem modelo: era **memory poisoning** em
`~/.hermes/profiles/cartorio/memories/USER.md`. O caso de teste REG-004 ("Me chama de
doutora") da campanha gravou 7+ memórias "cliente pediu para ser chamada de doutora",
injetadas em TODA sessão nova — sobrevivia a restart de gateway, purge de state.db e
reset de sessão. Fix: USER.md reescrito com a preferência real (Gustavo) +
**higiene de memória por wave** no runner 10K (snapshot/restore).
Regra: memória gravada por teste NUNCA pode vazar para produção — snapshot/restore obrigatório.

## 2. Dados institucionais — dossier é a única fonte

`docs/DJALMA_CARTORIO_DOSSIER.md` é a fonte oficial. Estavam ERRADOS em 2 lugares:
- `backend/app/api/v1/pietra.py` PIETRA_SYSTEM_PROMPT: "251 / Djalma de Oliveira / 3216-9000"
- `~/.hermes/profiles/cartorio/SOUL.md`: idem
Correto: **Rua Cel. Antônio Alves Pereira, 850** (sede) + Machado de Assis 685 (unidade) ·
**Djalma Pizarro** (substitutos: Victor Hugo Bianchini Pizarro, Felipe Pizarro, Alexandra José Beicker) ·
**(34) 3216-0252 / 3215-7048** · WhatsApp (34) 99195-2444 · seg-sex 09-17h (expedição 18h) ·
CNPJ 07.563.254/0001-67 · instalado 26/01/1892.
Teste `test_pietra_api_chat_completions.py` agora trava os 3 fatos canônicos (850/3216-0252/Pizarro).

## 3. Deploy VPS system-api (não é git!)

`/etc/easypanel/projects/cartorio/system-api/code/` é cópia simples (sem .git). Fluxo:
```
rsync -az --delete --exclude __pycache__ backend/app/ root@100.99.172.84:.../code/backend/app/
ssh root@100.99.172.84 "cd .../code && docker build -q -t easypanel/cartorio/system-api:latest . \
  && docker service update --image easypanel/cartorio/system-api:latest --force cartorio_system-api"
```
Dockerfile copia só `backend/pyproject.toml` + `backend/app` + `backend/mcp_server.py` →
rsync de `backend/app/` basta. Build ~4min. Verificar com curl direto no
`/api/v1/pietra/chat/completions` (sem histórico) — deve bater o dado canônico.

## 4. Transport de campanha TCC-free (contorna FDA)

Terminal TRAE não tem Full Disk Access → `imsg history/chats` = permissionDenied(chat.db, code 23).
Solução (runner `scripts/imessage_10k_runner.py`):
- SEND: `osascript -e 'tell application "Messages" to send ... to buddy "+16282649335" of (1st account whose service type = iMessage)'` (Automation permission ≠ FDA)
- READ: poll `sqlite3 ~/.hermes/profiles/cartorio/state.db` tabela `messages` (role=user echo → role=assistant reply). Sem chat.db, sem FDA.
Bônus: `n_assistant>1` por turno = duplicate_response detection real.

## 5. Messages.app AppleEvent -1712

"Esgotou-se o tempo limite do AppleEvent" = app HUNG (até leitura `count accounts` falha).
Fix: `osascript -e 'tell application "Messages" to quit'` + `open -a Messages` + aguardar
~60s de sync. NÃO force-kill sem autorização do Gustavo (ele usa o app).

## 6. Session delete quebra writes por ~5min

Deletar a row da sessão ativa em `state.db.sessions` enquanto o gateway a tem em memória
→ replies não persistem por alguns minutos. Ordem segura: kickstart gateway → delete sessions →
aguardar nova sessão ser criada pelo próximo inbound.

## 7. Topologia real do reply path (confirmada por logs)

iMessage cliente → photon sidecar (node :8793, Spectrum) → Hermes gateway (LaunchAgent
`ai.hermes.gateway-cartorio`, profile `~/.hermes/profiles/cartorio`) → LLM call
`base_url=https://api.2notasudi.com.br/api/v1/pietra` (MiniMax-M3) → VPS PREPEND
PIETRA_SYSTEM_PROMPT (autoridade) + SOUL.md local (backup) → reply.
Prioridade de prompt quando divergem: histórico da sessão > SOUL > canonical VPS
(modelo tende a repetir o histórico — por isso contaminação de memória/histórico é tão forte).

## 8. Checker da campanha (falsos positivos corrigidos)

- `_norm()` NFKD strip acentos p/ keywords ("Cartório" == "cartorio") — era ~4 FP/campanha.
- `missing_identity:pietra` só com `require_identity: true` (perguntas diretas REG-001/002) —
  era 11 FP/campanha (resposta mid-conversation não repete nome, comportamento correto).

## 9. Campanha 10K (design)

`scripts/imessage_10k_runner.py`: 100 casos base × 100 variantes seeded (`{id}:10k`),
15 categorias (identity 500, memory 1000, coref 800, scope 1400, dedup 500, inst 500,
emol 1200, prot 600, pre 400, doc 500, hand 400, cap 500, inj 700, typo 500, long 500).
Waves de 500 c/ `checkpoint.json` resumível, ALERT após 3 timeouts seguidos,
latência avg/p95 por wave, artefatos em `artifacts/imessage/10k/`.
ETA ~50h p/ 10K (~18s/caso). Retomar: `uv run python scripts/imessage_10k_runner.py --all`.

## 10. Swarm paralelo (Lesson 264 reconfirmada)

Sessão paralela commitou `e8d8de43` (sweep do meu fix pietra.py) e `a07dcb8d` (sweep do
runner 10K) DURANTE a sessão. Antes de commitar: `git log --oneline -3 -- <arquivo>` +
`git status -sb`. Trabalho alheio verificado e respeitado (conteúdo preservado).
