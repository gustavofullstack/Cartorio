# Lesson 302 — Revisão Operacional do Manual do Chatbot 2º Notas de Uberlândia (2026-08-18)

## 1. Contexto & Causa Estrutural
- A Pietra consultava fontes diferentes e conflitantes para o cálculo de emolumentos e regras de atendimento.
- A tool MCP `cartorio_calcular_emolumento` retornava a camada regulatória da Portaria TJMG 8.664/2025 (`regulatory_tjmg`, ex.: Procuração Geral R$ 68,94), enquanto o total cobrado no balcão da serventia é a camada operacional (`operational_pos_2notas`, ex.: Procuração Genérica R$ 71,38).
- `_match_servico` mapeava qualquer citação de procuração para a modalidade genérica, ignorando se a finalidade era financeira (R$ 226,14) ou previdenciária (R$ 37,91).
- Atos simples de balcão (reconhecimento de firma, abertura de firma/cartão, arquivamento, autenticações, DUT/ATPV e xerox) permitiam pré-agendamento no prompt/capabilities, violando a regra administrativa de atendimento presencial por ordem de chegada com senhas preferenciais (idosos, autistas, advogados e PCDs).

## 2. Decisões de Arquitetura & Implementação (Issue #199)
1. **Camada Operacional Atualizada (2026)**:
   - `autenticacao_documento_eletronico`: corrigida de R$ 13,46 para **R$ 13,91** em `emolumento_operacional_balcao.py`.
   - Adicionados `reconhecimento_dut_atpv` (**R$ 16,61**, com CNTV/MG R$ 5,00), `xerox_1_face` (**R$ 1,80**) e `xerox_2_faces` (**R$ 3,60**).
   - Implementado `calcular_emolumento_operacional(...)` retornando status `PUBLISHED` para atos diretos e `HITL_REQUIRED` para urgência/composições complexas.
2. **Desambiguação Obrigatória de Procuração**:
   - Para qualquer pergunta genérica como *"quanto custa uma procuração?"*, o agente obrigatoriamente pergunta:
     > *"Qual será a finalidade da procuração? Por exemplo: representação simples, INSS, banco, venda de veículo, venda de imóvel ou recebimento de valores."*
   - Roteamento:
     * Genérica / Ad Judicia / Órgãos: **R$ 71,38**
     * Financeira / Patrimonial / Bancos / Venda de Bens: **R$ 226,14**
     * INSS / Previdenciária / Benefício: **R$ 37,91**
3. **Bloqueio de Pré-agendamento em Balcão**:
   - Atos simples de balcão recebem resposta orientando ordem de chegada e senhas preferenciais:
     > *"Para esse atendimento de balcão não há pré-agendamento. O atendimento é presencial e por ordem de chegada. Pessoas idosas, pessoas autistas, advogados e pessoas com deficiência recebem senha preferencial."*
   - Pré-agendamento permanece ativo apenas para escrituras e atos complexos.
4. **Separação de Camadas no MCP Server**:
   - `cartorio_calcular_emolumento(tipo, folhas=1, urgencia=False, pricing_layer="regulatory_tjmg")` suporta `pricing_layer="operational_pos_2notas"`.
5. **Canned Responses Sanitizadas**:
   - Removidos valores legados (R$ 156,40, R$ 28,90, R$ 32,10, R$ 245,80, R$ 198,60, R$ 132,40) de `chatwoot_canned_responses.py`.
6. **Divergências Documentadas sem Inferência**:
   - As duas discrepâncias do relatório de 03/08/2026 (RECIVIL no reconhecimento de firma e texto de arquivamento R$ 11,61 vs total R$ 13,91) permanecem registradas para confirmação humana, com o bot informando apenas os totais operacionais consolidados.

## 3. Testes & Cobertura
- Criado `backend/tests/test_issue_199_balcao_procuracoes.py` (29 testes dedicados cobrindo todas as regras).
- Suíte focada executada com 284/284 testes verdes (100% PASS).
- Verificação de secrets (`check_no_literal_keys.py`) com 0 violações.
- Código commitado no branch `feat/issue-199-balcao-procuracoes-regras` via Conventional Commits.
