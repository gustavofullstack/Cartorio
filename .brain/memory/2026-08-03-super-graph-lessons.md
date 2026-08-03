# Lições Aprendidas — Cartório Super Graph Loop (2026-08-03)

1. **[zip-corpus-batch-2026-07-31]**: O ZIP de 90 arquivos possui SHA-256 `ce236ba32b01e11139052867d189ce76ce14bf9d9030d9a24512ebdba2252efb` e corresponde ao batch privado já inventariado; raw corpus não deve entrar no Git.
2. **[knowledge-pipeline-existing-fail-closed]**: Já existe pipeline offline fail-closed para 90 fontes/3.087 unidades; `published_eligible` permanece zero até validação humana.
3. **[price-dual-layer-2026]**: Valores TJMG regulatórios e valores operacionais do balcão são camadas distintas; APIs/tools devem nomear camada, fonte, vigência e componentes.
4. **[operational-price-formula-observed]**: Nas 79 linhas do ZIP, o total operacional fecha como líquido + RECOMPE + fundos + ISS + TFJ. Em 78 linhas o ISS fecha em 5% half-up; o código 1606-3 difere R$0,01 e exige validação. RECOMPE/fundos não são inferidos fora das linhas aprovadas.
5. **[training-means-curated-knowledge-not-raw-finetune]**: Treinamento da Pietra é RAG/fatos PUBLISHED + tools determinísticas + evals; fine-tuning com corpus bruto/PII é proibido sem decisão explícita.
6. **[lark-single-consumer]**: Hermes VPS por WebSocket é o único consumidor Lark de produção; standalone Flask e router alternativo não podem coexistir ativos.
7. **[lark-p2-required]**: Lark só é certificável com `im.message.receive_v1` P2, sem `processor not found`, uma conexão, uma réplica e round-trip no mesmo chat.
8. **[lark-least-privilege-pilot]**: Piloto Lark usa DM e grupo com @, visibilidade nominal e tools read-only aprovadas; sem read-all, anexos/OCR, Drive/Docs/Contacts ou efeitos jurídicos.
9. **[completion-vocabulary]**: Usar estados `UNVERIFIED`/`CONFIGURED`/`TESTED_LOCAL`/`DEPLOYED`/`E2E_VALIDATED`/`CERTIFIED`; nunca chamar de 100% sem todos os gates.
10. **[git-policy-current]**: Seguir regra atual: branch a partir de master, sem push direto, PR e revisão independente; prompts antigos master-only são históricos.

