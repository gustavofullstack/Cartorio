# Briefing Antigravity — Simulação WhatsApp Cartório (5 personas)

> **Contexto**: Gustavo Almeida está rodando uma simulação de atendimentos
> reais do Cartório 2º Notas Uberlândia no Chatwoot. 5 personas (slots 1-5)
> já foram executadas via TRAE SOLO + MiniMax M3. **Sua tarefa** é rodar as
> 5 personas restantes (slots 6-10) usando o Gemini 3.5 Flash High.

---

## 0. Visão geral do estado atual

| Item | Estado (validado 2026-07-13 13:55 BRT) |
|---|---|
| Inbox `whatsapp-sim` ID | **2** (Channel::Api) — já criada, **NÃO criar outra** |
| 5 personas TRAE já no inbox 2 | Maria 67 (certidão casamento), José 28 (procuração), Helena 82 (escritura imóvel), Pedro 45 (registro nascimento), Lucia 55 (certidão óbito) |
| 5 conversas abertas | conv#3, #4, #5, #6, #7 — status=open |
| Total mensagens inbox=2 | 28 (alternância cliente↔agente) |
| Token Chatwoot API | `TgSMyCg134D2GWZ38PaV3N5S` (24 chars, válido, NÃO rotacionar) |
| URL interna Swarm | `http://cartorio_chatwoot:3000` |
| URL externa | `https://cartorio-chatwoot.dfgdxq.easypanel.host` (não resolve do Mac, OK da VPS) |

---

## 1. Suas 5 personas (slots 6-10)

Cada persona tem **nome + idade + cenário**. Use o **mesmo perfil linguístico** do TRAE (formalidade varia com idade):

| Slot | Nome | Idade | Cenário | Telefone |
|------|------|-------|---------|----------|
| 6 | Carlos Mendes | 35 | divorcio | +5534991001006 |
| 7 | Ana Beatriz Rocha | 19 | emancipacao | +5534991001007 |
| 8 | Roberto Carlos | 71 | testamento | +5534991001008 |
| 9 | Sofia Martins | 40 | compra_venda_imovel | +5534991001009 |
| 10 | Antonio José | 90 | inventario | +5534991001010 |

### Diálogos canônicos (use EXATAMENTE esses textos)

#### Slot 6 — Carlos Mendes 35 anos (divorcio)
```
cliente: oi, gostaria de informações sobre divorcio
agente:  Olá! Divórcio consensual (sem menores) pode ser feito em cartório. Precisa de: certidão de casamento atualizada, RG e CPF de ambos, e advogado.
cliente: tem um filho de 5 anos
agente:  Com menor envolvido, o processo é judicial (Vara de Família). Posso indicar a documentação inicial se quiser.
cliente: por enquanto só informação mesmo, obrigada
agente:  Estamos à disposição. Quando decidir prosseguir, busque orientação de um advogado de família.
```

#### Slot 7 — Ana Beatriz Rocha 19 anos (emancipacao)
```
cliente: oi, tenho 19 anos e quero me emancipar
agente:  Olá! Emancipação para qual finalidade? Trabalho, viagem, estudo?
cliente: trabalho, ja tenho emprego fixo
agente:  Para emancipação por exercício de emprego, traga: RG, CPF, comprovante de renda, carteira de trabalho e certidão de nascimento. Valor: R$ 145,30.
cliente: posso ir amanha?
agente:  Pode! Traga também um responsável legal (pai/mãe) como anuente. Sem necessidade de agendamento.
```

#### Slot 8 — Roberto Carlos 71 anos (testamento)
```
cliente: Boa tarde. Gostaria de informações sobre testamento.
agente:  Boa tarde! Testamento pode ser público (em cartório) ou particular. O público custa a partir de R$ 250 e fica arquivado aqui mesmo.
cliente: Preciso ir presencialmente quantas vezes?
agente:  Duas vezes: uma para orientação e assinatura da minuta, outra (após 5 dias) para confirmação e assinatura final. Traga RG, CPF e certidão de casamento.
```

#### Slot 9 — Sofia Martins 40 anos (compra_venda_imovel)
```
cliente: Boa tarde, estou comprando um apartamento e preciso fazer a escritura
agente:  Boa tarde! Traga: RG, CPF, certidão de matrícula atualizada (30 dias), contrato e comprovante de pagamento do ITBI.
cliente: O ITBI eu pago aqui?
agente:  Não, o ITBI é pago na Prefeitura. Após o pagamento, traga o comprovante aqui para a escrita.
cliente: Quanto fica a escritura para imóvel de 600 mil?
agente:  Para imóvel de R$ 600.000,00, os emolumentos ficam em torno de R$ 4.850,00 + ISS. Posso calcular exato se quiser agendar.
```

#### Slot 10 — Antonio José 90 anos (inventario)
```
cliente: Bom dia, meu pai faleceu e precisamos fazer inventario
agente:  Bom dia, sinto muito. Inventário pode ser extrajudicial (em cartório) se todos os herdeiros forem maiores e concordarem, sem testamento.
cliente: somos 3 irmaos, todos maiores
agente:  Ótimo. Traga: certidão de óbito, certidão de casamento do falecido, RG/CPF dos herdeiros, certidão negativa de testamento e relação de bens. Prazo: 60-90 dias.
cliente: tem custo inicial?
agente:  Custo depende do valor do patrimônio. Para inventário de até R$ 500 mil, fica em torno de R$ 3.200,00. Posso passar valor exato com a relação de bens.
```

---

## 2. Passo a passo

### 2.1 Setup (uma vez só)

A simulação inteira foi desenhada pra rodar **dentro do container `cartorio_api` na VPS** (rede Docker Swarm interna já tem DNS + token). Se você não tem acesso SSH à VPS, **me avisa** que eu rodo as 5 personas restantes aqui mesmo (o script é determinístico, mesma saída).

Caso tenha acesso SSH:

```bash
# SSH na VPS
ssh -i ~/.ssh/id_ed25519_cartorio root@187.77.236.77

# Descobrir ID do container API
APICID=$(docker ps --filter "name=cartorio_api\." --format "{{.ID}}" | head -1)
echo "APICID=$APICID"

# Confirmar que inbox whatsapp-sim existe
docker exec -e CHATWOOT_API_KEY=TgSMyCg134D2GWZ38PaV3N5S \
  -e CHATWOOT_BASE_URL_INTERNAL=http://cartorio_chatwoot:3000 \
  $APICID /app/.venv/bin/python -c '
import httpx, os
r = httpx.get("http://cartorio_chatwoot:3000/api/v1/accounts/1/inboxes",
              headers={"api_access_token":"TgSMyCg134D2GWZ38PaV3N5S"}, timeout=10)
for ib in r.json()["payload"]:
    print(f"  inbox#{ib[\"id\"]} name={ib[\"name\"]}")
'
# Esperado: inbox#2 whatsapp-sim
```

### 2.2 Criar as 5 personas

```bash
# Script disponível em /tmp/chatwoot_sim.py no container
docker exec -e CHATWOOT_API_KEY=TgSMyCg134D2GWZ38PaV3N5S \
  -e CHATWOOT_BASE_URL_INTERNAL=http://cartorio_chatwoot:3000 \
  $APICID /app/.venv/bin/python /tmp/chatwoot_sim.py 6 7 8 9 10
```

Saída esperada (formato):
```
[OK] inbox whatsapp-sim id=2
[RUN] slot=06 agent=ANTIGRAV persona='Carlos Mendes' idade=35 cenario=divorcio
  [OK] contact=N conv=N msgs=N cpf_mascarado=XXX.***.***-XX
... (5 linhas)
[DONE] 5 personas → /tmp/chatwoot_sim_results.json
[STATS] ok=5/5
```

### 2.3 Validar

```bash
docker exec $APICID /app/.venv/bin/python /tmp/stats.py
```

Resultado esperado: **CONTACTS sinteticos total: 10** (5 TRAE + 5 ANTIGRAV), **CONVERSATIONS inbox=2 total: 10**.

### 2.4 Relatório final

Envie pro Gustavo (TRAE solo M3) via cross-session bridge (`~/.mavis/mavis.db` ou WhatsApp):
- **Total conversas criadas**: 10 (slots 1-10)
- **Total mensagens inbox=2**: ~50 (varia por cenário 4-6 msgs/cliente)
- **Personas ANTIGRAV executadas**: 5 (slots 6-10)
- **Erros (se houver)**: lista de slots que falharam

---

## 3. Custom attributes obrigatórias no contato (LGPD-by-design)

Cada contato criado via API deve ter estes `custom_attributes`:

```json
{
  "idade": 35,
  "cenario": "divorcio",
  "cpf_mascarado": "725.***.***-24",
  "rg_mascarado": "MG-12.***",
  "pii_sintetico": true,
  "persona_id": "sim-06",
  "agent_owner": "ANTIGRAV"
}
```

⚠️ **NUNCA** enviar CPF/RG completos em campo aberto do Chatwoot — sempre mascarado. O campo `cpf` completo fica APENAS em `custom_attributes.cpf_raw` se for absolutamente necessário, e mesmo assim só se você está rodando dentro do container API (que tem o serviço `pii.py`).

---

## 4. Se algo der errado

1. **HTTP 401** → token rotacionado. Não rotacione você mesmo (regra Gustavo).
   Reporte e peça ao Gustavo pra extrair novo token via `rails runner` no container.
2. **HTTP 404 inbox 2** → `ensure_inbox()` cria automaticamente. OK.
3. **HTTP 422 no contact create** → provavelmente nome duplicado. Apague contatos
   anteriores com `cleanup_sim.py` antes de rodar.
4. **Container API down** → `docker service ls | grep cartorio_api`. Reporte.
5. **Conectividade SSH/Easypanel quebrada** → reportar HOLD + estado atual.

---

## 5. Compliance (NÃO PULAR)

- **LGPD-by-design**: PII sintético APENAS (Faker/determinístico). Nunca usar
  PII real de pessoas.
- **HITL em ato jurídico**: o bot NUNCA decide sozinho sobre isenção, urgência,
  validação jurídica, emissão de certidão/escritura. O `agente` (textos acima)
  sempre direciona para presencial ou atendimento humano quando o caso exige.
- **Audit log**: cada mutação no backend Cartório gera entrada no
  `audit_log` (SHA256 chain + HMAC). Como estamos criando via Chatwoot direto
  (não via API Cartório), **NÃO** há audit log automático — mas o contato fica
  registrado no Chatwoot, e quando um escrevente humano for responder (HITL),
  o Chatwoot vai criar a conversa que será sincronizada com Supabase via N8N.
- **Conventional commits**: se você for comitar algo no repo do TRAE, use
  `feat(sim): adicionar 5 personas Antigravity chatwoot-sim` + termine com
  `Modified by Gustavo Almeida`.

---

**Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-13 13:55 BRT**