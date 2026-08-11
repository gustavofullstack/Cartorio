# Lesson 303 — Pietra WhatsApp piloto: allowlist Felipe+Gustavo + fatos oficiais

Data: 2026-08-11
Reins: cartorio-dev, cartorio-lgpd, cartorio-n8n
Status: codigo na branch `fix/pietra-whatsapp-p0-audit-20260811`

## Sintoma

Felipe Pizarro reportou erros em producao (texto, valores, agendamento, identidade).
O bot estava aberto ao publico. `APP_ENV=test` na VPS faria qualquer ACL baseada
em ambiente falhar aberta. `CARTORIO_AGENT_MODEL=MiniMax-M2.7-HighSpeed` (glitches).
Canned/templates ainda diziam 08h e sabado.

## Fix

- Allowlist HMAC com piloto embutido: `+5534998807228` (Felipe) e
  `+5534992800250` (Gustavo). `restrict_inbound=true` + hashes vazios = so esses
  dois. `APP_ENV` nao governa a ACL.
- Normalizacao E.164 aceita 10/11/12/13 digitos e LID via `remoteJidAlt`.
- Slot de agenda: rejeita sabado/domingo, 08h e horario passado; HITL/DRAFT.
- Guardrail de horario oficial 09h-17h seg-sex; canned/templates alinhados.
- Endereco oficial nos templates (Rua Cel. Antonio Alves Pereira, 850).

## Producao observada (SSH, so leitura de estado)

- `cartorio_system-api` 1/1 atende `api.2notasudi.com.br`. `cartorio_api` 0/1.
- WhatsApp `cartorio-agent` session `open`. Evolution = `cartorio_whatsapp-api`.
- Allowlist **ainda nao estava no container** ate o deploy desta branch.
- OpenClaw e Chatwoot offline no radar (amarelo).

## Nao fazer

- Nao reabrir o bot com `APP_ENV=test` ou `restrict_inbound=false` em producao.
- Nao commitar hashes HMAC, chaves ou senhas de inspect.
- Nao trocar MiniMax-M3 de volta para HighSpeed no canal do cliente.
- HITL permanece: protocolo DRAFT, agenda so apos escrevente.
