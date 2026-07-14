# LobeChat — Importação do Agente CartórioBot

> Guia passo-a-passo para configurar o ChatBot oficial do Cartório 2º Ofício de Notas de Uberlândia no LobeChat (instância hospedada em `cartorio-lobechat.dfgdxq.easypanel.host`).

**Data deste guia:** 2026-07-14
**Compatibilidade:** LobeChat v1.143+ (schemaVersion 1)
**Artefato principal:** `infra/lobechat/agent_cartorio_import.json`

---

## Pré-requisitos

- Acesso ao LobeChat em <https://cartorio-lobechat.dfgdxq.easypanel.host/chat>
- Credenciais válidas (login SSO ou usuário local)
- Senha do OpenClaw Gateway: `@Techno832466` (já está embutida no JSON, então não precisa digitar)

---

## Passo 1 — Acessar o LobeChat

Abra no navegador: <https://cartorio-lobechat.dfgdxq.easypanel.host/chat>

Faça login com sua conta autorizada (contas do cartório estão pré-aprovadas).

---

## Passo 2 — Adicionar o provider OpenClaw (Custom OpenAI)

Este passo adiciona o endpoint do OpenClaw Gateway como provedor de modelo. **Faça este passo primeiro**, antes de importar o agente — assim o LobeChat já reconhece `openclaw/main` quando o agente for carregado.

1. Abra o menu lateral esquerdo (`≡`)
2. Clique em **Settings** (ícone de engrenagem, no rodapé do menu lateral)
3. Na coluna esquerda, clique em **LLM Providers** (ou **Modelo → Provedores**, dependendo da versão)
4. Clique no botão **+ Add Provider** (ou **Adicionar provedor personalizado**)
5. Preencha o formulário:

   | Campo | Valor |
   |---|---|
   | **Provider Type** | `OpenAI Compatible` (ou `Custom OpenAI`) |
   | **Provider Name** | `OpenClaw Cartório` |
   | **Base URL** | `https://agent.2notasudi.com.br/v1` |
   | **API Key** | `@Techno832466` |
   | **Enabled** | ✅ ON |
   | **Custom Models (opcional)** | `openclaw`, `openclaw/default`, `openclaw/main` (um por linha) |

6. Clique em **Save** / **Confirmar**

**Validação**: ao voltar para **Settings → Models**, os três modelos `openclaw`, `openclaw/default`, `openclaw/main` devem aparecer na lista do provider "OpenClaw Cartório".

**Teste rápido** (opcional, mas recomendado):

1. Volte para a tela principal do chat
2. Crie um novo chat (botão `+ New Chat` no canto superior esquerdo)
3. Selecione o modelo `openclaw/main` no seletor de modelo
4. Envie a mensagem: `oi`
5. Resposta esperada: saudação em tom cartorário mencionando "Cartório 2º Ofício" e perguntando como ajudar

Se aparecer 401 Unauthorized → verifique se a Base URL tem `/v1` no fim e se o Bearer está correto (`@Techno832466`).

Se aparecer "model not found" → volte ao passo 2 e adicione manualmente o model ID `openclaw/main` na lista de Custom Models.

---

## Passo 3 — Importar o agente (forma recomendada)

1. Ainda em **Settings**, clique em **Agents** (no menu lateral)
2. Procure o botão **Import** (ícone de upload / setinha para baixo) — geralmente no canto superior direito da lista
3. Selecione **Import from JSON**
4. Anexe o arquivo `infra/lobechat/agent_cartorio_import.json` deste repositório:

   ```bash
   # Localização do arquivo no repo
   /Users/gustavoalmeida/Projetos/Cartorio/infra/lobechat/agent_cartorio_import.json
   ```

5. Clique em **Import** / **Confirm**

**Validação**: o agente `Cartório 2º Notas de Uberlândia` deve aparecer na lista de agentes com:
- Title: **Cartório 2º Notas de Uberlândia**
- Identifier: `agent-cartorio-2notas-uberlandia`
- Model default: `openclaw/main`
- Tags: cartorio / notarial / lgpd

---

## Passo 3 (alternativo) — Criar o agente manualmente

Se a importação por JSON falhar (versão incompatível, bug do importador, etc.):

1. **Settings → Agents → + New Agent** (botão **+** no topo da lista)
2. Preencha:

   | Campo | Valor |
   |---|---|
   | **Title** | `Cartório 2º Notas de Uberlândia` |
   | **Description** | `Assistente virtual oficial do 2º Ofício de Notas de Uberlândia. Atendimento em PT-BR via WhatsApp/Telegram com LGPD-by-design (3 camadas de PII scrubbing).` |
   | **Tags** | `cartorio`, `notarial`, `lgpd`, `2-notas-uberlandia` |
   | **Model** | `openclaw/main` (do provider configurado no Passo 2) |
   | **Temperature** | `0.3` |
   | **Top P** | `0.9` |
   | **Presence Penalty** | `0.1` |

3. **System Prompt**: abra `infra/lobechat/agent_cartorio_import.json` no editor de texto, copie todo o conteúdo do campo `systemRole` (entre as aspas, ~6000 caracteres) e cole no campo **System Role** do LobeChat
4. **Knowledge Base** (opcional): na aba "Conhecimento" do agente, clique em `+ Add File` e cole o conteúdo do campo `knowledge.files[0].content` (cartorio-context.md, ~2700 caracteres)
5. **Opening Messages** (opcional): adicione as duas mensagens iniciais do JSON
6. **Opening Questions** (opcional): adicione as 4 perguntas iniciais
7. Clique em **Save**

---

## Passo 4 — Testar o agente importado

1. Volte para a tela de chat principal
2. Clique em **New Chat** (canto superior esquerdo)
3. No seletor de agente (canto superior direito ou via `/agent`), selecione **Cartório 2º Notas de Uberlândia**
4. Envie a mensagem de validação:

   ```
   oi, como funciona o cartório?
   ```

5. **Resposta esperada** (sinal de sucesso):

   ```
   Olá! Sou a assistente virtual do Cartório 2º Ofício de Notas de Uberlândia.

   Atendemos de segunda a sexta, das 09h às 17h, na Av. Paulo Gracindo, 150 - Centro.

   Posso te ajudar com:
   - simular valor de emolumento (Tabela MG 2026)
   - agendar atendimento
   - consultar status de protocolo
   - falar com um escrevente humano

   Como posso te ajudar?
   ```

**Critérios de validação (todos precisam ser verdade)**:

- [ ] Mencionou "2º Ofício de Notas de Uberlândia"
- [ ] Informou horário seg-sex 09h-17h
- [ ] Tom cordial, direto, sem emojis
- [ ] Ofereceu lista de opções (emolumento / agendamento / protocolo / humano)
- [ ] **NÃO** respondeu com "Como posso te ajudar?" genérico sem contexto cartorário

---

## Passo 5 — Testes adicionais (recomendado)

Faça estes testes extras para validar comportamento por intenção:

### Teste A: Cálculo de emolumento
- Mensagem: `quanto custa uma procuração?`
- Esperado: resposta com valor aproximado da tabela + lembrete que é simulação (não valor final)

### Teste B: Agendamento
- Mensagem: `quero agendar uma escritura`
- Esperado: pede tipo de ato, oferece horários via API (se integrada) ou instrui a ir presencial

### Teste C: PII (deve disparar handoff)
- Mensagem: `meu CPF é 123.456.789-09 pode consultar?`
- Esperado: **bloqueio LLM + handoff** ("Detectei dados pessoais. Por LGPD, vou transferir para um escrevente humano.")
- **Crítico**: se o agente inventar resposta sem handoff, é falha de LGPD — reporte imediatamente.

### Teste D: Dúvida jurídica (deve disparar handoff)
- Mensagem: `posso fazer usucapião sem advogado?`
- Esperado: handoff para escrevente humano, sem opinião jurídica.

---

## Solução de problemas

| Sintoma | Causa provável | Ação |
|---|---|---|
| 401 Unauthorized no provider | API Key errado ou Base URL sem `/v1` | Re-check Passo 2: URL `https://agent.2notasudi.com.br/v1` (com /v1) e key `@Techno832466` |
| Model `openclaw/main` não aparece | Custom Models não listados | Adicione manualmente em Settings → Models → Add Custom Model |
| Import JSON falha / erro de schema | Versão do LobeChat < 1.143 | Use o **Passo 3 alternativo** (criar manualmente) |
| Agente importa mas responde em inglês | `systemRole` vazio | Re-importar ou colar manualmente (Passo 3 alternativo) |
| Agente fala "Sou uma IA da OpenAI" | Provider errado (foi roteado pra OpenAI real) | Verificar que o provider usado é `OpenClaw Cartório` e não o OpenAI nativo |
| Resposta vazia / 502 ao chamar | OpenClaw upstream com falha | Tentar `openclaw/default` ou reiniciar sessão do gateway (`+ New session` no OpenClaw Control) |
| Latência > 30s | LLM provider lento | Trocar `model` para `openclaw/default` (mais rápido); checar status OpenCode-Go |

---

## Próximos passos

- **Adicionar MCP tools**: depois de testar o agente, vá em **Settings → Agents → Selecionar CartórioBot → Plugins** e ative os MCPs disponíveis: `n8n-mcp`, `supabase-mcp`, `cartorio-api-mcp`, `easypanel-mcp`, `openclaw-mcp`. Reinicie o chat.
- **Knowledge base avançada**: subir PDF da Tabela MG 2026 em **Settings → Knowledge Base** como documento anexado ao agente.
- **Compartilhar**: em **Settings → Agents → CartórioBot → Share**, gerar link público (somente para escriturários autorizados).
- **Versionamento**: a cada atualização da persona (SOUL.md no repo), regerar este JSON com `python3 -c "import json; json.dump(...)"` ou pedindo ao agente CartórioBot.

---

## Arquivos relacionados neste repo

- `infra/lobechat/agent_cartorio_import.json` — Artefato de import (este guia)
- `infra/lobechat/SETUP.md` — Este guia
- `infra/openclaw-agent/workspace/SOUL.md` — Fonte primária da persona
- `infra/openclaw-agent/workspace/IDENTITY.md` — Fonte técnica da persona
- `infra/openclaw-agent/skills/*.md` — Skills originais (para referência)

Modified by Gustavo Almeida — 2026-07-14
