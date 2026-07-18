# Auditoria de modificações dos workflows N8N — G8.19.T4

O auditor `scripts/n8n_wf_audit.py` reconcilia os exports locais críticos com o histórico Git. Ele é totalmente offline: não lê `N8N_API_KEY`, não consulta a API do n8n e não executa workflows.

## Como rodar

Na raiz do repositório:

```bash
make n8n-audit
make n8n-audit ARGS="--critical-only"
make n8n-audit ARGS="--since 2026-07-18T00:00:00Z"
make n8n-audit ARGS="--critical-only --output /tmp/n8n-wf-audit.json"
```

O JSON retorna:

- `workflows`: arquivo, ID do n8n (ou `local:<nome>` para templates), SHA256 e threshold;
- `entries`: commit, autor, email, timestamp UTC, assunto, workflow, ID e hash atual;
- `modifications_count`: quantidade de modificações após o filtro `--since`;
- `critical_wfs` e `selected_wfs`: catálogo completo e escopo efetivamente auditado.

Sem flags, o catálogo inclui thresholds `critical` e `high`. `--critical-only` mantém somente `critical`.

## Hash canônico e LGPD

O SHA256 usa o JSON canônico com chaves ordenadas e remove metadados não estruturais do export, como `createdAt`, `updatedAt`, `versionId`, `pinData` e `staticData`. Assim, o hash representa apenas a definição estrutural do workflow.

O hash não recebe payloads de execução, conversas, telefones, CPF, RG, protocolos reais ou documentos. O relatório nunca serializa o conteúdo dos nodes; publica apenas o digest SHA256. Exports devem continuar passando pelo lint anti-PII antes do commit.

O cache `lru_cache` usa `(repo, workflow, HEAD)` como chave e evita repetir `git log --follow` enquanto o input não muda. Um novo commit muda `HEAD` e invalida naturalmente a chave.

## Catálogo crítico

| Grupo | Workflows | Threshold |
|---|---|---|
| Entrada e atendimento | `evo-in`, `01-consulta-emolumento`, `02-criar-protocolo`, `04-boas-vindas-lgpd` | critical |
| PII e LLM | `12-chatbot-llm-end-to-end` | critical |
| Auditoria e LGPD | `08-audit-verify-diario`, `22-audit-verify-6h`, `23-lgpd-esqueci-v2`, `24-retencao-diaria` | critical |
| Atos e documentos | `25-protocolo-concluido-pdf`, `38-emolumento-calculator`, `template-orcamento-escritura` | critical |
| Operação | `00-error-handler` | critical |
| Evidência e saúde | `28-audit-snapshot`, `30-health-deep-check` | high |

Alterar esse catálogo exige revisão de `cartorio-n8n`; qualquer workflow que toque PII também exige revisão de `cartorio-lgpd`.

## Integração com o dead-man's-switch

A integração recomendada é executar `make n8n-audit ARGS="--critical-only --since <ultimo_check> --output <arquivo>"` antes da verificação periódica da cadeia de auditoria. O dead-man's-switch deve:

1. validar exit code zero e JSON parseável;
2. alertar o escrevente e `cartorio-lgpd` quando `modifications_count > 0`;
3. anexar somente IDs, hashes e metadados Git ao evento de auditoria;
4. exigir HITL para aceitar o novo hash como baseline;
5. nunca publicar ou ativar automaticamente um workflow.

Esta task entrega o auditor e o contrato de integração. O agendamento dentro do loop de 15 minutos deve ser feito separadamente pelo owner do dead-man's-switch, preservando a cadeia append-only SHA256 + HMAC.

Modified by Gustavo Almeida — G8.19.T4 (2026-07-18).
