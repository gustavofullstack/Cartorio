# Análise completa — conversas com Felipe Pizarro

**Data da análise:** 2026-09-02
**Fontes cruzadas:** WhatsApp.app (ChatStorage.sqlite) · Google Drive · GitHub `gustavofullstack/Cartorio` · VPS `cartorio` (tailnet) · Evolution API / agente MiniMax
**Método:** extração integral do fio 1:1 e cruzamento requisito-a-requisito com o código e a produção.
Cada afirmação abaixo carrega status de evidência conforme a regra evidence-first.

---

## 1. O corpus

| Métrica | Valor |
|---|---|
| Período | 16/05/2026 → 01/09/2026 (109 dias) |
| Mensagens totais | **1.480** |
| Do Felipe | 696 · Do Gustavo | 784 |
| Áudios | 169 (67 Felipe / 102 Gustavo) |
| Documentos trocados | 25 |
| JID | `260541373247704@lid` |

`VERIFIED_LIVE` — fonte: `~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`, tabelas `ZWAMESSAGE`/`ZWACHATSESSION`, 02/09/2026 18:42.

**Grupo relacionado:** "Cartório 2 Ofício de Notas de Uberlândia" (`120688748835058@lid`) — apenas 1 mensagem. Todo o projeto correu no 1:1.

---

## 2. Quem é quem

- **Felipe Pizarro** — tabelião substituto, é quem decide tecnicamente e opera o dia a dia. `febianchinipizarro@gmail.com` / `felipepizarro@uol.com.br`. Também faz impressão 3D como hobby remunerado (`@brutalspanj3d`).
- **Djalma de Oliveira Pizarro** — o titular ("dono dos bois"), 70 anos. Decide **só valores**. Felipe: *"ele não entende nada"*, *"o restante é comigo"*.
- **William** — TI terceirizado do cartório. Criou `atendimento@2notasudi.com.br`. Gustavo o avaliou como *"meio fraquinho"*, focado em hardware/manutenção.
- **Victor Hugo Bianchini Pizarro** — **não trabalha mais no cartório** (informado em 28/07). Já virou guarda de saída no código.

---

## 3. O contrato — o que foi realmente combinado

| Item | Valor | Evidência |
|---|---|---|
| Setup | **R$ 2.800,00** | 17/06 16:21 |
| Recorrente | **R$ 100,00/mês** (VPS dedicada) | 17/06 16:21 |
| Escopo | **Somente automação de WhatsApp** — Djalma recusou os 2 serviços opcionais | 17/06 12:03 |
| Faturamento | **Pessoa física**: Djalma Pizarro, CPF 005.658.718-03, Rua Cel. Antônio Alves Pereira 850, Centro, Uberlândia/MG, CEP 38400-104 | 17/06 16:31–16:32 |
| Contrato | Assinado pelas duas partes | 21/06 16:26 |
| Pagamento | PIX `gustavo@triqhub.tech`, comprovante em 21/06 17:46 | 21/06 |
| Recibo | Emitido 21/06 17:54 | — |
| **Nota fiscal** | **Nunca emitida.** Djalma dispensou, mas Felipe pediu o recibo *"para lembrar de te cobrar a nota fiscal"* | 21/06 17:49–17:53 |

**Marketing está fora do escopo por lei** — cartório é proibido de fazer propaganda (11/06 13:37).
A infra foi comprada pelo próprio Felipe na Hostinger com o cupom `gustavoedc`, KVM 4 + EasyPanel (18–19/06).

---

## 4. Estado real da produção — verificado agora

```
https://api.2notasudi.com.br/health   → 200  {"status":"ok","service":"cartorio-backend","version":"0.6.0"}
https://2notasudi.com.br              → 200
https://cartorio-evolution-api...     → 200
https://agent.2notasudi.com.br        → 404   ← gateway ainda quebrado
```

Instância Evolution (`VERIFIED_LIVE`, 02/09/2026):

```
name:             cartorio-agent
connectionStatus: open
profileName:      Cartório 2 Ofício de Notas de Uberlândia
Message: 10.111   Contact: 2.105   Chat: 276
```

> **O agente está no ar, conectado ao número oficial do cartório, e já processou 10.111 mensagens com 2.105 contatos reais.**
> Isso não é mais piloto. É atendimento ao público, sob a saudação "em fase de testes" que o próprio Felipe redigiu em 10/08.

Nós tailnet relevantes: `cartorio` (100.99.172.84, **idle**), `producao` (100.110.127.44, idle), `agent-os` (100.108.167.50, active).

---

## 5. Matriz de requisitos — o que o Felipe pediu × o que existe

### ✅ Entregue e verificado no código

| Pedido do Felipe | Quando | Onde está |
|---|---|---|
| "Não existe unidade complementar, somente a sede" | 28/07 14:04 | `pietra_outbound_guard.py:167` — guarda de saída com texto canônico |
| "Victor Hugo não trabalha mais aqui" | 28/07 14:05 | `pietra_outbound_guard.py:154` — regex `_FALSE_CURRENT_MEMBER_RE` |
| "Está passando o valor total sem o ISS de 5%" | 03/08 17:12 | `emolumento_operacional_balcao.py` — R$ 11,61 (com ISS + RECOMPE), consumido por `cartorio_agent.py:28` |
| Tabela de balcão 2026 completa | 12/08 13:35 | `GENERAL_ITEMS` bate item a item com a tabela do Felipe |
| Validação humana obrigatória em dúvida | manual, 12/08 | `HITL_REQUIRED` em atos compostos/financeiros |
| Saudação "em fase de testes", sem emoji no corpo | 10/08 17:24 | Ativa em produção |
| Chatbot não pode se apresentar como tabelião | manual, 12/08 | Perfil público guardado (`test_cartorio_agent_public_profile.py`) |

### ⛔ Pedido explicitamente e **ausente do código**

| Lacuna | Quando o Felipe pediu | Impacto |
|---|---|---|
| **CNTV/MG — R$ 5,00** na transferência veicular. Reconhecimento de firma em DUT/ATPV = **R$ 16,61**, não R$ 11,61 | 12/08 13:35 (item 5 da tabela) + Módulo 3.9 do manual | `grep -ri cntv` no repo só acha `docs/supabase/llms-full.txt`. **O agente cobra R$ 11,61 num ato que custa R$ 16,61** — erro de preço a menor num atendimento ao público |
| **Atendimento por ordem de chegada**, sem pré-agendamento | 12/08 13:36 | Não existe no prompt nem no planner. O agente ainda oferece agendamento (`agendamento_cache.py`, `agendamento_metrics.py`) num cartório que **não agenda** |
| **Senha preferencial: idoso, autista, advogado, PCD** | 12/08 13:36 | Zero ocorrências fora de artefatos de teste |
| **Xerox R$ 1,80 (1 face) / R$ 3,60 (2 faces)** e regra de obrigatoriedade na abertura de firma | 12/08 13:35 (item 6) | Não localizado na camada operacional |
| **Manual Completo de Treinamento do Chatbot** (10 módulos, `.docx`, 12/08 14:18) | 12/08 | **`grep -ri "MANUAL COMPLETO DE TREINAMENTO"` no repo inteiro: 0 resultados.** O documento de requisitos mais completo que o cliente produziu nunca foi ingerido na base |
| **Erros de grafia/acentuação** ("animas", "proceeder", "situaçoes") | 11/08 10:52 | Só há instrução em prompt (`pietra.py:494`, ela mesma escrita sem acentos). Nenhuma normalização/validação de saída |
| Relatório de logs de proteção de dados **para enviar ao CNJ** | 17/07 16:11 | Existe `lgpd_relatorio.py`, mas não há evidência de export no formato CNJ |

---

## 6. Pendências relacionais em aberto

1. **Felipe está sem acesso ao chat desde 25/08.** Ele confirmou *"Não está"* às 16:07; Gustavo respondeu às 18:14 *"Vou ver o que aconteceu"* — e não voltou ao assunto.
2. **Mensagem não respondida.** 01/09 09:11 Felipe: *"Bom dia"*. Última interação do fio. **Há ~33 horas sem resposta.**
3. **Gustavo continua como `reader` no MiniMax.** Pedido de admin feito em 22/07 18:46 (*"Ficou faltando dar administrador"*) e **nunca atendido**. Sem admin não dá para criar chaves, endpoints ou rotacionar nada — dependência de 42 dias.
4. **Visita presencial pendente.** Felipe ofereceu duas vezes (03/08 e 17/08, "qualquer dia depois das 17h"). Sem data marcada.
5. **Nota fiscal** não emitida (ver §3).
6. **Exportação de e-mails do setor de procuração** nunca concluída — Felipe tentou em 24/06 e falhou; o plano B (AnyDesk / máquina aberta à noite, 06/07) nunca foi executado.

---

## 7. Segredos que trafegaram em texto claro no WhatsApp

**Nada foi rotacionado — por determinação explícita do Gustavo (02/09).** Registro apenas para rastreabilidade:

| Item | Data | Origem |
|---|---|---|
| Credenciais Hostinger do Felipe (2 strings) | 19/06 14:16 | Felipe → Gustavo |
| Senha do webmail `atendimento@2notasudi.com.br` | 20/07 13:57 | Gustavo → Felipe |
| **API key MiniMax** (`sk-cp-f0TQ1...`) | 22/07 18:46 | Felipe → Gustavo |
| **Token Evolution API** (`429683C4...`) + URL do manager | 07/08 15:38 | Gustavo → Felipe |
| CPF do Djalma | 17/06 16:32 | Felipe → Gustavo |

Observação factual, sem ação: o token Evolution ainda é válido — foi usado nesta análise para consultar o estado da instância. O backup do WhatsApp do Mac não é criptografado em repouso, então essas cinco credenciais também vivem em claro no `ChatStorage.sqlite`.

---

## 8. Leitura do relacionamento

O Felipe é **o melhor cliente-parceiro do portfólio**: escreve requisito estruturado (o manual de 10 módulos é melhor que a maioria das specs internas), testa de graça, absorve a política do titular e ainda protege o fornecedor (*"fica tranquilo"*, *"tá tudo bem"*, *"desculpa o sumiço"*). Ele nunca cobrou prazo uma única vez em 109 dias.

O gargalo **não é técnico e não é o Felipe** — é a mesma falha estrutural já catalogada com a Flávia: mensagens do cliente que não viram tarefa. O padrão se repete três vezes aqui:

1. O manual de 12/08 — o insumo mais valioso do projeto — nunca entrou no repositório.
2. O acesso dele está bloqueado há 8 dias sem follow-up.
3. Um "Bom dia" de ontem segue sem resposta.

Enquanto isso, **o agente atende 2.105 contatos reais** com pelo menos um erro de preço conhecido (CNTV) e regras de fila que contrariam o funcionamento do balcão.

---

## 9. Ordem de ataque sugerida

**P0 — hoje**
1. Responder o Felipe. Depois desbloquear o canal dele (aberto desde 25/08).
2. Corrigir CNTV: reconhecimento de firma em DUT/ATPV = R$ 16,61 (R$ 11,61 + R$ 5,00 repasse CNB/MG, que não é emolumento).

**P1 — esta semana**
3. Ingerir o *Manual Completo de Treinamento* (12/08) na base de conhecimento — é a spec do cliente.
4. Remover/condicionar a oferta de agendamento; fixar "ordem de chegada" + senha preferencial (idoso, autista, advogado, PCD).
5. Adicionar xerox R$ 1,80 / R$ 3,60 à camada operacional.
6. Cobrar o admin do MiniMax (42 dias em aberto).

**P2**
7. Normalização de acentuação na saída + teste de regressão com as frases que o Felipe reportou.
8. Consertar `agent.2notasudi.com.br` (404).
9. Marcar a visita presencial e emitir a NF.

---

*Relatório gerado por análise direta das fontes. Itens marcados `VERIFIED_LIVE` têm comando e saída registrados na sessão de 02/09/2026.*
