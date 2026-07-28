# FELIPE_INCIDENT_2026-07-28 — Atendimento iMessage do Cartório ao interlocutor Felipe P.

**Status**: CLOSED — forense concluída, recomendações pendentes de implementação
**Severity**: P1 (dano reputacional, vazamento de lixo técnico, risco de dados pessoais e quebra de canal institucional)
**Detected**: 2026-07-28 18:30 BRT (durante revisão forense do iMessage)
**Reporter**: Subagente Frente C
**Scope**: Canal iMessage / Messages.app do Mac local (não é backend VPS)

---

## TL;DR

Durante a certificação do atendimento iMessage do 2º Tabelionato de Notas de Uberlândia, o interlocutor **Felipe P.** enviou mensagens para o canal do cartório e recebeu:

1. Resposta de número/canal errado (operador pediu que aguardasse outro número);
2. Atraso de ~13 minutos entre a primeira pergunta e uma resposta institucional válida;
3. Mensagens do bot corrompidas por encoding (`��\x00`, `��\x04`, `�\x1f\x02`) no início do texto;
4. Vazamento de linguagem promocional não-notarial ("versão super evoluída") e de metadados técnicos em outro chat de configuração;
5. Oferta indevida de atendimento privado "sem burocracia" por um agente de IA de operação.

Não houve exposição de CPF, RG ou números de certidão do Felipe P. nos registros encontrados.

---

## Fontes de evidência

| Fonte | Tipo | Período | Notas |
|-------|------|---------|-------|
| `~/Library/Messages/chat.db` (Mac local) | Banco SQLite nativo, acesso somente-leitura | 2026-07-25 a 2026-07-28 | Exportado via `imsg history --chat-id <id> --limit 10000 --json` |
| `artifacts/imessage/frente_c_forensic/chat365_+55_34_9****-7228_history.jsonl` | Export bruto | 2026-07-28 | Canal do interlocutor Felipe P. (Brasil) |
| `artifacts/imessage/frente_c_forensic/chat359_+1_628_***-3877_history.jsonl` | Export bruto | 2026-07-25 a 2026-07-28 | Canal do agente de IA de operação (EUA) |
| `artifacts/imessage/frente_c_forensic/chat364_+1_628_***-9335_history.jsonl` | Export bruto | 2026-07-26 a 2026-07-28 | Canal de testes/QA do cartório |
| `artifacts/imessage/history_analysis_20260728.md` | Análise prévia | 2026-07-28 | Diagnóstico do chat 364 (2.044 msgs, 929 de sistema/erro) |
| `artifacts/imessage/ANALISE_PERSONAS_2026-07-28.md` | Análise prévia | 2026-07-28 | Campanha de 10 personas, validação do guard anti-lixo |

> Os exports brutos ficam em `artifacts/imessage/frente_c_forensic/` com permissões padrão do usuário. Não foram commitados. Recomenda-se mover para storage criptografado ou destruir após retenção definida pela política LGPD do cartório.

---

## Personagens e canais

- **Felipe P.** — interlocutor/cliente, número Brasil: `+55 34 9****-7228` (mascarado).
- **Canal institucional do cartório** — número destino dos envios: `+55 34 9****-0250` (mascarado).
- **Agente de IA de operação (Codex/Grok)** — número EUA: `+1 628 ***-3877` (mascarado). Usado por Gustavo para configurar/monitorar a infraestrutura Hermes/Photon.
- **Canal de testes/QA** — número EUA: `+1 628 ***-9335` (mascarado). Canal usado para bateria de testes T0–T5 do bot.

---

## Timeline das falhas

### 2026-07-27 ~01:27 BRT — Oferta indevida de atendimento privado

**Canal:** chat 364 (testes/QA).  
**Falha:** O agente de IA de operação respondeu a uma pergunta sobre encaminhar o Felipe P. para um canal específico com:

> "Pode sim! O atendimento por esse canal é aberto — é só o Felipe chamar aqui que eu atendo na hora, sem burocracia. Se preferir, ele também pode ligar no (34) 3216-0252, de segunda a sexta, das 9h às 17h. Qualquer coisa que ele precisar — certidão, reconhecimento de firma, emolumentos — eu resolvo por aqui."

**Classificação:** ALTO — confusão entre canal de testes/QA e canal de atendimento ao público; promessa de resolução sem burocracia, fora do fluxo de protocolo DRAFT obrigatório.

---

### 2026-07-28 17:57 BRT — Mensagem promocional e auto-referencial

**Canal:** chat 365 (Felipe P.).  
**Mensagem do bot (is_from_me=true):**

> "Olá, Felipe! Peço sinceras desculpas pelos mal-entendidos e atrasos anteriores no atendimento. Atualizamos e ativamos a Pietra na versão super evoluída: agora com atendimento 100% resolutivo, triagem e coleta completa de dados, documentos e agendamentos, sem fallbacks em chinês e com as informações institucionais 100% corrigidas (atendimento exclusivo na Sede: Rua Cel. Antônio Alves Pereira, 850). Estou inteiramente à disposição para te atender e realizar todos os testes necessários. Em que posso te ajudar hoje?"

**Problemas observados:**
- Início corrompido por encoding: `�\x1f\x02`.
- Linguagem promocional inadequada para instituição notarial ("super evoluída", "100% resolutivo", "100% corrigidas").
- Menção explícita a "fallbacks em chinês" — revela defeito anterior do sistema ao cliente.
- Oferta de "realizar todos os testes necessários" — trata o cliente como beta-tester.

**Classificação:** MÉDIO — tom institucional quebrado + leak indireto de defeitos anteriores.

---

### 2026-07-28 18:06:13 BRT — Primeira mensagem do Felipe P.

**Canal:** chat 365.  
**Mensagem:** "Oi"  
**Classificação:** Entrada normal do cliente.

---

### 2026-07-28 18:06:23 BRT — Pergunta do Felipe P. sem resposta imediata

**Canal:** chat 365.  
**Mensagem:** "Qual o preço da procuração?"  
**Classificação:** Pergunta notarial legítima.

---

### 2026-07-28 18:06:58 BRT — Resposta do operador indicando canal errado

**Canal:** chat 365.  
**Mensagem do operador Gustavo (is_from_me=true):** "Perdão Felipe ela vai lhe responder pelo numero que lhe enviei"

**Problema:** O cliente foi atendido em um canal, mas o operador informou que a resposta viria por outro número. Isso indica roteamento confuso ou duplicidade de canais ativos simultaneamente.

**Classificação:** ALTO — handoff mal executado, cliente deixado sem resposta no canal original.

---

### 2026-07-28 18:19:25 BRT — Resposta do bot admitindo falha técnica

**Canal:** chat 365.  
**Mensagem do bot:**

> "Olá, Felipe. Sou a Pietra, a agente virtual do 2º Cartório de Notas de Uberlândia. Peço desculpas pela demora nas respostas anteriores — houve um problema técnico na configuração do nosso atendimento automatizado que deixou suas mensagens sem retorno. Já foi corrigido. Sobre a procuração: Procuração genérica (sem conteúdo financeiro): R$ 68,94; Procuração com conteúdo financeiro: R$ 218,41."

**Problemas observados:**
- Início corrompido por encoding: `��\x01`.
- Vazamento de problema técnico interno ao cliente ("problema técnico na configuração").
- Resposta dá valores parciais, sem explicar Recompe/TFJ/ISS, nem o valor final.
- Não aciona HITL/escrevente para coleta de dados sensíveis (CPF, outorgado etc.).

**Classificação:** ALTO — mensagem de erro técnico vazada + resposta incompleta.

---

### 2026-07-28 18:25:34 BRT — Follow-up do cliente

**Canal:** chat 365.  
**Mensagem:** "Esse é o valor final ?"  
**Classificação:** Pergunta de esclarecimento legítima.

---

### 2026-07-28 18:29:51 BRT — Resposta detalhada do bot

**Canal:** chat 365.  
**Mensagem do bot:**

> Forneceu valores finais detalhados (R$ 93,76 e R$ 296,84), explicou composição de Recompe + TFJ + ISS e ofereceu iniciar pré-protocolo.

**Problemas observados:**
- Início corrompido por encoding: `��\x04`.
- Apesar da resposta correta em conteúdo, o bot solicita CPF e dados do outorgado diretamente no iMessage sem informar canal seguro ou acionar escrevente.

**Classificação:** MÉDIO — conteúdo técnico correto, mas coleta de PII planejada em canal de chat sem HITL explícito.

---

## Resumo das falhas classificadas

| # | Falha | Severidade | Evidência | Quantidade |
|---|-------|------------|-----------|------------|
| 1 | Mensagens de sistema/erro vazadas ao cliente | ALTO | "problema técnico na configuração", "fallbacks em chinês", preflight em chat 364 | 2 diretas + múltiplas em chat 359/364 |
| 2 | Resposta enviada pelo canal/número errado | ALTO | Operador: "ela vai lhe responder pelo numero que lhe enviei" | 1 |
| 3 | Mensagens do Felipe P. sem resposta imediata | ALTO | 18:06:13 a 18:19:25 (~13 minutos de silêncio) | 2 mensagens sem resposta no canal correto |
| 4 | Corrupção de encoding no início das mensagens do bot | MÉDIO | `��\x00`, `��\x01`, `��\x04`, `�\x1f\x02` | 3 mensagens no chat 365 |
| 5 | Linguagem promocional/não-notarial | MÉDIO | "versão super evoluída", "100% resolutivo", "realizar todos os testes necessários" | 1 |
| 6 | Oferta indevida de atendimento privado "sem burocracia" | ALTO | Chat 364, mensagem de 2026-07-27 01:27 | 1 |
| 7 | Coleta de PII planejada sem HITL explícito | MÉDIO | Bot solicita CPF/nome/outorgado no iMessage | 1 |
| 8 | Handoffs/deflexões | BAIXO | Não houve "ligue", "vá ao cartório" ou "mande email" no chat 365; o bot manteve o diálogo | 0 |
| 9 | Mensagens em chinês ou idioma estrangeiro | BAIXO | Nenhuma mensagem em chinês no chat 365; apenas referência do bot a "fallbacks em chinês" | 0 |
| 10 | Informações falsas sobre endereço/unidade complementar/Victor Hugo | BAIXO | Nenhuma informação incorreta identificada sobre endereço ou pessoas no chat 365 | 0 |

---

## Causa raiz identificada

1. **Roteamento iMessage instável:** o mesmo interlocutor (Felipe P.) estava exposto a múltiplos números/canais (Brasil, EUA teste, EUA operação) sem um ponto de entrada único e documentado. O operador teve que corrigir o canal em tempo real.
2. **Outbound guard insuficiente no bridge iMessage:** mensagens de sistema ("problema técnico", "fallbacks em chinês") e bytes de encoding corrompido (`\x00`, `\x04`) não foram filtrados antes do envio. O guard anti-lixo implementado no dia 28/07 corrigiu parte do problema (não há mais "Interrupting current task" no chat 365), mas não pegou encoding e metalinguagem.
3. **System prompt com tom promocional:** a mensagem inicial usou superlativos inadequados para uma serventia notarial, sugerindo que o prompt ou uma resposta manual foi escrita em tom de marketing.
4. **Confusão de papéis no chat 364:** o agente de IA de operação misturou conversa técnica de infraestrutura com oferta de atendimento notarial ao público, desrespeitando a regra de que toda ação jurídica nasce como DRAFT e passa por escrevente.

---

## Correções aplicadas / recomendadas

### Já aplicadas (durante a própria janela do incidente)

- Deploy do novo prompt resolutivo formal-carinhoso + outbound guard anti-lixo/anti-CJK no dia 2026-07-28, conforme documentado em `artifacts/imessage/ANALISE_PERSONAS_2026-07-28.md`. O chat 365 já usa essa versão, mas ainda exibe resíduos dos problemas anteriores.
- O operador interveio manualmente às 18:06:58 BRT para informar ao Felipe P. que a resposta viria pelo canal correto.

### Recomendadas

1. **(P0) Filtrar encoding corrompido no outbound:** rejeitar mensagens que comecem com bytes de controle (`\x00`–`\x1f`) ou U+FFFD antes do envio pelo iMessage. Implementar no sanitizer `backend/app/api/v1/pietra.py::_sanitize_pietra_output` e no bridge Photon/Hermes.
2. **(P0) Proibir metalinguagem técnica no system prompt:** remover do prompt qualquer menção a "fallbacks em chinês", "problema técnico", "versão", "testes" etc. O bot deve falar como serventia notarial, não como release note.
3. **(P1) Canal único de entrada para clientes:** documentar e comunicar um único número/entrada iMessage oficial para o cartório. Números de teste/QA e de operação não devem ser compartilhados com clientes.
4. **(P1) Revisar o papel do agente de operação (Codex/Grok):** o agente de IA usado para configuração de infraestrutura não deve responder perguntas de atendimento ao cliente nem oferecer resolução notarial. Isolar por persona/system prompt.
5. **(P1) Gate de HITL antes de coletar PII:** quando o bot precisar de CPF/nome/outorgado, deve informar que o escrevente validará os dados e marcar o protocolo como DRAFT, em vez de prosseguir como se o chat fosse o formulário final.
6. **(P2) Cobertura de teste para handoffs:** adicionar cenário de handoff de canal na bateria de personas, garantindo que o cliente nunca fique sem resposta no canal original.

---

## Lições aprendidas

- **L282a:** Números de teste/QA e de operação não podem ser expostos a clientes reais; a fronteira entre "canal institucional" e "canal de engenharia" precisa ser explícita e auditada.
- **L282b:** Mensagens de sistema, metalinguagem técnica e bytes de encoding corrompido devem ser filtrados no bridge iMessage antes do envio; o guard anti-lixo deve cobrir não só CJK/inglês, mas também metalinguagem e caracteres de controle.
- **L282c:** Superlativos e linguagem promocional ("super evoluída", "100% resolutivo") destroem a credibilidade notarial. O tom padrão deve ser formal, carinhoso e sem promessas absolutas.
- **L282d:** Todo atendimento que envolva coleta de PII ou produção de ato notarial deve acionar HITL e nascer como DRAFT, mesmo em canais informais como iMessage.

---

## Armazenamento e retenção dos exports brutos

- Local: `artifacts/imessage/frente_c_forensic/`
- Arquivos:
  - `chat365_+55_34_9****-7228_felipe_history.jsonl`
  - `chat359_+1_628_***-3877_usa_history.jsonl`
  - `chat364_+1_628_***-9335_history.jsonl`
- **Não foram commitados.** Recomenda-se:
  1. Mover para volume criptografado fora do repo, OU
  2. Aplicar retenção LGPD (ex.: 180 dias) e destruir após prazo, OU
  3. Anonimizar (hash de handles + remoção de texto) antes de qualquer commit para fins de análise estatística.

---

**Modified by Gustavo Almeida**
