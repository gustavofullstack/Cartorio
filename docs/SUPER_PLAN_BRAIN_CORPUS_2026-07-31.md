# Super Plano — Brain Corpus

**Data:** 2026-07-31
**Estado:** pipeline local implementado (ingest+classify+lifecycle+HITL+cálculo);
corpus classificado em `PENDING_HUMAN_VALIDATION`; **não certificado para T4 ou T5**.
Hermes/prod intocados. Ver `docs/BRAIN_PIPELINE_CONHECIMENTO.md`.

## Objetivo

Incorporar conhecimento institucional aprovado ao BRAIN de forma rastreável, reversível e
LGPD-by-design, para que respostas informativas sejam fundamentadas em fontes internas
aprovadas. O corpus permanece privado; esta iniciativa não altera Hermes nem qualquer
componente de produção.

## Estado factual de partida

- Extração privada concluída: 90 fontes, total de 17.505.807 B.
- Varredura antimalware (AV): **PASS**, 0 itens infectados.
- Grok 4.5 está preparado como líder de revisão; Kimi está preparado localmente.
- AGY já existia e será preservado, sem substituição ou tomada de controle.
- Gemini 3.6 Flash está indisponível e não é dependência de entrega.
- Nenhum dado bruto foi enviado a serviços externos.
- Schema e pipeline permanecem em revisão; portanto T4 e T5 não podem ser declarados.

## Princípios não negociáveis

1. **Privacidade primeiro:** conteúdo bruto, identificadores, credenciais e segredos não saem
   do ambiente privado. Somente metadados mínimos, hashes e resultados sanitizados podem entrar
   na trilha de evidências.
2. **Menor privilégio:** leitores, validadores, indexadores e publicadores recebem permissões
   separadas e temporárias, restritas ao estágio necessário.
3. **HITL obrigatório:** classificação jurídica, aprovação de publicação, respostas com efeito
   jurídico e exceções exigem aprovação humana registrada.
4. **Audit append-only:** cada transição, decisão, rejeição, publicação e rollback gera evento
   encadeado, com ator, motivo, versão e referência de integridade.
5. **Fail closed:** na ausência de aprovação, integridade, classificação ou evidência de
   segurança, o item não avança nem é recuperável por respostas do BRAIN.
6. **Separação de ambientes:** ingestão e revisão acontecem fora do caminho de atendimento;
   promoção é explícita, versionada e reversível.

## Arquitetura-alvo: ConhecimentoInstitucional

`ConhecimentoInstitucional` é o registro lógico e versionado do conteúdo aprovado, sem expor
o conteúdo bruto fora do repositório privado de origem. Cada versão contém, no mínimo:

- identificador opaco; origem e classificação institucional; hash de integridade;
- versão, status de ciclo de vida, data de retenção e motivo de decisão;
- resultado de antimalware, detecção de PII e sanitização;
- vínculo com revisões humana, jurídica/LGPD e operacional;
- referências de audit e de indexação, sem conteúdo sensível no log;
- escopo de uso permitido, precedência, vigência e condição de revogação.

Os componentes são: cofre privado de origem; área de quarentena; serviços de inspeção e
normalização locais; registro de revisão/HITL; índice de recuperação restrito a versões
publicadas; camada BRAIN que só consulta conteúdo publicado; e trilha de auditoria imutável.
Nenhum componente de consulta pode ler diretamente a quarentena ou versões não publicadas.

## Fluxo de ciclo de vida

```text
QUARANTINED
  -> INSPECTED (integridade e AV aprovados)
  -> CLASSIFIED (tipo, vigência, PII e escopo definidos)
  -> SANITIZED (PII removida/mascarada quando aplicável)
  -> REVIEW_PENDING
  -> APPROVED (HITL institucional + jurídico/LGPD conforme risco)
  -> INDEXED (índice privado, versionado e isolado)
  -> PUBLISHED (único estado elegível para recuperação no BRAIN)

Qualquer falha -> REJECTED ou QUARANTINED; publicação revogada -> WITHDRAWN.
```

Transições são unidirecionais por padrão. Reprocessamento cria nova versão; não edita histórico.
`WITHDRAWN` remove a elegibilidade de recuperação imediatamente e preserva a evidência de audit.

## Gates T0–T5

| Gate | Evidência mínima de aceite | Estado |
|---|---|---|
| T0 — escopo | finalidade, dados permitidos, retenção, donos e limites aprovados | parcial (plano + docs pipeline) |
| T1 — integridade | inventário opaco, hash, AV limpo e acesso privado verificados | parcial: AV PASS; 90/90 extract; 3083 units |
| T2 — privacidade | classificação de PII, sanitização e prova de que nenhum raw sai externamente | parcial: scrub ingest + classificador bloqueia CPF bruto |
| T3 — controle | schema, RBAC, audit append-only, HITL e flags revisados com testes | parcial: lifecycle/HITL/cálculo + 40 testes; sign-off LGPD pendente |
| T4 — integração controlada | ingestão/indexação em ambiente isolado, rollback exercitado e recuperação somente PUBLISHED | **não declarado** |
| T5 — operação | consulta real autorizada, resposta segura no mesmo canal, monitoramento e evidência humana | **não declarado** |

T4 não decorre de testes unitários ou de catálogo saudável. T5 exige evidência de ponta a ponta
no canal autorizado; sem isso, o sistema permanece não operacional para este corpus.

## Metas, tarefas, donos, dependências e aceite

| Meta | Tarefa | Dono primário | Dependências | Aceite |
|---|---|---|---|---|
| M1: governança | Definir contrato `ConhecimentoInstitucional` e máquina de estados | @Codex | T0, revisão @Terra | schema versionado, transições fail-closed e decisão registrada |
| M2: segurança | Formalizar inspeção, classificação e sanitização locais | @Terra | M1, parecer @Grok | testes com amostras sintéticas e bloqueio de PII/raw externo |
| M3: revisão | Implementar fila HITL e aprovações por risco | @Grok | M1, política LGPD | dupla aprovação quando aplicável e audit encadeado |
| M4: indexação | Indexar apenas versões APPROVED em ambiente isolado | @Kimi | M1–M3, feature flags | recuperação rejeita estados não publicados |
| M5: publicação | Promover, revogar e reverter versões sem mutação histórica | @Codex | M1–M4, AGY preservado | exercício de rollback e rastreabilidade completa |
| M6: certificação | Executar gates T0–T5 e tribunal de evidências | @AGY (coordenação) | M1–M5, autorização operacional | T4/T5 somente após evidência correspondente |

## Matriz PII, HITL e audit

| Etapa | PII | HITL | Audit obrigatório |
|---|---|---|---|
| Quarentena e inspeção | bloquear acesso não autorizado; não exportar raw | não para AV/integridade automática | entrada, hash, resultado AV e ator/sistema |
| Classificação e sanitização | detectar, minimizar e mascarar antes de qualquer uso subsequente | revisão humana para ambiguidade ou risco | categoria, decisão, regra e versão |
| Aprovação | somente conteúdo sanitizado e metadados mínimos na interface de revisão | obrigatório para publicação; jurídico/LGPD quando aplicável | aprovador, escopo, motivo, horário e integridade |
| Indexação | índice privado; sem logs de trechos sensíveis | aprovação prévia obrigatória | versão indexada, configuração e resultado |
| Consulta BRAIN | recuperar somente PUBLISHED; não registrar conteúdo sensível | obrigatório para efeito jurídico ou exceção | versão consultada, política aplicada e decisão |
| Revogação/rollback | remover elegibilidade, preservar evidência mínima | autorização humana | motivo, versões afetadas e confirmação |

## Estratégia de testes

- Unitários: máquina de estados, validação de schema, RBAC, flags e bloqueios fail-closed.
- Segurança: hash/integridade, AV, PII sintética, mascaramento em três camadas e ausência de raw
  em logs, eventos ou chamadas externas.
- Integração isolada: ingestão, revisão, indexação, consulta apenas de `PUBLISHED` e revogação.
- Regressão: tentativa de pular estado, editar evento de audit, re-publicar revogado e usar versão
  não aprovada deve falhar.
- Operação: somente após autorização, canário com conteúdo sintético, observabilidade sanitizada e
  confirmação humana no canal autorizado. Não usar essa etapa para declarar T5 antecipadamente.

## Flags e rollback

As flags devem iniciar desligadas, ter escopo por ambiente e default fail-closed: habilitar
ingestão, habilitar indexação, habilitar recuperação e habilitar publicação. A habilitação de
consulta depende de T4 aceito; a operação em canal depende de T5 aceito.

Rollback é imediato e sem apagar a trilha: desligar recuperação/publicação, marcar a versão como
`WITHDRAWN`, retirar seu índice ativo e restaurar a última versão publicada aprovada. Não há
reprocessamento automático, mutação retroativa de audit ou alteração de Hermes/produção.

## Rastreabilidade de agentes

| Agente | Papel | Evidência esperada | Limite |
|---|---|---|---|
| @Codex | contrato, plano, promoção e rollback | diff revisável, testes e decisão de release | não publica sem gates |
| @Terra | arquitetura, schema e segurança de dados | revisão de isolamento, RBAC e PII | não envia raw externamente |
| @Grok | liderança de revisão e qualidade | parecer de risco, HITL e critérios de aceite | não substitui aprovação humana |
| @Kimi | execução local assistida e testes | resultados locais sanitizados | sem acesso/publicação externa por padrão |
| @AGY | coordenação preexistente | consolidação de dependências e evidências | preservado; sem takeover ou mudança de runtime |

## Critério de conclusão

O plano só é concluído quando as tarefas M1–M6 tiverem evidências sanitizadas, revisões
requeridas e gates aprovados. Até lá, o estado correto é: corpus privado inspecionado, pipeline e
schema em revisão, sem T4/T5 e sem alteração de Hermes ou produção.

---

Assinatura: **@Codex/super_plano**
