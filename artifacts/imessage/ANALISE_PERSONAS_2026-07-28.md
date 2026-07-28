# Análise Consolidada — Campanha de 10 Personas iMessage

**Data:** 2026-07-28
**Fontes:** `personas/P1..P10_report.md` + transcripts, `history_analysis_20260728.md` (2.044 msgs, chat 364)
**Corte:** P1–P6 = bot ANTIGO · P7–P10 = bot NOVO (prompt resolutivo formal-carinhoso + outbound guard anti-lixo/anti-CJK, deploy hoje)

---

## 1. Tabela comparativa por persona

| Persona | Perfil / Assunto | Bot | H | U | Issue principal |
|---|---|---|---|---|---|
| P1 | Maria José, 72a — notário itinerante | Antigo | 7 | 6 | Vazamento de sistema ("⚡ Interrupting…"), quick-replies enviadas em nome da cliente, custo nunca respondido, typo "airi", resposta a pergunta fantasma |
| P2 | JP, 21a — autenticação p/ intercâmbio | Antigo | 5 | 7 | Chinês/russo no texto (ids 4116–4124), contaminação cruzada ("matrícula do seu filho"), 2 msgs ignoradas, pergunta prática sobre cópias sem resposta |
| P3 | Dra. Camila — procuração ad judicia | Antigo | 7 | 8 | "⚡ Interrupting…" (vazamento), "via Teams" p/ outorgante no exterior (impreciso — e-Notariado), typos "ad juditia", mistura de contextos no chat |
| P4 | Seu Antônio, 81a — testamento | Antigo | 8 | 7 | Code-switch EN ("approves and signs", "documents"), frase truncada "Ligação e vai com calma", respostas cruzadas de outra sessão (id 4221) |
| P5 | Fernanda — casamento Itália/apostilamento | Antigo | 8 | 9 | "signatories" (EN), explicação de apostila enrolada, não citou tradução juramentada p/ italiano |
| P6 | Ricardo — escritura galpão R$ 1,2M | Antigo | 6 | 5 | **Grave:** "50% urgência" inventado, erro de cálculo (~5% de 1,2M = R$ 60 mil, disse R$ 4–5 mil), "roughly"/"depending on", palavra corrompida "ISSA" |
| P7 | Dona Rosa, 67a — inventário (luto) | **Novo** | 9 | 7 | "sensibility"/"sounds like" (EN, ids 4248/4250), "quandoolhar" (4254), "vou ser honesta" (voz mudou de gênero), custo 100% defletido |
| P8 | Lucas, 20a — reconhecimento de firma | **Novo** | 9 | 9 | "prosetão" (palavra inventada), espelhamento residual "Kkk", não distinguiu firma por semelhança vs autenticidade |
| P9 | Dra. Helena — procuração do exterior | **Novo** | 6 | 7 | "Carta minecraft:" (glitch, id 4272), "indeed" (EN), CRM exigido como doc civil (erro factual, id 4274), emolumento local citado p/ ato lavrado no exterior, custo/prazo vagos |
| P10 | Seu Edivaldo, 90a — inventário irmão | **Novo** | 7 | 7 | "és velho" (PT-PT + inapropriado), "explains that situation" (EN), gênero errado ("herdeira (irmã)" com irmão explícito), paredes de texto p/ idoso, "È"/"unas" |

**Placar:** Antigo H 6.8 / U 7.0 → Novo H 7.75 / U 7.5 (**+0,9 H / +0,5 U**). Mediana U antiga 7.0, nova 7.0 — ganho real está em Humanidade e na eliminação de falhas catastróficas.

---

## 2. Antes/Depois — o que o FIX resolveu de fato

### Resolveu (com evidência)

1. **Vazamento de lixo de infra/sistema — ELIMINADO.** P1–P4 tinham "⚡ Interrupting current task", mensagens de erro de provider etc. (histórico: 929 msgs de sistema, 75% do volume do bot). Em P7–P10: **zero** ocorrências reportadas. Guard `_INFRA_PATTERNS` + sanitizer em `pietra.py` funcionando.
2. **CJK/cirílico — ELIMINADO.** P2 tinha "então，大概 R$ 22-33" (id 4124) e russo "есть". P7–P10: nenhum caractere não-latino reportado. `_NON_LATIN_RE` (guard + sanitizer) cobre o caso.
3. **Contaminação cruzada de contexto — ELIMINADA.** P2 ("matrícula do seu filho" p/ universitário), P4 (resposta cruzada id 4221). P8, P9 e P10 explicitamente notam "contexto novo tratado limpo" mesmo com histórico de outras personas no mesmo chat. Regra "ISOLAMENTO DE CONVERSA (P0)" do prompt novo eficaz.
4. **Identidade estável.** Histórico antigo: 88x "Pietra" vs 16x "Hermes" vs "Pietro"/"agende". Nenhuma crise de identidade em P7–P10.
5. **Valores de emolumentos consistentes.** P5 (R$ 68,94 procuração) e P8 (R$ 11,21 firma, 3x consistente) — vs. histórico antigo com 3 valores conflitantes p/ procuração e 2 p/ firma. Tool `cartorio_calcular_emolumento` + REGRA DE OURO funcionando.
6. **Acolhimento emocional de alto nível.** P7 (luto) é o melhor atendimento da campanha (H9): condolências antes do prático, sem pular etapas. Regra "Acolhimento Emocional (P0)" do prompt novo entregou.
7. **Espelhamento de gíria — MUITO reduzido.** P2 espelhava "kkkk" livremente; no bot novo só resíduo pontual ("Kkk" em P8).

### NÃO resolveu

1. **Language mixing EN/PT-PT residual** — o guard só pega ranges não-latinos (CJK/cirílico/kana/hangul/grego/árabe). Inglês e PT-PT são ASCII/latim e passam: "sensibility", "sounds like" (P7), "indeed" (P9), "explains that situation" (P10), "és velho" (P10). **Continua em produção hoje.**
2. **Glitches de token / palavras inventadas** — "prosetão" (P8), "Carta minecraft:" (P9, id 4272), "quandoolhar" (P7, id 4254), "ISSA" (P6, antigo). Nenhuma camada atual detecta palavra fora de dicionário.
3. **Erros de gênero/voz** — "vou ser honesta" (P7), "você é herdeira (irmã)" com irmão explícito (P10). O prompt novo proíbe presumir gênero **do cliente no tratamento**, mas não cobre concordância sobre terceiros nem a própria voz da Pietra.
4. **Paredes de texto** — P10: 4 de 5 respostas com múltiplas seções/bullets para um idoso de 90 anos; só simplificou quando pediu. Regra "Estilo no Canal" existe mas não é enforcement.
5. **Deflexão de custo em atos complexos** — inventário (P7, P10) e atos no exterior (P9): zero faixa de valor. REGRA DE OURO cobre atos tabelados; atos com `HITL_REQUIRED` caem em "só o escrevente calcula", sem orientação intermediária.
6. **Precisão técnica** — CRM como doc civil (P9), emolumento local citado p/ ato lavrado em Portugal (P9), firma semelhança vs autenticidade omitida (P8), tradução juramentada omitida (P5), "via Teams" (P3, antigo — bot novo citou e-Notariado corretamente em P9, melhora parcial).
7. **HITL/urgência** — o "50% urgência inventado" foi P6 (bot antigo). O prompt novo já diz "urgência → escrevente humano", mas **nenhuma persona P7–P10 testou urgência** — cobertura não verificada em produção.
8. **Quick-replies em nome do cliente** (P1), **placeholder `[IMAGE_OFICIAL_TABELIONATO]`** (14x no histórico), **encoding `��`** (10 msgs no histórico) — anteriores ao deploy; o guard atual **não** tem regra para tokens `[...]` nem para U+FFFD — precisa verificação/fix independente.

---

## 3. Taxonomia dos issues restantes (priorizada)

### P0 — credibilidade/correção factual

| # | Issue | Evidência | Causa provável | Fix proposto |
|---|---|---|---|---|
| P0-1 | **Language mixing EN/PT-PT residual** | P7 ids 4248 ("sensibility"), 4250 ("sounds like"); P9 id 4272 ("indeed"); P10 ("explains that situation", "és velho") | Guard e sanitizer só testam `_NON_LATIN_RE` (ranges não-latinos); EN/PT-PT são latim puro e passam. Prompt proíbe mas modelo não obedece 100% | (a) Estender o sanitizer em `backend/app/api/v1/pietra.py::_sanitize_pietra_output`: léxico de anglicismos/PT-PT (lista curada: sounds like, indeed, roughly, depending on, explains that, sensitivity/sensibility, és/estás/tu-forms) → detecção dispara **retry 1x** (mesmo fluxo já existente de `non_latin_retry`), não strip cego. (b) Reforço no `PIETRA_SYSTEM_PROMPT`: "Se surgir qualquer palavra inglesa ou português europeu na minuta, reescreva em PT-BR antes de enviar." (c) Métrica `language_mixing_latin` no guard para observabilidade |
| P0-2 | **Palavras inventadas / glitch de token** | P8 "prosetão"; P9 id 4272 "Carta minecraft:"; P7 id 4254 "quandoolhar"; P6 "ISSA" | Modelo rápido/barato (M2.7-HighSpeed) com temperatura efetiva alta; nenhuma validação lexical de saída | (a) Validador léxico determinístico no sanitizer: checar tokens contra dicionário PT-BR (wordfreq/hunspell-pt-br); token fora do dicionário e fora de whitelist (nomes próprios, siglas: CRM, RG, CPF, IPTU, LGPD, e-Notariado) → retry 1x. (b) Reduzir `temperature` da chamada em `_chat_completion` (provável 0.7+ → 0.3) para atendimento factual. (c) Avaliar troca de modelo (seção 5) |
| P0-3 | **Erro factual em requisitos/documentos** | P9 id 4274: CRM listado como documento da outorgada; P9: emolumento R$ 68,94 citado p/ procuração lavrada em Portugal | Modelo gera requisitos de memória, sem fonte. Tool de emolumentos não sabe que o ato é no exterior | (a) Prompt: regra explícita "Documentos de identificação válidos para atos notariais: RG, CNH ou passaporte + CPF. NUNCA exigir carteira profissional (CRM/OAB/CREA) como documento civil." (b) Prompt/tool: "Emolumentos deste cartório só valem para atos lavrados AQUI; ato lavrado no exterior (consulado/notário estrangeiro) tem custo do órgão de origem — não citar valor local." (c) Adicionar FAQ técnico curado no RAG/contexto para os 6 temas mais cobrados (seção 3 P1-3) |
| P0-4 | **Placeholder/encoding/quick-reply** (pré-deploy, guard não cobre) | Histórico: `[IMAGE_OFICIAL_TABELIONATO]` 14x (ids 3760–3854); `��`/`\x00` 10x (ids 2116, 2122, 4083); P1: quick-replies enviadas como se fossem da cliente | (a) Token de template nunca resolvido antes do envio; (b) bug de encoding UTF-16/UTF-8 no pipeline; (c) mecanismo de quick-reply usa `is_from_me=true` | (a) Guard outbound (`pietra_outbound_guard.py`): novo padrão `\[IMAGE_[A-Z_]+\]` e regex genérica `\[[A-Z_]{4,}\]` → strip + fallback se sobrar vazio. (b) Sanitizer: detectar U+FFFD / `\x00` → retry (texto corrompido não é recuperável por strip). (c) Corrigir no remetente (iMessage bridge): quick-reply suggestion nunca pode ser enviada como mensagem do cliente; marcar como metadata, não como texto |

### P1 — qualidade de atendimento

| # | Issue | Evidência | Causa provável | Fix proposto |
|---|---|---|---|---|
| P1-1 | **Deflexão de custo em atos complexos** | P7 id 4254 ("só o escribente calcula"); P10 ("algumas centenas a uns poucos milhares"); P9 (custo/prazo "a consultar") | Tool retorna `HITL_REQUIRED` p/ inventário/escritura e o prompt manda não inventar número — correto, mas o modelo deflete 100% em vez de dar faixa/orientação | Prompt: para `HITL_REQUIRED`, responder com (1) o que compõe o custo (emolumentos por faixa de valor do bem + TFJ + escritura), (2) exemplo ancorado genérico sem promessa ("para imóveis de valor popular, costuma ficar na casa das centenas a poucos milhares — o escrevente confirma o exato"), (3) caminho de isenção/assistência quando o cliente declara dificuldade financeira. Faixa qualitativa permitida; número exato inventado continua proibido |
| P1-2 | **Erros de gênero/voz** | P7 id 4254 "vou ser honesta" (voz oscilou); P10 "você é herdeira (irmã)" com irmão explícito | Prompt proíbe presumir gênero do interlocutor, mas não ancora a voz da Pietra nem concordância sobre terceiros citados | Prompt: (a) "A Pietra é sempre feminina — nunca varie a própria voz ('vou ser honesta', nunca 'honesto')." (b) "Para terceiros citados pelo cliente, use o gênero que o CLIENTE usou (irmão → herdeiro); na dúvida, forma neutra ('o herdeiro', 'a pessoa')" |
| P1-3 | **Precisão técnica em temas recorrentes** | P8: não distinguiu firma por semelhança vs autenticidade; P5: omitiu tradução juramentada p/ Itália; P3 (antigo): "via Teams"; P9: apostila consular vs notário estrangeiro confusa | Conhecimento de domínio notarial ausente do contexto; modelo improvisa | Adicionar bloco "Notas técnicas" no prompt (ou RAG): (1) firma: sempre perguntar semelhança (mais barata, exige firma cadastrada) vs autenticidade; (2) apostilamento p/ casamento/cidadania no exterior → mencionar tradução juramentada; (3) ato com outorgante no exterior → e-Notariado ou consulado (nunca "videochamada comum"); consulado brasileiro NÃO precisa de apostila, notário estrangeiro precisa; (4) poderes p/ venda de imóvel → poderes especiais e específicos (art. 105 CC) |
| P1-4 | **Paredes de texto p/ iMessage/idosos** | P10: 4/5 respostas com seções+bullets (15–25 linhas) p/ cliente de 90 anos; só simplificou após pedido | Regra "Estilo no Canal" é aspiracional; modelo defaulta para estrutura de relatório | (a) Prompt: regra dura "máx. ~8 linhas por mensagem; para idosos ou quem escreve mensagens curtas, 3–4 passos numerados e UMA pergunta por vez, desde a PRIMEIRA resposta — não esperar pedido de simplificação". (b) Guard leve: resposta > N caracteres (ex.: 900) com >2 listas → retry pedindo versão curta (mesmo mecanismo do sanitizer) |
| P1-5 | **HITL urgência — não verificado no bot novo** | P6 (antigo) id: "acréscimo de 50%" inventado + encaixe prometido indiretamente | Prompt novo já encaminha urgência ao escrevente, mas a campanha P7–P10 não incluiu persona de urgência | Antes de fechar o round 2, rodar 1 persona de urgência/pressão (replay do roteiro P6) contra o bot novo e validar: sem percentual inventado, sem promessa de encaixe, encaminhamento ao escrevente com explicação CNS/CNJ |

### P2 — polimento

| # | Issue | Evidência | Causa provável | Fix proposto |
|---|---|---|---|---|
| P2-1 | Espelhamento residual de gíria | P8: "Ficou claro agora? Kkk" | Prompt proíbe, modelo escapa em rapport | Reforço de prompt com exemplo negativo explícito; validador barato no sanitizer: `\b[kK]{2,}\b` em mensagem do bot → strip da risada (não retry — baixo risco) |
| P2-2 | Typos/junções recorrentes | "È"→"É", "unas" (P10); "ad juditia", "aprocuração" (P3, antigo) | Modelo rápido; temperatura | Coberto em parte por P0-2 (validador léxico pega "quandoolhar", não pega "ad juditia" que é palavra quase-válida); whitelist com termos jurídicos corretos + correção ortográfica leve no sanitizer |
| P2-3 | Repetição mecânica dos telefones | P7: telefones em 4 de 5 respostas | Prompt lista telefones; modelo os repete como fórmula de fechamento | Prompt: "cite telefone/WhatsApp no máximo 1x por conversa, ou quando o cliente pedir contato" |
| P2-4 | Tom oscilante formal↔coloquial | P9: "Liga pro Consulado" p/ médica formal | Espelhamento de registro sem piso formal | Prompt: "piso de registro: 'a senhora/você' + imperativo formal ('ligue', 'traga') com interlocutores formais ou que se apresentam com título" |

---

## 4. Plano FIX ROUND 2 (ordenado por impacto)

| Ordem | Mudança | Tipo | Arquivo | Impacto estimado |
|---|---|---|---|---|
| 1 | **Language guard latino**: léxico EN/PT-PT → retry 1x (não strip) + métrica | Código | `backend/app/api/v1/pietra.py::_sanitize_pietra_output` (+ espelho em `services/pietra_outbound_guard.py`) | Elimina o issue nº1 do bot novo (5 personas atingidas); +0,3–0,5 H |
| 2 | **Validador léxico anti-glitch** (wordfreq/hunspell-pt-br + whitelist) → retry 1x; baixar `temperature` p/ 0.3 nas respostas factuais | Código | `pietra.py::_sanitize_pietra_output`; `services/cartorio_agent.py::_chat_completion` | Elimina "prosetão"/"Carta minecraft"/"quandoolhar" — maior destruidor de credibilidade com personas detalhistas (P9 caiu p/ H6 por isso); +0,5 H em personas exigentes |
| 3 | **Regras de prompt: custo HITL com faixa orientativa + não-presunção de gênero de terceiros + voz fixa feminina + limite de tamanho p/ idosos + notas técnicas (firma, apostila+tradução, exterior, CRM)** | Prompt | `pietra.py::PIETRA_SYSTEM_PROMPT` (~linha 470) | Resolve P1-1..P1-4 de uma vez; +0,5–1,0 U em inventário/escritura/exterior |
| 4 | **Guard anti-placeholder e anti-`��`** (`\[[A-Z_]{4,}\]`, U+FFFD/`\x00` → retry/fallback) + fix do quick-reply no bridge iMessage | Código | `pietra_outbound_guard.py`; remetente iMessage (fora deste repo — verificar bridge) | Fecha regressões do histórico pré-deploy que o guard atual não cobre |
| 5 | **Validação HITL urgência**: replay da persona P6 contra bot novo antes do deploy do round 2 | Processo/QA | roteiro P6 em `artifacts/imessage/personas/` | Garante que "50% inventado" não recorra; gate de release |
| 6 | Strip barato de `Kkk`/risadas no sanitizer + regra "1 telefone por conversa" + piso formal | Código + prompt | `pietra.py` | Polimento; +0,1–0,2 H |

**Sequência sugerida:** 1+3 (mesma janela, prompt+guard) → 2 (precisa de dependência lexical, validar falso-positivo com nomes próprios de Uberlândia) → 4 → gate 5 → 6. Re-rodar as 10 personas após o deploy; critério de aceite: H ≥ 8.5, U ≥ 8.0, zero language-mixing e zero glitch de token nas 50 respostas.

---

## 5. Recomendação de modelo: M2.7-HighSpeed vs K3 256K

**Diagnóstico:** os issues P0-1 (mixing EN/PT-PT), P0-2 (glitches de token), P1-2 (concordância) e P2-2 (typos) têm assinatura de modelo: são falhas de **instruction-following sob geração rápida** e de **qualidade de decodificação**, não de prompt — o prompt novo já proíbe explicitamente tudo isso e o modelo escapa mesmo assim. Guard/sanitizer mitigam, mas cada retry custa latência e cada fallback é uma mensagem perdida.

**Recomendação: sim, avaliar K3 256K em A/B — mas com gate objetivo, não por impressão.**

Critérios objetivos (rodar a mesma suíte de 10 personas + harness existente em ambos):

1. **Taxa de language mixing**: nº de respostas com token EN/PT-PT fora de whitelist por 50 respostas. Gate: 0 no K3; se M2.7 > 2 mesmo com guard, troca se justifica.
2. **Taxa de glitch de token** (palavra inventada / string fora de contexto / junção): gate 0; qualquer "Carta minecraft" é falha de modelo, não de stack.
3. **Aderência a instrução**: % de respostas violando regras explícitas do prompt (gíria espelhada, emoji indevido, gênero presumido, parede de texto). Gate ≥ 95%.
4. **Confiabilidade de tool-call**: % de perguntas de preço respondidas com `cartorio_calcular_emolumento` na mesma resposta (REGRA DE OURO). Gate ≥ 99% — modelo fraco aqui inventa valor (risco P0 financeiro, cf. P6).
5. **Latência p95** no iMessage: ≤ 8s por resposta (K3 256K tem contexto maior; medir, não assumir).
6. **Custo por conversa de 5 turnos**: comparar custo total K3 vs (M2.7 + custo dos retries do sanitizer). Se K3 elimina 80% dos retries, o delta de preço pode se pagar.
7. **Regressão de empatia**: K3 precisa manter o nível de acolhimento de P7 (H9) — modelo mais "certo" porém mais frio não resolve o negócio.

**Decisão:** se K3 zerar os itens 1–2 e segurar 3–5 com latência aceitável, migrar; o guard vira segunda linha de defesa (como deveria ser) em vez de muleta do modelo. Se o ganho for marginal, manter M2.7-HighSpeed + FIX ROUND 2 e reavaliar após o round 2.

---

*Gerado por QA — consolidação da campanha de 10 personas. Nenhum código modificado; nenhuma mensagem enviada.*
