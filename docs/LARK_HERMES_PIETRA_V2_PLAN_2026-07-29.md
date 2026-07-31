# Lark · Hermes · Pietra v2 — plano de arquitetura e aceite

> **Data:** 2026-07-29  
> **Estado:** `PARCIAL` — contrato local validado; tenant, runtime e E2E ainda exigem revalidação.

## Decisão

Hermes nativo na VPS, conectado ao Lark por WebSocket, será o único consumidor do canal em
produção. Pietra é a única identidade pública. FastAPI permanece responsável por domínio,
MCP autenticado, PII, audit e HITL. O plugin Codex `lark-cartorio` é apenas uma ferramenta de
engenharia/auditoria; ele não é carregado pelo Hermes e não atende clientes.

Os caminhos `scripts/lark_bot_v6.py` e `backend/app/api/v1/lark.py` não podem coexistir como
consumidores ativos. Permanecem sem credenciais e sem subscription até remoção formal ou
definição explícita de fallback ativo-passivo.

## Baseline confirmado localmente

- O stack versionado usa `FEISHU_CONNECTION_MODE=websocket`.
- `FEISHU_ALLOW_ALL_USERS=false`, grupos em allowlist, menção obrigatória e bots bloqueados.
- Uma réplica, secrets externos e rollback estão declarados no Swarm.
- Streaming, reasoning, commentary, progresso e footers estão desabilitados no canal.
- `pietra-public-output` é o único plugin público declarado.
- O toolset Lark está limitado a `mcp-cartorio` e `cartorio_calcular_emolumento`.
- O plugin pessoal `lark-cartorio` possui skill, validador e MCP somente leitura, incluindo
  validação semântica estática da fronteira MCP pública.

Esses fatos provam `CONFIGURED` no código local. Não provam configuração carregada, inferência,
transporte, E2E ou certificação.

## Achados impeditivos

### P0

1. O router FastAPI Lark não está registrado em `backend/app/main.py`; seu contrato declarado
   diverge da rota composta.
2. O mesmo router aceita verificação quando `LARK_ENCRYPT_KEY` está ausente. Não pode ser
   publicado nesse estado.
3. O bot Flask legado expõe `/test-image`, grava upload bruto/OCR em disco e não satisfaz o
   contrato público LGPD.
4. MiniMax ainda depende de decisão DPO/DPA. Coding/Token Plan não é SLA de produção e não
   autoriza cobrança on-demand.
5. **[IMPLEMENTADO LOCALMENTE E REVISADO ESTATICAMENTE — NÃO DEPLOYED]** A fronteira MCP
   pública agora usa chave separada, instância pública com a única tool
   `cartorio_calcular_emolumento`, filtro de JSON-RPC, bloqueio de chamada direta fora da
   allowlist, framing HTTP fail-closed e scrub/no-echo. A evidência é somente local
   (código/testes/validador); não prova configuração carregada, deploy, transporte, E2E ou
   certificação.
6. O Flask legado usa nome de anexo sem contenção comprovada e pode permitir path traversal se
   voltar a ser ativado.

### P1

1. Faltam testes específicos do webhook/canal Lark e da não coexistência dos consumidores.
2. O router alternativo devolve identificadores de remetente/chat e registra `event_id`; essa
   superfície deve ser minimizada se for mantida.
3. Falta definir um relay interno de auditoria idempotente Hermes → FastAPI sem ampliar o
   toolset público.

## Modelo por tier

| Tier | Uso | Direção |
|---|---|---|
| T0 | Jurídico ou PII residual | Backend/MCP determinístico + HITL; sem LLM externo |
| T1 | FAQ, triagem e emolumentos | M2.7-highspeed primário; M2.7 fallback após DPA |
| T2 | Caso complexo já scrubbed | M3 somente com interface oficialmente suportada e corpus aprovado |
| T3 | Coding/backoffice sintético | M3 no Coding Plan, fora do SLA do canal público |

Nenhuma mudança de modelo, provider ou modalidade de cobrança é automática.

## Menor privilégio no Lark

Piloto:

- app internal/custom;
- visibilidade nominal;
- `im.message.receive_v1`;
- DM enviada ao bot;
- @menção ao bot em grupo permitido;
- envio como bot.

Vetados no piloto:

- leitura de todas as mensagens de grupo;
- `user_access_token`, `offline_access` ou personificação;
- Contacts amplo, Drive, Docs, Calendar, Mail ou Approval;
- anexos, download, OCR e retenção de conteúdo;
- criação/alteração de grupo ou membros;
- tool MCP de escrita ou efeito jurídico;
- publicação/geração automática de credencial.

Cada criação de app, scope, evento, visibilidade, publicação, credencial ou expansão de acesso
exige confirmação humana no momento da ação.

## Fases

### F0 — Freeze e inventário

- Provar consumidor único e ausência de Flask/FastAPI Lark ativos.
- Comparar configuração versionada e carregada sem imprimir envs ou payloads.
- Registrar versão, digest, pairing e rollback sanitizados.

### F1 — Tenant piloto

- Confirmar Lark global versus Feishu China.
- Auditar app atual, scopes, eventos, visibilidade e versão publicada.
- Criar ou ajustar somente após confirmação de Admin e revisão de menor privilégio.

### F2 — Canário Hermes

- Implantar config imutável com uma réplica e `failure_action: rollback`.
- Validar um processo, uma conexão WebSocket, MiniMax sintético e MCP autenticado.
- Provar grupo sem @ silencioso e usuário/grupo não pareado bloqueado.

### F3 — Audit e HITL

- Desenhar relay interno idempotente, fail-closed e sem payload bruto.
- Revisar retenção e PII com `cartorio-lgpd`.
- Garantir que qualquer efeito jurídico permaneça humano e que protocolos nasçam `DRAFT`.

### F4 — E2E autorizado

- Enviar mensagem sintética por pessoa autorizada.
- Correlacionar `Lark → Hermes → provider/tool → mesmo chat`.
- Testar duas mensagens seguidas, dedupe, isolamento, timeout/fallback e ausência de
  reasoning, progresso, nomes internos e PII.

### F5 — Consolidação

- Remover ou quarentenar Flask e router alternativo.
- Ensaiar rollback.
- Publicar evidências sanitizadas e somente então promover a `CERTIFIED`.

## Critério de aceite

O canal só pode ser chamado `CERTIFIED` quando houver, na mesma janela:

1. app/scopes/eventos/visibilidade confirmados no tenant;
2. um gateway e uma conexão WebSocket;
3. configuração fail-closed carregada;
4. provider e MCP testados com conteúdo sintético;
5. guard Pietra, PII e HITL aprovados;
6. audit chain íntegra;
7. round-trip real autorizado no mesmo chat;
8. teste de concorrência/dedupe/isolamento;
9. rollback ensaiado.

`1/1`, HTTP 200, WebSocket conectado, versão publicada ou inferência isolada não bastam.

## Rollback

Antes de mudança, capturar somente metadados sanitizados de serviço, revisão, configs, volume,
sessão e pairing. Usar configs imutáveis, `stop-first` e rollback do Swarm. Restaurar apenas a
configuração ou sessão afetada; nunca apagar volume/pairing em massa nem copiar secrets.

## Próxima ação segura

Quando o Arc estiver livre e houver confirmação para mudanças persistentes, abrir Lark Developer
e Lark Admin, auditar o app existente sem exibir credenciais e comparar tenant/scopes/eventos/
visibilidade com este contrato. Parar antes de criar app, ampliar scope ou publicar.
