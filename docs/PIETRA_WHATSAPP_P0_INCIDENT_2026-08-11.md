# Pietra WhatsApp - incidente P0 e tabela operacional 2026

Data: 2026-08-11. Estado: contido; webhook Evolution pausado durante o rollout.

## Correcoes implementadas

- ACL de entrada por HMAC SHA-256, com chave dedicada, dois hashes em secret manager e
  comportamento fail-closed quando a configuracao estiver ausente ou malformada.
- Normalizacao E.164 aceita o JID brasileiro legado sem o nono digito e `remoteJidAlt` para LID.
- Gate executado antes de idempotencia, banco, consentimento, Redis, fila e LLM.
- ACL de saida revalidada em texto, typing e reacao; LID tem binding efemero de 120 segundos.
- Webhook legado desabilitado por padrao. Endpoints de teste/debug exigem API key e o envio de
  teste fica oculto em producao.
- Consentimento deixa de ser automatico: `SIM` concede, `PARAR` revoga e as chaves Redis usam
  pseudonimo HMAC com TTL.
- Respostas acima de 800 caracteres sao enviadas em blocos, sem truncamento silencioso.
- Logs do ingest nao registram telefone/JID, ID da mensagem nem corpo da resposta upstream.
- Routers internos `/brain`, `/pietra` e `/agent-hermes` exigem `X-API-Key`.
- Tabela de balcao virou uma camada operacional separada; a tabela regulatoria TJMG permanece
  imutavel e rastreavel. Atos financeiros continuam HITL.

## Diagnostico operacional

- O canal vivo era Evolution direto para FastAPI; os 39 workflows N8N estavam inativos.
- Chatwoot nao estava implantado e a acao estruturada de handoff nao era consumida.
- Na janela auditada, houve 604 webhooks, 243 eventos aceitos, 120 entradas no pipeline, 92
  respostas, 19 descartes por rate limit e 10 respostas truncadas acima de 800 caracteres.
- O Redis continha chaves de historico e consentimento com identificador bruto; consentimentos
  nao tinham expiracao. Nao havia RAG/graph-summary no caminho real do WhatsApp.
- O workflow de agendamento estava inativo e incorreto: condicao de dados ausentes, deduplicacao,
  HITL e confirmacao eram inalcancaveis ou incompletos. Ele nao deve ser ativado.

## Contencao de agendamento

- Toda solicitacao criada pela API ou webhook nasce com status `draft`; nenhum horario e
  prometido ao cliente antes da decisao humana.
- Apenas uma chamada autenticada de escrevente promove `draft` para `agendado`, com evento
  `agendamento.approved_by_clerk` na auditoria.
- Horarios passados, finais de semana e intervalos fora de 09h-17h no fuso
  `America/Sao_Paulo` sao recusados. Datetime sem offset e interpretado como horario civil local,
  nunca como UTC.
- O endpoint antigo de disponibilidade estatica agora retorna 503 e informa que a validacao deve
  ser humana; ele nao anuncia mais cinco vagas ficticias.
- Os endpoints de criacao, listagem, cancelamento e aprovacao exigem `X-API-Key`. O workflow N8N
  05 permanece inativo e nao deve ser ligado ate ser refeito e testado ponta a ponta.

## Tabela geral operacional de balcao

Valores transcritos e conferidos visualmente no arquivo privado `tabela geral 5_.pdf`.

| Codigo | Natureza | Recompe | Fundos | ISS | Emolumentos | Taxa judiciaria | Total |
|---|---|---:|---:|---:|---:|---:|---:|
| 1502-4 | Abertura de firma | 0,60 | - | 0,40 | 7,95 | 2,66 | **11,61** |
| 1418-3 | Aditamento/rerratificacao | 2,31 | - | 1,53 | 30,67 | 10,37 | **44,88** |
| 1101-5 | Aprovacao de testamento cerrado | 34,92 | - | 23,20 | 463,90 | 156,88 | **678,90** |
| 8310-5 | Apostilamento por documento | 9,74 | - | 6,47 | 129,43 | 43,74 | **189,38** |
| 8101-8 | Arquivamento | 0,72 | - | 0,48 | 9,50 | 3,21 | **13,91** |
| 1202-1 | Ata notarial ate duas folhas | 11,63 | - | 7,73 | 154,55 | 52,24 | **226,15** |
| 1203-9 | Ata notarial por folha | 0,60 | - | 0,40 | 7,95 | 2,66 | **11,61** |
| 1302-9 | Autenticacao de documento eletronico | 0,70 | - | 0,47 | 9,31 | 2,98 | **13,46** |
| 1301-1 | Autenticacao | 0,60 | - | 0,40 | 7,95 | 2,66 | **11,61** |
| 8301-4 | Busca de livros por cinco anos | 0,50 | - | 0,34 | 6,71 | 2,24 | **9,79** |
| 8401-2 | Certidao de inteiro teor | 2,13 | - | 1,41 | 28,23 | 10,72 | **42,49** |
| 8402-0 | Certidao conforme quesitos | 3,72 | - | 2,47 | 49,39 | 10,72 | **66,30** |
| 8503-5 | Diligencia outros limites | 2,91 | - | 1,93 | 38,63 | 13,06 | **56,53** |
| 8502-7 | Diligencia perimetro rural | 2,17 | - | 1,44 | 28,80 | 9,77 | **42,18** |
| 8501-9 | Diligencia perimetro urbano | 1,25 | - | 0,83 | 16,62 | 5,64 | **24,34** |
| 1401-9 | Escritura sem conteudo financeiro | 3,88 | - | 2,58 | 51,57 | 17,45 | **75,48** |
| 1460-5 | Inventario sem conteudo financeiro | 11,63 | - | 7,73 | 154,55 | 52,23 | **226,14** |
| 1477-9 | Pacto, divorcio, dissolucao ou uniao estavel | 34,92 | - | 23,20 | 463,90 | 156,86 | **678,88** |
| 1458-9 | Procuracao com conteudo financeiro | 11,63 | - | 7,73 | 154,55 | 52,23 | **226,14** |
| 1437-3 | Procuracao generica | 3,67 | - | 2,44 | 48,76 | 16,51 | **71,38** |
| 1438-1 | Procuracao INSS | 1,95 | - | 1,30 | 25,91 | 8,75 | **37,91** |
| 1501-6 | Reconhecimento de firma | 0,60 | - | 0,40 | 7,95 | 2,66 | **11,61** |
| 1457-1 | Revogacao de testamento | 11,64 | - | 7,73 | 154,65 | 52,34 | **226,36** |
| 1455-5 | Substabelecimento | 2,45 | - | 1,63 | 32,51 | 11,00 | **47,59** |
| 1456-3 | Testamento generico | 23,28 | - | 15,47 | 309,36 | 104,60 | **452,71** |
| 1459-7 | Testamento cerrado a rogo | 46,57 | - | 30,94 | 618,70 | 209,22 | **905,43** |
| 1697-2 | Autenticacao digital CENAD | 0,70 | - | 0,47 | 9,31 | 2,98 | **13,46** |
| 1698-0 | Autorizacao eletronica de viagem | 0,60 | - | 0,40 | 7,95 | 2,66 | **11,61** |
| 1699-8 | Reconhecimento e-Not Assina | 0,60 | - | 0,40 | 7,95 | 2,66 | **11,61** |

### Cenarios compostos registrados pelo Felipe

Estes totais combinam mais de um ato/insumo e nao substituem o valor unitario da tabela geral.

| Cenario de balcao | Total |
|---|---:|
| Firma simples, uma assinatura | **11,61** |
| Autenticacao mais xerox de duas faces | **15,21** |
| Abertura de firma completa do exemplo (cartao, arquivamentos e xerox) | **44,83** |
| DUT/ATPV, um signatario com consulta | **16,61** |

## Escritura com conteudo financeiro

| Codigo | Faixa | Total |
|---|---:|---:|
| 1402-7 | ate 1.400,00 | 227,95 |
| 1403-5 | ate 2.720,00 | 371,84 |
| 1404-3 | ate 5.440,00 | 538,85 |
| 1405-0 | ate 7.000,00 | 745,98 |
| 1406-8 | ate 14.000,00 | 994,78 |
| 1407-6 | ate 28.000,00 | 1.285,21 |
| 1408-4 | ate 42.000,00 | 1.616,57 |
| 1409-2 | ate 56.000,00 | 1.989,94 |
| 1410-0 | ate 70.000,00 | 2.404,60 |
| 1411-8 | ate 105.000,00 | 3.026,34 |
| 1600-6 | ate 140.000,00 | 3.839,67 |
| 1601-4 | ate 175.000,00 | 4.106,03 |
| 1602-2 | ate 210.000,00 | 4.372,88 |
| 1603-0 | ate 280.000,00 | 4.914,86 |
| 1604-8 | ate 350.000,00 | 5.050,25 |
| 1605-5 | ate 420.000,00 | 5.186,26 |
| 1606-3 | ate 560.000,00 | 5.677,78 |
| 1607-1 | ate 700.000,00 | 5.989,84 |
| 1608-9 | ate 840.000,00 | 6.302,53 |
| 1609-7 | ate 1.120.000,00 | 7.046,73 |
| 1610-5 | ate 1.400.000,00 | 7.632,83 |
| 1611-3 | ate 1.680.000,00 | 8.219,92 |
| 1416-7 | ate 3.200.000,00 | 8.808,22 |
| 1417-5 | ate 3.700.000,00 | 13.034,69 |
| 1612-1 | cada 500.000,00 excedente | 2.254,46 |

## Testamento e alteracao contratual

| Codigos | Faixa | Total |
|---|---:|---:|
| 1419-1 / 1645-1 | ate 1.400,00 | 113,98 |
| 1420-9 / 1646-9 | ate 2.720,00 | 185,92 |
| 1421-7 / 1647-7 | ate 5.440,00 | 269,42 |
| 1422-5 / 1648-5 | ate 7.000,00 | 372,99 |
| 1423-3 / 1649-3 | ate 14.000,00 | 497,38 |
| 1424-1 / 1650-1 | ate 28.000,00 | 642,60 |
| 1425-8 / 1651-9 | ate 42.000,00 | 808,28 |
| 1426-6 / 1652-7 | ate 56.000,00 | 994,96 |
| 1427-4 / 1653-5 | ate 70.000,00 | 1.202,31 |
| 1428-2 / 1654-3 | ate 105.000,00 | 1.513,17 |
| 1615-4 / 1655-0 | ate 140.000,00 | 1.919,84 |
| 1616-2 / 1656-8 | ate 175.000,00 | 2.053,01 |
| 1617-0 / 1657-6 | ate 210.000,00 | 2.186,44 |
| 1618-8 / 1658-4 | ate 280.000,00 | 2.457,43 |
| 1619-6 / 1659-2 | ate 350.000,00 | 2.525,13 |
| 1620-4 / 1660-0 | ate 420.000,00 | 2.593,13 |
| 1621-2 / 1661-8 | ate 560.000,00 | 2.838,89 |
| 1622-0 / 1662-6 | ate 700.000,00 | 2.994,92 |
| 1623-8 / 1663-4 | ate 840.000,00 | 3.151,27 |
| 1624-6 / 1664-2 | ate 1.120.000,00 | 3.523,37 |
| 1625-3 / 1665-9 | ate 1.400.000,00 | 3.816,41 |
| 1626-1 / 1666-7 | ate 1.680.000,00 | 4.109,96 |
| 1433-2 / 1667-5 | ate 3.200.000,00 | 4.404,11 |
| 1434-0 / 1668-3 | ate 3.700.000,00 | 6.517,35 |
| 1627-9 / 1669-1 | cada 500.000,00 excedente | 1.127,24 |

## Gates e pendencias

- Unitario/focal: ACL, adapter, consentimento, ingest, HMAC, pipeline, PII e audit.
- Nenhum workflow N8N de WhatsApp/agendamento deve ser ativado no estado atual.
- Handoff real precisa ser restaurado antes de a Pietra afirmar que encaminhou algo.
- A chave SSH exposta no pedido deve ser rotacionada depois de garantir uma segunda via de acesso.
- O aceite final exige round-trip real controlado dos dois contatos autorizados e verificacao de
  que um terceiro sintetico e ignorado antes de qualquer persistencia.
- Agendamento focal: validacao temporal, autenticacao, ciclo `draft` -> `agendado`, webhook,
  cache e metricas cobertos por testes automatizados.
