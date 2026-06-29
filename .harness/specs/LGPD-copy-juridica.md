# LGPD Copy Jurídica — Templates para D27 (Consentimento) + D31 (Revogação)

> **Para**: cartorio-dev (implementar) + cartorio-n8n (plug em WhatsApp/Telegram)
> **De**: cartorio-lgpd (Pietra) — área jurídica
> **Base**: Lei 13.709/2018 + Provimento 74/2018 CNJ
> **DPO contact**: dpo@2notasudi.com.br

## Regra de ferro

Toda resposta LGPD ao titular DEVE conter:
1. **Base legal específica** (art. + inciso + parágrafo)
2. **Direito de revogação** (art. 8º §5º)
3. **DPO contact** (dpo@2notasudi.com.br)
4. **Como remediar** (próximo passo concreto)
5. **Linguagem simples** (LGPD art. 9º — "informação clara e adequada")

---

## D27 — Copy para `POST /api/v1/lgpd/consent`

### Response JSON (campo `copy_juridica`)

```json
{
  "copy_juridica": {
    "base_legal": "LGPD art. 7º I + art. 8º",
    "direito_revocacao": "Você pode revogar este consentimento a qualquer momento, sem ônus, via este canal ou pelo e-mail dpo@2notasudi.com.br (LGPD art. 8º §5º).",
    "dpo_contact": "dpo@2notasudi.com.br",
    "finalidade_registrada": "<FINALIDADE>",
    "como_remediar": "Para exercer outros direitos (acesso, correção, portabilidade, eliminação), envie mensagem ao DPO."
  }
}
```

### Mensagem WhatsApp/Telegram (quando cliente responde "SIM" via chat)

```
✅ Consentimento registrado

O que você acabou de aceitar:
→ Finalidade: {{finalidade}}
→ Canal: {{canal}}
→ Data: {{data_hora}}

Base legal: Lei 13.709/2018 (LGPD), art. 7º, inciso I, combinado com art. 8º.

Você pode revogar este consentimento a qualquer momento, sem custos.
Como revogar:
• Responda "REVOGAR" neste chat
• E-mail: dpo@2notasudi.com.br
• Portal: https://cartorio.local/revogar

Para outros direitos (acesso, correção, portabilidade, eliminação), fale com nosso Encarregado de Dados (DPO):
📧 dpo@2notasudi.com.br

2º Tabelionato de Notas e Protesto de Uberlândia
```

### Mensagem WhatsApp/Telegram (quando cliente responde "NÃO")

```
❌ Consentimento NÃO registrado

Você optou por não consentir com: {{finalidade}}.

Sem problemas! Você pode:
• Revisar esta decisão a qualquer momento
• Continuar usando os serviços cartorários obrigatórios (escritura, procuração, certidão) que têm base legal própria (Provimento 74 CNJ)
• Falar com nosso DPO: dpo@2notasudi.com.br

Base legal: LGPD art. 7º I (consentimento é livre e pode ser negado sem prejuízo aos serviços obrigatórios).
```

---

## D31 — Copy para `POST /api/v1/lgpd/revogar-consent`

### Response JSON (campo `copy_juridica`)

```json
{
  "copy_juridica": {
    "base_legal": "LGPD art. 18, inciso IX + art. 8º §5º",
    "efeito": "Sua revogação foi aplicada AGORA. Os seguintes processamentos foram parados: {{processamentos_parados}}. Os serviços cartorários obrigatórios (escritura, certidão) continuam funcionando pois têm base legal de obrigação legal (LGPD art. 7º II + Provimento 74 CNJ).",
    "direito_anonimizacao": "Se você deseja também a eliminação dos seus dados pessoais, exerça o direito do art. 18, VI via endpoint D28 ou solicite ao DPO.",
    "dpo_contact": "dpo@2notasudi.com.br",
    "como_remediar": "Para reativar qualquer finalidade, basta consentir novamente via D27."
  }
}
```

### Mensagem WhatsApp/Telegram (revogação "TODAS")

```
🛑 Consentimento revogado

Você revogou TODOS os consentimentos opcionais em {{data_hora}}.

O que isso significa:
→ Marketing e prospecção: PARADOS
→ Compartilhamento com terceiros: PARADO
→ Analytics: PARADO
→ Atendimento cartorário: MANTIDO (obrigação legal — Provimento 74 CNJ)
→ Seus protocolos lavrados: PRESERVADOS por 5 anos (obrigação legal)

Base legal: LGPD art. 18, IX (revogação a qualquer momento) + art. 8º §5º (sem ônus).

Quer eliminar também seus dados pessoais?
→ Responda "ESQUECER" ou "EXCLUIR" para exercer art. 18, VI
→ Ou solicite ao DPO: dpo@2notasudi.com.br

Mudou de ideia? Você pode reativar finalidades a qualquer momento respondendo "QUERO CONSENTIR".

Encarregado de Dados (DPO):
📧 dpo@2notasudi.com.br

2º Tabelionato de Notas e Protesto de Uberlândia
```

### Mensagem WhatsApp/Telegram (revogação específica — ex: só marketing)

```
🛑 Consentimento revogado para: MARKETING

Você revogou apenas o consentimento de marketing. Outras finalidades (atendimento, etc.) continuam ativas.

Base legal: LGPD art. 18, IX.

Para revogar outras finalidades ou TODAS, responda:
• "REVOGAR MARKETING"
• "REVOGAR ANALYTICS"
• "REVOGAR TODAS"
• "ESQUECER" (para eliminação completa)

DPO: dpo@2notasudi.com.br
```

---

## D28 — Copy para `DELETE /api/v1/lgpd/cliente/{id}`

### Response JSON (campo `copy_juridica`)

```json
{
  "copy_juridica": {
    "base_legal": "LGPD art. 18, VI + art. 16",
    "tipo_aplicado": "<soft | hard>",
    "retencao_minima_legal": "{{#if soft}}Você possui {{N}} protocolos lavrados. Estes registros são mantidos por 5 anos conforme Provimento 74/2018 CNJ. Após esse prazo, serão anonimizados também. O hash do seu CPF permanece para fins de integridade do histórico jurídico. {{/if}}{{#if hard}}Todos os seus dados foram eliminados. Como você não possui protocolos lavrados, não há retenção legal obrigatória. {{/if}}",
    "dpo_contact": "dpo@2notasudi.com.br",
    "como_remediar": "Em caso de dúvida ou para reversão (apenas DPO + ferramenta dedicada, conforme art. 18, VI §3º), contate o DPO."
  }
}
```

### Mensagem WhatsApp/Telegram (anonimização aplicada)

```
✅ Direito de eliminação aplicado

Tipo: {{soft|hard}}
Data: {{data_hora}}

O que fizemos:
{{#if soft}}
→ Seu nome, email e telefone foram removidos do cadastro ativo
→ Seu CPF foi substituído por hash interno
→ {{N}} protocolos lavrados foram PRESERVADOS (obrigação legal — 5 anos, Provimento 74 CNJ)
{{/if}}
{{#if hard}}
→ Todos os seus dados foram eliminados
{{/if}}

Base legal: LGPD art. 18, VI (eliminação) + art. 16 (minimização).

Para dúvidas ou reversão: dpo@2notasudi.com.br

2º Tabelionato de Notas e Protesto de Uberlândia
```

---

## D29 — Copy para `GET /api/v1/lgpd/export/{cliente_id}`

### Mensagem WhatsApp/Telegram (após export gerado)

```
📦 Exportação de dados pronta

Você solicitou a portabilidade dos seus dados (LGPD art. 18, V).

Download: {{link_download}}
Validade: 90 dias
Formato: JSON estruturado (LGPD art. 19)
Integridade: SHA-256 verificado

Hash do arquivo: {{export_hash}}
Tamanho: {{tamanho_bytes}} bytes

⚠️ Este link contém dados pessoais. Não compartilhe.

DPO: dpo@2notasudi.com.br

2º Tabelionato de Notas e Protesto de Uberlândia
```

---

## D30 — Copy para `POST /api/v1/lgpd/correct/{cliente_id}`

### Mensagem WhatsApp/Telegram (após correção)

```
✅ Dados corrigidos

Você alterou {{N}} campos:
{{#each campos_alterados}}
• {{campo}}
{{/each}}

Data: {{data_hora}}

Base legal: LGPD art. 18, III.

As alterações foram registradas em nosso log de auditoria (LGPD art. 37) com os hashes anterior e posterior, sem exposição dos valores.

DPO: dpo@2notasudi.com.br

2º Tabelionato de Notas e Protesto de Uberlândia
```

---

## D32 — Copy para `GET /api/v1/lgpd/audit/{cliente_id}`

### Mensagem WhatsApp/Telegram (resumo da transparência)

```
📊 Histórico de tratamento dos seus dados

Período: {{periodo_inicio}} a {{periodo_fim}}
Total de eventos registrados: {{total_eventos}}

Categorias:
• Consentimentos: {{consentimentos}}
• Atendimentos: {{atendimentos}}
• Protocolos: {{protocolos}}
• Anonimizações: {{anonimizacoes}}
• Exports: {{exports}}

Sub-processadores com quem compartilhamos dados:
{{#each sub_processadores}}
• {{nome}} ({{pais}}) — DPA: {{dpa_status}}
{{/each}}

Para o detalhamento completo, acesse seu portal ou solicite ao DPO: dpo@2notasudi.com.br

Base legal: LGPD art. 18, VII + art. 37.

2º Tabelionato de Notas e Protesto de Uberlândia
```

---

## LGPDBlockedResponse (genérico, para uso em N8N)

Quando o bot detecta bloqueio regulatório (consent ausente, IP bloqueado, suspeita de fraude, etc):

```
⚠️ Não foi possível processar sua solicitação

Motivo: {{motivo_legal}}
Base legal: {{art_lgpd}}

Para resolver:
• {{como_remediar_1}}
• {{como_remediar_2}}

Encarregado de Dados (DPO):
📧 dpo@2notasudi.com.br

Status: 422 (precondição semântica/regulatória)
```

**NÃO usar 400 (sintaxe) nem 403 (permissão) nem 412 (precondição HTTP) — usar SEMPRE 422 para bloqueios regulatórios LGPD.**

---

## Validações (copy jurídica em PR review)

cartorio-lgpd verifica em TODO endpoint novo que toca dado pessoal:

- [ ] Base legal citada (art. + inciso + parágrafo)?
- [ ] DPO contact visível (dpo@2notasudi.com.br)?
- [ ] Direito de revogação comunicado (art. 8º §5º)?
- [ ] Linguagem simples (LGPD art. 9º)?
- [ ] Finalidade específica (não genérica)?
- [ ] Status code correto (422 para LGPDBlocked)?
- [ ] Mensagem WhatsApp/Telegram formatada sem MarkdownV2 com `\\.` (aprender com Gustavo: vai texto puro)?

Modified by cartorio-lgpd (Pietra root mvs_97612f6bb1824cbdaf7c134fa34bf057)