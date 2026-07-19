# Exportação agregada CNJ — LGPD-safe

O endpoint interno `/api/v1/lgpd/cnj-exports` produz um artefato JSON para revisão e transmissão manual pelo canal institucional autorizado. Ele não envia dados para nenhum serviço externo e não armazena o arquivo gerado.

Fluxo obrigatório:

1. Um DPO autenticado por `X-API-Key` e JWT com `dpo=true` cria o pedido para `YYYY-MM`.
2. Outro DPO, com `sub` distinto, aprova o pedido e justifica a operação.
3. Um DPO gera o pacote local. Cada etapa é registrada em `audit_log` sem a justificativa nem dados de titulares.

O relatório contém somente contagens agregadas, estado da cadeia de auditoria e controles de segurança. São expressamente excluídos nomes, CPF/CNPJ, e-mails, telefones, endereços, IPs, mensagens, documentos, payloads de auditoria e IDs de titulares.

O pacote tem `report_sha256` e `manifest_sha256`, calculados sobre JSON canônico. Antes da transmissão institucional, o DPO deve conferir esses hashes, a validade da cadeia, a finalidade e a aprovação de quatro olhos. Uma cadeia inválida exige investigação: o artefato não deve ser enviado.

Exemplo de sequência de teste:

```text
POST /api/v1/lgpd/cnj-exports/requests {"reference_period":"2026-07"}
POST /api/v1/lgpd/cnj-exports/requests/{request_id}/approval {"reason":"Revisão mensal para envio institucional CNJ."}
POST /api/v1/lgpd/cnj-exports/requests/{request_id}/generate
```

Todos os endpoints exigem `X-API-Key` e JWT DPO; em produção também devem permanecer atrás de Tailscale/VPN e das políticas de proxy já vigentes.

## Evidências mínimas antes do envio institucional

O endpoint gera um artefato, não uma autorização regulatória nem transmissão automática. O DPO responsável deve registrar, fora do arquivo exportado, a evidência de que:

1. a migration Alembic está no head que contém as restrições `0024`–`0026`;
2. solicitante e aprovador são titulares distintos do papel DPO;
3. `audit_integrity.chain_valid` é `true` e os hashes do relatório e manifesto foram recalculados de forma independente;
4. o período, finalidade e destinatário institucional foram revisados; e
5. o arquivo foi transmitido manualmente por canal institucional autorizado, sem anexar logs, payloads ou identificadores de titulares.

Se alguma evidência faltar, o pacote deve permanecer retido para investigação. A geração não deve ser repetida: um pedido já gerado é imutável e o sistema retorna conflito para nova geração.
