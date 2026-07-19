# CD quality gate

O workflow `.github/workflows/cd.yml` é acionado somente pelo evento
`workflow_run` de uma execução `CI` concluída com sucesso após um `push` em
`master`. O gate testa o mesmo `head_sha` validado pelo CI e não possui trigger
direto de `push` nem despacho manual que possa contornar os gates.

O job de qualidade usa credenciais sintéticas efêmeras e serviços Postgres/Redis
de teste. Elas não são credenciais de produção e não devem ser copiadas para
`.env`, secret managers ou documentação operacional.

## Deploy Render: opt-in e SUI

O job `deploy-render` fica **skip** por padrão. Para uma janela de deploy
aprovada, um operador autorizado deve:

1. concluir e registrar a revisão de `.harness/SUI_CHECKLIST.md`;
2. configurar as variáveis de repositório `RENDER_DEPLOY_ENABLED=true` e
   `SUI_CHECKLIST_APPROVED=true` durante a janela autorizada;
3. acompanhar o workflow e remover/desativar as variáveis ao terminar.

Sem as duas variáveis, uma execução CI verde não dispara deploy. Não há valores
de secrets neste arquivo; `RENDER_API_KEY` continua exclusivamente no secret
manager do GitHub.

## Diagnóstico rápido

- `jobs: []` em runs antigos: eram causados por `needs: CI`, referência inválida
  a um job de outro workflow. O gate agora usa apenas `workflow_run`.
- erro de `Settings`: o valor aceito é `APP_ENV=test`, não `testing`; o CD
  injeta também os valores sintéticos exigidos para `AUDIT_HMAC_KEY` e
  `CARTORIO_API_KEY`.

Modified by Gustavo Almeida
