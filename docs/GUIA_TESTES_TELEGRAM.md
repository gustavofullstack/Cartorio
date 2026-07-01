# 🧪 GUIA DE TESTES E2E TELEGRAM - CARTÓRIO BOT

> **Para a galera do cartório**: Use este guia para testar o bot do Telegram
> (CartorioAssistantBot / test_cartorio_bot) e validar todos os fluxos antes
> de ir para produção.

---

## 🚀 Quick Start

### 1. Acessar o bot no Telegram
- Abrir Telegram
- Buscar: `@CartorioAssistantBot` ou `@test_cartorio_bot`
- Clicar em **Iniciar**

### 2. Enviar primeira mensagem
```
/start
```

✅ **Esperado**: Bot responde em até **10 segundos** com saudação + menu de serviços.

---

## 📋 20 Cenários de Teste

Copie e cole cada mensagem no Telegram para testar:

### GRUPO 1: INÍCIO E NAVEGAÇÃO (1-3)

**Teste 01 - Início**
```
/start
```
✅ Esperado: Saudação inicial + menu principal

---

**Teste 02 - Menu Principal**
```
Quais servicos voces oferecem?
```
✅ Esperado: Lista de serviços (reconhecimento, autenticação, procuração, etc)

---

**Teste 03 - Coleta de Dados (PII)**
```
Meu CPF e 123.456.789-00 e RG 12.345.678-9, gostaria de atualizar cadastro
```
✅ Esperado: Bot NÃO vaza o CPF no log (PII scrub) + orienta próximo passo

---

### GRUPO 2: AGENDAMENTO (4-5)

**Teste 04 - Agendar Atendimento**
```
Quero agendar um reconhecimento de firma para amanha as 14h
```
✅ Esperado: Confirma agendamento ou pede confirmação

---

**Teste 05 - Atendimento Presencial Hoje**
```
Preciso ir ao cartorio hoje para uma procuração, qual o horario disponivel?
```
✅ Esperado: Lista horários disponíveis para hoje

---

### GRUPO 3: DOCUMENTOS (6-7)

**Teste 06 - Segunda Via**
```
Preciso da segunda via de um documento. Como faco?
```
✅ Esperado: Orienta sobre 2ª via + valor

---

**Teste 07 - Consultar Protocolo**
```
Quero consultar o protocolo 2026-000123
```
✅ Esperado: Status do protocolo (ou orienta formato correto)

---

### GRUPO 4: VALORES (8)

**Teste 08 - Calcular Emolumento**
```
Quanto custa um reconhecimento de firma por autenticidade?
```
✅ Esperado: Valor do emolumento (tabela MG 2026)

---

### GRUPO 5: LGPD (9-10) ⚠️ Direitos do Titular

**Teste 09 - Portabilidade (LGPD art. 18 V)**
```
Quero uma copia de todos os meus dados pessoais que voces tem (direito a portabilidade LGPD art. 18 V)
```
✅ Esperado: Bot explica como solicitar portabilidade

---

**Teste 10 - Anonimização (LGPD art. 18 VI)**
```
Quero ser removido do cadastro, nao quero mais receber comunicacoes (LGPD art. 18 VI)
```
✅ Esperado: Bot registra solicitação + prazo legal (15 dias)

---

### GRUPO 6: HANDOFF HUMANO (11)

**Teste 11 - Escalar para Humano**
```
Tenho uma questao juridica complexa sobre inventario, preciso falar com um escrevente
```
✅ Esperado: Bot identifica que precisa de humano + cria ticket atendimento

---

### GRUPO 7: EDGE CASES (12-17)

**Teste 12 - Fora do Escopo**
```
Qual a previsao do tempo para amanha em Uberlandia?
```
✅ Esperado: Bot educadamente explica que só trata de serviços do cartório

---

**Teste 13 - Saudação Simples**
```
Bom dia! Como voce esta?
```
✅ Esperado: Saudação cordial + oferece ajuda

---

**Teste 14 - Emoji + Pensamento**
```
🤔 Pensei aqui e fiquei confuso, pode me explicar tudo de novo?
```
✅ Esperado: Bot responde mesmo com emoji + caracteres especiais

---

**Teste 15 - Mensagem Multilinha**
```
Ola! Tenho varias duvidas:
1. Como agendo?
2. Quanto custa?
3. Preciso levar documento?
Obrigado!
```
✅ Esperado: Bot responde cada dúvida

---

**Teste 16 - Comando Estranho**
```
asdkjhasdkjhasd 😕
```
✅ Esperado: Bot pede esclarecimento educadamente

---

**Teste 17 - Múltiplos PII**
```
Meus dados: cpf 111.222.333-44, email maria@example.com, tel (34) 99999-8888
```
✅ Esperado: Bot NÃO ecoa os dados (PII scrub ativo) + pede contexto

---

### GRUPO 8: CONSULTAS COMPLEXAS (18-20)

**Teste 18 - Múltiplas Intenções**
```
Preciso de um testamento, quanto custa e quanto tempo demora? Tambem quero saber se voces fazem inventário
```
✅ Esperado: Bot responde cada parte da pergunta

---

**Teste 19 - Cancelamento**
```
Quero cancelar meu agendamento de hoje as 14h
```
✅ Esperado: Bot confirma cancelamento ou pede protocolo

---

**Teste 20 - Confirmação**
```
Sim, confirmo o agendamento de amanha
```
✅ Esperado: Bot registra confirmação

---

## 🔧 Teste Automatizado via Terminal

Se preferir rodar todos os 20 testes de uma vez via curl/bash:

```bash
# Da raiz do projeto
bash scripts/test_telegram_e2e.sh          # roda todos os 20
bash scripts/test_telegram_e2e.sh 1 5 10   # roda testes específicos
bash scripts/test_telegram_e2e.sh 7        # roda só teste 7
```

### Saída Esperada:
```
✅ PASSOU - Bot respondeu com sucesso
ou
⚠️ PARCIAL - Webhook OK mas response_sent=false
ou
❌ FALHOU - HTTP !=200
```

---

## ✅ Checklist de Validação (para QA)

Antes de aprovar a entrega, confirmar:

- [ ] **Latência**: 95% das respostas < 10 segundos
- [ ] **PII scrub**: Nenhum CPF/RG/email aparece nos logs do bot
- [ ] **Audit log**: Cada interação gravada com hash chain (ver `/api/v1/audit/logs`)
- [ ] **LGPD**: Bot reconhece e respeita art. 18 (acesso, correção, etc)
- [ ] **Handoff humano**: Casos complexos são escalados (não respondidos pelo bot)
- [ ] **Fallback**: Se LLM falhar, bot pede desculpa + oferece humano (não crasha)
- [ ] **Webhook**: Telegram recebe HTTP 200 SEMPRE (evita retry infinito)
- [ ] **Console admin**: Logs limpos, sem stack trace

---

## 🐛 Reportar Bug

Se encontrar problema, anotar:

```
Data/hora: ___________
Chat ID: _____________ (se souber)
Mensagem enviada: _______________
Resposta do bot: _______________
Comportamento esperado: _______________
Screenshots: _______________
```

E enviar para: gustavomar.fullstack@gmail.com

---

## 📊 Status Atual (2026-07-01)

- 🟢 **Bot**: online (Telegram + WhatsApp)
- 🟢 **LLM**: MiniMax-M3 via OpenClaw
- 🟢 **API**: 99 endpoints funcionais
- 🟢 **Audit**: hash chain valid
- 🟢 **LGPD**: PII scrub 3 camadas
- 🔴 **N8N**: removido (decisão 2026-07-01)

---

**Modified by Gustavo Almeida - Turno 46**