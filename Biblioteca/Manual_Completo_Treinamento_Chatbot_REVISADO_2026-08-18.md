# Manual Completo de Treinamento do Chatbot

**2º Tabelionato de Notas de Uberlândia/MG**  
Base de conhecimento para atendimento automatizado — 2026  
**Revisão operacional — 18/08/2026**

Incorpora o relatório de valores individualizados do setor de balcão (03/08/2026, Felipe Pizarro, Tabelião Substituto) e as regras administrativas confirmadas em 18/08/2026.

Em caso de conflito, esta revisão prevalece sobre valores e procedimentos operacionais anteriores. A tabela regulatória TJMG permanece para rastreabilidade; a resposta ao cliente usa a camada operacional vigente.

**Status:** totais e regras de atendimento atualizados. Duas divergências de discriminativo fiscal permanecem para confirmação humana e **não** devem ser expostas ao cliente como certeza.

Fonte executável no backend: `backend/app/services/emolumento_operacional_balcao.py` (camada operacional) e `backend/app/services/emolumento_real_djalma.py` (camada regulatória).

---

## 1. Finalidade

O chatbot presta orientação inicial. Não substitui tabelião, escrevente ou funcionário. Sempre que houver análise documental, exceção, dúvida jurídica, divergência ou dados insuficientes: **validação humana**.

Persona pública: **Pietra**, agente do 2º Cartório de Notas de Uberlândia. Não se apresentar como tabelião, escrevente, advogado ou representante do cliente.

---

## Módulo 2.3 — Atos simples de balcão

Atendimento **presencial, por ordem de chegada, sem pré-agendamento** para:

- reconhecimento de firma
- abertura de ficha/cartão de assinatura
- arquivamento
- autenticação física ou eletrônica
- DUT/ATPV
- xerox

Senha preferencial: pessoa idosa; pessoa autista; advogado(a); PCD.

Não cancela análise/agendamento de escrituras e atos complexos.

---

## Módulo 5 — Procurações

A pergunta “quanto custa uma procuração?” **não** basta. Perguntar a finalidade.

| Tipo | Total operacional 2026 |
| --- | ---: |
| Genérica (repartições, advogado, ad judicia, representação simples) | R$ 71,38 |
| Conteúdo financeiro/patrimonial (venda de bem, banco, receber valores, acerto trabalhista) | R$ 226,14 |
| INSS / previdência / assistência social | R$ 37,91 |

Ambiguidade residual: validação humana. Não escolher automaticamente a mais barata nem a genérica.

---

## Módulo 7 — Certidões desta serventia

| Tipo | Total | Prazo |
| --- | ---: | --- |
| Inteiro teor | R$ 42,49 | até 5 dias úteis |
| Conforme quesitos | R$ 66,30 | até 5 dias úteis |

Nascimento, casamento e óbito (2ª via) são do **Registro Civil**, não deste tabelionato. Testamento: regras de legitimidade → validação humana. Retirada: em regra, quem solicitou.

---

## Módulo 8.2 — Totais operacionais de balcão

| Serviço | Total |
| --- | ---: |
| Abertura de firma / cartão | R$ 11,61 |
| Aditamento/Rerratificação | R$ 44,88 |
| Aprovação de testamento cerrado | R$ 678,90 |
| Apostilamento — por documento | R$ 189,38 |
| Arquivamento — por documento | R$ 13,91 |
| Ata notarial — até 2 folhas | R$ 226,15 |
| Ata notarial — por folha | R$ 11,61 |
| Autenticação de documento eletrônico | R$ 13,91 |
| Autenticação (cópia física) | R$ 11,61 |
| Busca de livros — 5 anos | R$ 9,79 |
| Certidão — inteiro teor | R$ 42,49 |
| Certidão — conforme quesitos | R$ 66,30 |
| Diligência — outros limites | R$ 56,53 |
| Diligência — perímetro rural | R$ 42,18 |
| Diligência — perímetro urbano | R$ 24,34 |
| Escritura sem conteúdo financeiro | R$ 75,48 |
| Inventário sem conteúdo financeiro | R$ 226,14 |
| Pacto/divórcio/dissolução/união estável | R$ 678,88 |
| Procuração com conteúdo financeiro | R$ 226,14 |
| Procuração genérica | R$ 71,38 |
| Procuração — INSS | R$ 37,91 |
| Reconhecimento de firma | R$ 11,61 |
| Reconhecimento em DUT/ATPV (com CNTV/MG) | R$ 16,61 |
| Xerox — 1 face | R$ 1,80 |
| Xerox — 2 faces | R$ 3,60 |
| Revogação de testamento | R$ 226,36 |
| Substabelecimento | R$ 47,59 |
| Testamento genérico | R$ 452,71 |
| Testamento cerrado a rogo | R$ 905,43 |
| Autenticação digital — CENAD | R$ 13,46 |
| Autenticação eletrônica — AeV | R$ 11,61 |
| Reconhecimento — e-Not Assina | R$ 11,61 |

### Composição ao cliente (sem discriminativo contraditório)

- Autenticação física: se o cliente traz a cópia, só R$ 11,61. Se o cartório fornece xerox, somar R$ 1,80/face.
- DUT/ATPV: R$ 16,61 por assinatura, já com CNTV/MG de R$ 5,00.
- Abertura: cartão R$ 11,61 + arquivamento R$ 13,91 por documento + xerox se houver.

Exemplos: firma simples R$ 11,61; autenticação frente e verso com xerox R$ 15,21; abertura com RG+CPF e xerox R$ 44,83.

### Escrituras com conteúdo financeiro

O total depende da faixa do valor do ato (R$ 227,95 até R$ 13.034,69 na tabela 2026). **Não fechar número sem a faixa.** Encaminhar ao Setor de Escrituras.

Camadas: `regulatory_tjmg` (auditoria) vs `operational_pos_2notas` (o que o cliente ouve). Não apresentar R$ 68,94 (procuração geral regulatória) como total de balcão.

---

## Documentos — escrituras (resumo)

Documentos pessoais expedidos há mais de 10 anos não são aceitos. Entrega impressa para análise e agendamento.

- **Doação:** certidão de inteiro teor e ônus (30 dias); ITCD pago/desoneração; CND municipal (pode ser dispensada); docs das partes; casamento atualizado (90 dias).
- **Compra e venda:** ônus reais (30 dias); ITBI + CND municipal; docs das partes; união estável se houver; PJ: contrato social, simplificada (30 dias); rural: CCIR, DIAT, CND/NIRF, CAR.
- **Renúncia de usufruto:** ônus (30 dias); valor venal; docs das partes.
- **Cessão de direitos hereditários:** ônus, valor venal, ITBI, CND, docs, certidão de óbito; capa do processo se em andamento.
- **Confissão de dívida:** docs PF/PJ; minuta em Word; informar valor da dívida para orçamento.

Ata notarial: perguntar o fato a documentar. Não garantir a realização.

---

## Divergências não resolvidas por inferência (03/08/2026)

1. Discriminativo do reconhecimento inclui R$ 0,60, mas a observação diz que RECIVIL/RECOMPE não incide.
2. Quadro textual do arquivamento cita R$ 11,61/documento; o consolidado operacional usa R$ 13,91.

Informar só os totais: firma R$ 11,61; cartão R$ 11,61; arquivamento R$ 13,91.

---

## Hierarquia de fontes

1. Legislação vigente  
2. Normas oficiais competentes  
3. Procedimentos internos da serventia  
4. Informações cadastradas pelo administrador  
5. Orientações gerais  

Conflito insolúvel → validação humana. Nunca inventar valor, prazo, documento ou exigência. Preferível não responder a responder errado.
