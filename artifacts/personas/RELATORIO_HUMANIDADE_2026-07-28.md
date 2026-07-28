# Relatório de Auditoria de Humanidade — Pietra (10 personas)

**Data:** 2026-07-28 · **Auditor:** SUBAGENT-ANALISTA (squad Cartório)
**Fonte:** `artifacts/personas/*.json` — 10 conversas reais via iMessage, 59 turnos, 59 OK / 0 fail / 0 timeout (transporte 100%, mas qualidade de conteúdo severamente comprometida).

---

## 1. Tabela por persona

| Persona | Idade | OK/Fail/TO | warm_avg | Humanidade | Formalidade | Carinho | Resumo |
|---|---|---|---|---|---|---|---|
| Carla | 31 | 5/0/0 | 0.00 | 5 | 4 | 4 | Objetiva e útil, mas chinês no preço ("大致估算") + artifact no turno 4. |
| Dona Ester | 85 | 6/0/0 | 0.17 | 6 | 5 | 6 | Carinhosa com a idosa, porém "祥细", "like você", "ellos", "lucinda" numa conversa de testamento. |
| Dra. Fernanda | 42 | 6/0/0 | 0.17 | 2 | 3 | 2 | Desastre: contaminação total com caso de "filha acamada/INSS" — a advogada recebeu respostas de outra conversa. |
| João | 35 | 6/0/0 | 0.00 | 7 | 6 | 5 | Conversa mais limpa do lote: funcional, direta, apenas fria. |
| Lucas | 20 | 6/0/0 | 0.00 | 3 | 3 | 4 | Chamou o Lucas de "Camila" e respondeu sobre procuração ad juditia que ninguém pediu. |
| Maria | 24 | 6/0/0 | 0.00 | 4 | 5 | 4 | Vazou "via Photon (iMessage)" e encerrou com "De nada, Gustavo!" para a Maria. |
| Patrícia | 48 | 6/0/0 | 0.50 | 7 | 6 | 8 | Melhor empatia (luto), mas "比不上", "they", "Gedanken" estragam o acolhimento. |
| Roberto | 55 | 5/0/0 | 0.00 | 4 | 5 | 3 | Artifact + respostas deslocadas em quase todos os turnos (perguntou docs, recebeu preço). |
| Seu Antônio | 78 | 6/0/0 | 0.33 | 2 | 4 | 3 | Pior caso: chinês em 4 turnos (inclusive "糟了太久没看见了" 3x), russo "есть", contaminou com "Maria José/acamada". |
| Seu Jorge | 67 | 7/0/0 | 0.29 | 3 | 5 | 3 | Chamado de "Antonio" 3 vezes, artifact, respostas deslocadas, "documents" em inglês. |

**Médias (baseline pré-upgrade):** Humanidade **4.3** · Formalidade **4.6** · Carinho **4.2** · warm_avg **0.146**

---

## 2. Falhas Sistêmicas (frequência × gravidade)

### P0 — críticas (risco de imagem institucional e jurídico)

1. **Vazamento multilíngue** — 7/10 personas, ~11 turnos. Chinês (大致估算, 祥细, 可能会有, 爱你, 糟了太久没看见了 ×3, 会的。会加油的。会顺利的。), russo (есть), alemão (Gedanken), inglês solto (they, like, documents, explains that situation). Inaceitável em serviço notarial com fé pública; em idosos (Ester, Antônio) beira o constrangimento.
2. **Contaminação de contexto entre conversas** — 3 personas, ~5 turnos. Casos e nomes de outras sessões injetados: "filha acamada / reconhecimento de firma pra INSS" na conversa da Dra. Fernanda (ata notarial); "caso da Maria José" na do Seu Antônio; "Camila / procuração ad juditia" na do Lucas. Além de quebrar a experiência, é potencial incidente LGPD (eco de dados de terceiros).
3. **Nome errado / identidade trocada** — 2 personas, 4 turnos. "De nada, **Gustavo**!" para Maria (vazou o nome do operador/dono); "Antonio" 3× para Seu Jorge. Destrói confiança na hora.
4. **Artifact "[This response was interrupted by a user correction.]" entregue ao cliente** — 5 personas (Carla T4, Fernanda T2, Lucas T2, Roberto T2, Jorge T4). Placeholder interno do gateway vazando como resposta final.
5. **Dessincronia de turnos** — 6 personas, ~9 turnos. Resposta claramente referente à pergunta anterior/seguinte (Carla T2, Roberto T3–T5, Lucas T4–T5, Fernanda T4/T6, Jorge T2). Mesma raiz provável do artifact: pipeline de streaming perde o pareamento pergunta↔resposta.

### P1 — altas

6. **Typos da bot** — 6 personas: "tranqulão", "acostumbrado", "lucinda", "ellos", "vizigo", "diferentão", "compararse", "se.programando", "au caso", "Att,".
7. **Vazamento de vocabulário interno** — 1 persona (Maria T4): "como é via Photon (iMessage)". Viola a regra de nunca expor stack/gateway.

### P2 — moderadas

8. **Frieza (warm_avg baixo)** — 4 personas com 0.00; média geral 0.146. Bot funciona como FAQ, não como atendente do cartório.
9. **Markdown pesado no iMessage** — negrito/listas longas para Dona Ester (85) e Seu Antônio (78), canal que renderiza mal.
10. **Gíria excessiva ("kkkk")** — Carla (2×), Lucas; espelhamento sem filtro de registro.

---

## 3. Scores agregados (baseline pré-upgrade)

| Métrica | Valor |
|---|---|
| Turnos totais / OK transporte | 59 / 59 (100%) |
| Turnos com ≥1 falha P0 | ~28 (47%) |
| Turnos limpos | ~31 (53%) |
| warm_avg médio | 0.146 |
| Humanidade média | 4.3 / 10 |
| Formalidade média | 4.6 / 10 |
| Carinho médio | 4.2 / 10 |
| Personas sem nenhuma falha P0 | 1 (João) |

---

## 4. Plano de Upgrade

### (a) Guardrail / sanitizador determinístico — `backend/app/api/v1/pietra.py`

1. **Filtro pós-LLM de idioma**: regex `\u4e00-\u9fff` (CJK), `\u0400-\u04ff` (cirílico) e stoplist de termos DE/EN fora de whitelist institucional → descarta a resposta e re-gera (máx. 1 retry) ou cai em fallback determinístico em pt-BR.
2. **Filtro de artifact**: qualquer resposta contendo `[This response was interrupted` (ou placeholders internos) nunca é entregue; dispara re-geração.
3. **Guard de nomes**: extrai nomes próprios da resposta e rejeita qualquer nome ausente do contexto da conversa atual (bloqueia "Camila", "Maria José", "Gustavo").
4. **Turn-lock por correlation ID**: resposta só é enviada se o ID do turno casar com a última pergunta do contato; órfãs são descartadas.

### (b) System prompt — `PIETRA_SYSTEM_PROMPT` + `SOUL.md`

1. Regra explícita: **responder exclusivamente em português brasileiro**, incluindo interjeições e vocativos — proibido qualquer token em outro idioma.
2. **Isolamento de sessão**: "use somente informações desta conversa; nunca mencione nomes, casos ou detalhes de outros atendimentos".
3. Diretriz de calor adaptativa (idosos e luto = mais acolhimento), teto de 1 "kkk" por conversa, markdown mínimo em canal iMessage, proibição de citar tecnologia interna (Photon, iMessage, gateway, modelo).

### (c) Arquitetura / gateway

1. **Envelope com correlation/turn ID** iMessage↔gateway: respostas de turnos interrompidos são descartadas no gateway (nunca convertidas em placeholder entregue).
2. **Namespacing de memória/sessão por contato** (session key = remetente), eliminando a contaminação cruzada entre conversas concorrentes.
3. **Retry-regenerate em vez de texto parcial**: interrupção de stream → nova geração completa; placeholder vira log interno, não mensagem.

---

*Baseline registrado para comparação pós-upgrade. Não executar novos testes de persona antes de aplicar as ações (a)1–(a)4.*
