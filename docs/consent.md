# Termo de Consentimento Livre e Esclarecido — Cartório 2 Notas Uberlândia

**Versão:** 1.0
**Data:** 23 de junho de 2026
**Controlador:** Cartório 2º Ofício de Notas de Uberlândia
**Encarregado de Dados (DPO):** dpo@2notasudi.com.br
**Política de Privacidade completa:** https://2notasudi.com.br/privacidade

> Linguagem simples, conforme exige o **art. 9º da LGPD** ("informação clara, adequada e ostensiva"). Este termo é apresentado como **checkbox obrigatório** na primeira conversa com o chatbot, conforme art. 8º da LGPD.

---

## O que você está concordando (em linguagem simples)

Ao marcar **"Eu li e aceito"** abaixo, você entende e concorda com o seguinte:

### 1. O que vamos coletar

- Seu **nome completo** e **telefone** (que você já nos enviou pelo WhatsApp/Telegram/Web).
- O **conteúdo da sua conversa** com o chatbot (texto, áudio transcrito, descrição de imagens).
- **Dados específicos do ato** que você solicitar (por exemplo: dados das partes de uma procuração, valor do imóvel em uma escritura).
- **Metadados técnicos** (IP, agente do navegador, identificador de sessão) para segurança e auditoria.

### 2. Para que vamos usar

1. **Para te atender** — responder suas dúvidas sobre emolumentos, protocolos, serviços notariais.
2. **Para executar o serviço notarial** que você contratar (escritura, procuração, ata, autenticação).
3. **Para cumprir a lei** — guardar protocolos, documentos e o histórico da conversa pelo prazo legal (Provimento CNJ 74/2018).
4. **Para segurança** — registrar acessos, prevenir fraudes e investigar incidentes.

### 3. Com quem compartilhamos

Apenas quando a lei obriga ou quando for estritamente necessário para te atender:

- **Corregedoria, Receita Federal, Poder Judiciário** — por obrigação legal.
- **OpenAI / Anthropic / Cloudflare / Hostinger / Supabase** — como operadores nossos, sob contrato com cláusulas de proteção de dados. **Importante:** ao conversar com nosso bot, seu texto passa automaticamente por uma etapa que **mascara CPF, RG, CNPJ, telefone, e-mail e cartão** antes de qualquer modelo de linguagem ser chamado.

### 4. Por quanto tempo guardamos

| Dado | Prazo |
|------|-------|
| Sua conversa com o bot (texto) | **365 dias** |
| Áudios e imagens da conversa | **365 dias** |
| Protocolos e documentos notariais | 5 a 20+ anos (obrigação legal) |
| Log de quem acessou o quê | 5 anos (LGPD art. 37) |

Passado o prazo, apagamos ou anonimizamos.

### 5. Seus direitos (LGPD art. 18)

A qualquer momento, você pode:

- **Saber** se temos dados seus e pedir uma cópia.
- **Corrigir** dados errados.
- **Pedir a exclusão** dos dados tratados com base no consentimento.
- **Revogar** este consentimento — basta mandar um "Quero revogar meu consentimento" no chat ou um e-mail para dpo@2notasudi.com.br.
- **Pedir portabilidade** dos seus dados.
- **Reclamar à ANPD** (www.gov.br/anpd) se achar que não respeitamos seus direitos.

**Prazo de resposta:** até 15 dias úteis.

### 6. O que acontece se você não aceitar

Se você marcar **"Não aceito"** ou não marcar nada:

- **Você não conseguirá usar o chatbot** para consultas ou serviços que dependam de tratamento de dados pessoais.
- Você ainda poderá falar diretamente com um escrevente humano pelos nossos canais tradicionais (telefone do cartório, balcão, e-mail).

Não há prejuízo para serviços que não dependam de tratamento de dado pessoal além do necessário (LGPD art. 18 §6º).

### 7. Segurança

Adotamos medidas técnicas e administrativas conformes ao art. 46 da LGPD: criptografia em trânsito e em repouso, **PII scrubbing em 3 camadas** (input, pré-LLM, output), audit log imutável com SHA-256 + HMAC, controle de acesso por menor privilégio, backups diários criptografados.

Em caso de incidente relevante, notificamos você e a ANPD em até 72 horas (LGPD art. 48).

### 8. Revogação do consentimento (LGPD art. 8º §5º)

Você pode revogar este consentimento **a qualquer momento**, sem precisar justificar. A revogação:

- **Não afeta** a licitude do tratamento realizado antes dela.
- **Não impede** o cumprimento de obrigações legais que já tenham se iniciado (ex.: um protocolo aberto continua tramitando).
- **Apaga** conversas e metadados não necessários ao cumprimento de obrigação legal.

**Como revogar:**

1. Pelo próprio chat — responda "Quero revogar meu consentimento".
2. Por e-mail — dpo@2notasudi.com.br
3. Pelo site — https://2notasudi.com.br/dpo

### 9. Mudanças neste termo

Se este termo mudar de forma relevante, vamos pedir seu **novo consentimento** na próxima conversa.

---

## Como apresentar no chatbot (copy para UI)

### Mensagem inicial — exibida antes da primeira interação

```
👋 Olá! Sou o assistente virtual do Cartório 2 Notas Uberlândia.

Antes de continuar, preciso do seu consentimento para tratar seus dados pessoais
(como nome, telefone e o conteúdo da nossa conversa), conforme a Lei Geral de
Proteção de Dados (LGPD).

📄 Política de privacidade completa: https://2notasudi.com.br/privacidade
✉️ Encarregado (DPO): dpo@2notasudi.com.br

☐ Li e aceito a Política de Privacidade e o Termo de Consentimento.
☐ Não aceito — prefiro falar com um escrevente.

[Continuar]  [Falar com escrevente]
```

### Mensagem de confirmação (após aceitar)

```
✅ Obrigado! Seu consentimento foi registrado em [data/hora].

Você pode revogar este consentimento a qualquer momento enviando
"REVOGAR" neste chat ou um e-mail para dpo@2notasudi.com.br.

Em que posso te ajudar?
```

### Mensagem de revogação (após "REVOGAR")

```
🔒 Seu consentimento foi revogado em [data/hora].

Conversas e metadados não obrigatórios por lei serão apagados em até
15 dias úteis. Dados necessários para protocolos em andamento serão
mantidos até o encerramento do ato, conforme obrigação legal
(Provimento CNJ 74/2018).

Se precisar de um serviço, fale diretamente com um escrevente:
📞 (34) XXXX-XXXX  ✉️ atendimento@2notasudi.com.br
```

---

## Versionamento

| Versão | Data | Mudança | Aprovado por |
|--------|------|---------|--------------|
| 1.0 | 23/06/2026 | Versão inicial | DPO + Tabelião |

Modified by Gustavo Almeida