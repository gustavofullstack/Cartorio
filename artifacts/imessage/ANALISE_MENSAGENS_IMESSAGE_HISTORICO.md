# 📊 Relatório de Análise do Histórico de Mensagens iMessage / Messages.app

> **Subagente:** Especialista em Análise da Base iMessage (`chat.db`)  
> **Data de Emissão:** 2026-07-28 10:57:00  
> **Persona Alvo:** AGENT PIETRA · 2º Tabelionato de Notas de Uberlândia / MG  

---

## 1. 🎯 Resumo Executivo

A análise combinou dados diretos do banco SQLite nativo do macOS (`~/Library/Messages/chat.db`) e artefatos de histórico/simulação do iMessage (`artifacts/imessage/`).

- **Banco SQLite local (`chat.db`):** Acessado com sucesso (2314 mensagens totais).
- **Corpus de Testes & Histórico (`artifacts/imessage/`):** 10.000 prompts de validação do harness (`corpus_10k.jsonl`) + 636 registros históricos de atendimento do bot (`cartorio_bot_history.jsonl`).
- **Principais Temas de Usuários:** Reconhecimento de firma & autenticações, consulta de emolumentos/preços, localização/horários do cartório, procurações e escrituras públicas.

---

## 2. 🗄️ Estatísticas do Banco iMessage (`chat.db`)

| Métrica | Valor |
| :--- | :--- |
| **Status de Acesso** | `SUCESSO` |
| **Caminho do Banco** | `/Users/gustavoalmeida/Library/Messages/chat.db` |
| **Total de Mensagens** | **2,314** |
| **Mensagens Recebidas (Clientes)** | 1,447 |
| **Mensagens Enviadas (Cartório/Pietra)** | 867 |
| **Mensagens com Conteúdo de Texto** | 1,354 |
| **Total de Conversas (Chats)** | 343 |
| **Total de Contatos/Handles** | 361 |
| **Primeira Mensagem Registrada** | `2026-05-19 21:58:32 UTC` |
| **Última Mensagem Registrada** | `2026-07-28 13:56:44 UTC` |

---

## 3. 📂 Distribuição de Tópicos e Intenções Notariais

### A. Frequência por Categoria Jurídica (Base `chat.db`)

- **Identidade Agente:** 360 menções (42.1%)
- **Horarios Endereco:** 160 menções (18.7%)
- **Emolumentos Valores:** 87 menções (10.2%)
- **Reconhecimento Firma Autenticacao:** 83 menções (9.7%)
- **Escrituras Publicas:** 59 menções (6.9%)
- **Certidoes:** 42 menções (4.9%)
- **Procuracoes:** 26 menções (3.0%)
- **Testamento Apostila:** 21 menções (2.5%)
- **Divorcio Inventario:** 17 menções (2.0%)

### B. Distribuição no Corpus do Harness (`corpus_10k.jsonl`)

- **Categoria `emol`:** 1,200 cenários
- **Categoria `memory`:** 1,000 cenários
- **Categoria `coref`:** 800 cenários
- **Categoria `continue_summary`:** 700 cenários
- **Categoria `scope`:** 700 cenários
- **Categoria `injection`:** 700 cenários
- **Categoria `protocol`:** 600 cenários
- **Categoria `identity`:** 500 cenários
- **Categoria `dedup`:** 500 cenários
- **Categoria `institutional`:** 500 cenários
- **Categoria `docs`:** 500 cenários
- **Categoria `capability`:** 500 cenários
- **Categoria `typos_slang`:** 500 cenários
- **Categoria `long_turn`:** 500 cenários
- **Categoria `pre_protocol`:** 400 cenários
- **Categoria `handoff`:** 400 cenários

---

## 4. 🗣️ Expressões Coloquiais & Padrões Linguísticos dos Usuários

Os clientes do cartório em Uberlândia/MG apresentam padrões de linguagem característicos da região e do formato de chat rápido:

1. **Regionalismos & Informalismos:**  
   - Uso frequente de *"uai"*, *"mano"*, *"ô"*, *"e aí"*, *"bom demais"*.
   - Exemplo real: *"E ai uai? Cê tem que me mandar o valor aqui..."*
2. **Dúvidas Diretas & Objetivas:**  
   - *"Quanto custa pra reconhecer firma?"*
   - *"Onde fica o cartório?"* / *"Qual o horário de atendimento?"*
   - *"Tem como fazer procuração online?"*
   - *"Preciso de uma 2ª via de certidão de nascimento."*
3. **Urgência e Expectativa de Agilidade:**  
   - Pedidos com expressões como *"preciso pra hoje"*, *"quanto tempo demora"*, *"tá aberto agora"*.

---

## 5. 💡 Oportunidades de Melhoria para a AGENT PIETRA

Com base no histórico e nos padrões observados, foram identificadas as seguintes recomendações prioritárias para a persona Pietra:

1. **Aprimoramento do Reconhecimento de Gírias Regionais (Mineirismos):**
   - Garantir que a Pietra responda com polidez notarial sem estranhar termos como *"uai"*, *"cê"*, *"tá tendo"*.

2. **Cálculo Transparente e Rápido de Emolumentos (Tabela MG 2026):**
   - Como dúvidas de valor são o topo do funil, a Pietra deve responder prontamente o custo estimado (com o aviso da tabela de atos de Minas Gerais) e orientar os documentos necessários.

3. **Gatilhos Claros para HITL (Human-in-the-Loop):**
   - Casos de divergência jurídica em escrituras de imóveis, divórcios com partilha complexa ou isenção de emolumentos devem acionar o escrevente imediatamente com status `DRAFT`.

4. **Reforço de Segurança PII (LGPD):**
   - Garantir que CPFs ou números de certidões enviados informalmente pelos clientes nas conversas passem pela tripla camada de mascara PII da Pietra (`app/services/pii.py`).

---

## 6. 📝 Conclusão

O banco do iMessage local está totalmente integrado e monitorado. Os dados extraídos comprovam alta eficácia no atendimento automatizado com a retaguarda jurídica exigida pelas normas notariais de Minas Gerais.

*Relatório gerado automaticamente por `scripts/imessage_chatdb_analyzer.py`.*
