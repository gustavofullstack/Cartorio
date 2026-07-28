# Análise do histórico iMessage — Bot do Cartório (chat_id 364)

Data da análise: 2026-07-28
Fonte: `history_full_20260728.jsonl` (extraído com `imsg history --chat-id 364 --limit 10000 --json`)

## 1. Visão geral

- **Total de mensagens:** 2.044
  - Do bot (`is_from_me=false`): **1.242** (313 conversacionais reais + **929 mensagens de sistema/erro vazadas ao cliente**)
  - Dos usuários (`is_from_me=true`): **802**
- **Período coberto:** 2026-07-26 18:33 UTC → 2026-07-28 14:07 UTC (~44 horas)
  - 2026-07-26: 80 msgs | 2026-07-27: 1.179 msgs (727 erros!) | 2026-07-28: 785 msgs
- **Remetentes:** o chat tem um único handle (`+16282649335` ↔ `+5534992800250`); não é possível distinguir remetentes distintos pelo campo `sender`. Pelo conteúdo, há pelo menos 3 personas: **Gustavo** (operador/testador), uma **"doutora"** (persona de advogada testando), e **Maria José** (persona de idosa, 72 anos). O tráfego é majoritariamente de testes/QA do bot, não de clientes reais.

## 2. Padrões de comportamento do BOT

### Tom
- **Híbrido e instável:** oscila entre formal-robótico ("Doutora, por segurança e privacidade (LGPD)...") e informal-carinhoso ("Fazemos procuração sim!", "Boa pergunta!"). Não há registro fixo.
- Tratamento: **"doutora/doutor" 83x cada** (usado de forma mecânica, quase toda mensagem na sessão da persona advogada); "você" 39x; **zero** "senhor/senhora"; zero construções formais como "ajudá-lo".
- Saudações com nome: "Boa noite, Gustavo" (11x), "Boa noite, Pietra!" — inclusive chamando a si mesma pelo nome errado.

### Repetições mecânicas
- Top 6 mensagens idênticas do bot são **todas mensagens de erro de infra em inglês**:
  - 388x `⏱️ The model provider is rate-limiting requests. Please wait a moment and try again.`
  - 203x `❌ Provider returned an empty response stream after 3 attempts...`
  - 100x `Sorry, I encountered an unexpected error. Try again or use /reset...`
  - 76x `⚠️ The model provider failed after retries...`
  - 47x `⚡ Interrupting current task. I'll respond to your message shortly.`
  - 39x `API call failed after 3 retries: Provider returned an empty stream...`
- Frases recorrentes (mensagens reais): "Posso te ajudar" (32x), "Em que posso te ajudar" (16x), "posso ajudar" (21x), "2º Cartório de Notas" (116x), "Claro" (11x).
- Resposta de reconhecimento de firma repetida **quase verbatim 8x** (ids 2068, 2077, 2080, 2083, 2091, 2093, 2095, 2100) — efeito "disco riscado".
- A resposta evasiva "troca de agente... LGPD... não tenho acesso ao histórico" repetida **8x** na mesma sessão (ids 3667–3734).

### Emoji
- 772 de 1.242 mensagens do bot contêm emoji — mas a maioria esmagadora são os ícones das mensagens de erro (⏱️❌⚠️⚡). Nas mensagens conversacionais o uso é moderado.

### Tamanho das respostas
- Bot: média **152 caracteres**, mediana 91, máximo 6.110. Usuário: média 42, mediana 24. Respostas curtas — adequado para WhatsApp/iMessage quando não é erro.

## 3. Problemas observados (com evidência)

### 3.1 CRÍTICO — Erros de infra vazados ao cliente (929 msgs, 75% do volume do bot)
- id 2032/2050/3312: `📬 No home channel is set for Photon. A home channel is where Hermes delivers cron job results...` (14x)
- id 2033/2045: `↪ Redirected current run (iteration 1/150). I'll adjust using your correction.`
- id 2039: `⚡ Interrupting current task. I'll respond to your message shortly.` (49x)
- id 3357/3379/3393: `⚠️ Gateway shutting down — Your current task will be interrupted.`
- id 2156: `HTTP 403: You've reached your usage limit for this billing cycle. Your quota will be refreshed...` — **leak de quota/billing ao cliente**.

### 3.2 CRÍTICO — Leak de modelo/infra
- id 3293/3296/3315/3318: `🔄 Switched to fallback model: MiniMax-M3 via minimax → deepseek-v4-flash-free via opencode-zen` — nome de modelo, provider e rota de fallback expostos no chat.
- id 2041: mensagem de "Preflight" com hash de git (`HEAD | 383e4597`) e status de runtime enviada no canal do cliente.
- id 2051/2080/2083: bot sugere ao cliente `Digite /help para ver comandos disponíveis` — expõe comandos de admin no atendimento.
- id 3363: `Registrado na memória permanente — gateway crash + erros visíveis ao cliente + fallback MiniMax-M3 → opencode-zen` — nota interna de engenharia vazada como mensagem.

### 3.3 ALTO — Crise de identidade do bot
- **88x "Sou a Pietra"** vs **16x "Sou o Hermes"** — dois nomes/gêneros diferentes no mesmo chat.
- id 3659: `sou a Pietro, agende...` — terceiro nome + typo.
- id 3663: `Sou a Pietra, agende do 2º Cartório...` — typo "agende" (agente).
- id 2204: "Detalhes técnicos do modelo de IA por trás ficam com a nossa equipe interna" (bom), mas contradito pelos leaks de 3.2.
- Nome do cartório oscila: "2º Cartório de Notas de Uberlândia" vs "2º Tabelionato de Notas de Uberlândia" (ids 3608, 3760, 3828).

### 3.4 ALTO — Valores em R$ inconsistentes
- Reconhecimento de firma: id 2068 diz **R$ 8,46 por firma**; id 3776 diz **R$ 11,21 total (8,55 + 2,66 TFJ)**; id 4065 volta a **R$ 11,21**. Duas tabelas diferentes no mesmo dia.
- Procuração: id 2212 diz **"a partir de R$ 90,53"**; id 3406 diz **R$ 156,40**; id 3760 diz **R$ 68,94 (52,43 + 16,51 TFJ)** — três valores conflitantes em 2 dias.
- Testamento: id 2214 "a partir de R$ 252,78" vs id 3762 "R$ 437,24 total".
- Citou bases legais diferentes: "Tabela de Emolumentos de MG 2026" vs "Portaria CGJ/TJMG 8.664/2025".
- id com "R$ 200.000,00" aparece em contexto de simulação de escritura.

### 3.5 MÉDIO — Placeholder e corrupção de texto
- `[IMAGE_OFICIAL_TABELIONATO]` vazado literalmente em **14 mensagens** (ids 3760–3854) — placeholder de imagem nunca resolvido.
- **10 mensagens com caracteres corrompidos** (`��\x00`, `�|\x01`) no início do texto (ids 2116, 2122, 3312, 4083...).

### 3.6 MÉDIO — Quebras de contexto
- Bot afirma 8x que "quando há troca de agente não tenho acesso ao histórico" (ids 3667–3702), revelando que o contexto não sobrevive a trocas de sessão/agente — o cliente precisa recomeçar do zero.
- id 3698: `Desculpa, doutora — não entendi bem a referência` seguido da mesma resposta LGPD padrão — evasiva em loop.
- A última mensagem do histórico (id 4083, Maria José, 72 anos, pedindo ajuda) **ficou sem resposta** — o histórico termina na mensagem dela.

### 3.7 BAIXO — Tratamento robótico/inconsistente
- "Doutora" repetido em quase toda mensagem da sessão (ex.: 3661, 3689, 3760, 3828, 3840, 3850) — soa mecânico, não carinhoso.
- Nunca usa "senhor/senhora" — inadequado para o público idoso típico de cartório (cf. persona Maria José, que chama o atendente de "meu filho").

## 4. O que os USUÁRIOS mais pedem (top 10)

| # | Tema | Msgs de usuário |
|---|------|:---:|
| 1 | Cumprimentos/abertura (oi, bom dia, boa tarde) | 83 |
| 2 | Preços/emolumentos ("quanto custa", valor, taxa) | 68 |
| 3 | Documentos necessários (RG, CPF, o que levar) | 22 |
| 4 | Certidões (nascimento, casamento, óbito) | 19 |
| 5 | Contato (WhatsApp, telefone) | 17 |
| 6 | Reconhecimento de firma | 16 |
| 7 | Escrituras | 15 |
| 8 | Testamento | 15 |
| 9 | Inventário | 11 |
| 10 | Autenticação de cópias | 11 |

(Menções: casamento 6, nascimento 6, divórcio 5, agendamento 2, endereço 1.)

## 5. Recomendações priorizadas (mais humano, formal e carinhoso)

1. **(P0) Silenciar 100% das mensagens de sistema no canal do cliente.** Rate-limit, empty stream, "Interrupting current task", "Gateway shutting down", "Redirected run", HTTP 403 — nada disso pode chegar ao iMessage do cliente. Buffer + filtro no gateway antes do envio.
2. **(P0) Eliminar leaks de modelo/infra.** Bloquear por regex outbound: "MiniMax", "deepseek", "opencode", "fallback model", "Photon", "preflight", hashes de git, comandos `/help`, `/reset`. O bot já sabe dizer "detalhes técnicos ficam com a equipe interna" (id 2204) — precisa que a infra não o desminta.
3. **(P0) Uma identidade só.** Fixar nome, gênero e razão social em system prompt + validação outbound: "Pietra, assistente virtual do 2º Tabelionato de Notas de Uberlândia" (ou o nome oficial escolhido). Teste de regressão: nunca mais "Hermes", "Pietro", "agende".
4. **(P1) Fonte única de preços.** Tabela de emolumentos versionada (RAG ou tool determinística) — hoje o bot citou 3 valores diferentes para procuração (R$ 68,94 / 90,53 / 156,40) e 2 para firma. Resposta de preço deve ser cálculo, não geração livre. Sempre com o disclaimer "valor exato confirmado pelo escrevente".
5. **(P1) Resolver o placeholder `[IMAGE_OFICIAL_TABELIONATO]`** — ou envia a imagem oficial da tabela, ou remove o token. Validação outbound para tokens `[...]` não resolvidos.
6. **(P1) Consertar encoding** — mensagens com `\x00`/`��` indicam bug de codificação no pipeline (UTF-16 vs UTF-8); sanitizar antes do envio.
7. **(P2) Tom formal-carinhoso com regra clara:** "senhor/senhora + nome" como padrão; "doutor(a)" só quando o interlocutor se identificar como advogado; no máximo 1 menção de tratamento por mensagem (hoje "doutora" aparece em quase todas — efeito robótico). Com idosos (persona Maria José), resposta mais acolhedora, frases curtas e sem juridiquês.
8. **(P2) Continuidade de contexto:** persistir resumo da conversa entre sessões/trocas de agente, para o bot não repetir 8x a evasiva "por LGPD não tenho acesso ao histórico". Se realmente não há acesso, dizer uma vez e conduzir: "me conte em uma frase o que você precisa".
9. **(P2) Garantir resposta a toda mensagem de cliente** — a mensagem da idosa Maria José (id 4083) ficou sem resposta. Implementar watchdog: toda mensagem inbound precisa de reply ou escalonamento humano em N minutos.
10. **(P3) Variar as fórmulas de fechamento** — hoje "Posso te ajudar?" / "Em que posso te ajudar?" aparecem 70+ vezes. Criar repertório de encerramentos formais e calorosos ("Fico à disposição, senhora Maria", "Qualquer dúvida, estamos aqui") e rotacionar.
