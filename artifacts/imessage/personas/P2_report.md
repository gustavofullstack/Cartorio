# P2 — Relatório de Avaliação (João Pedro "JP", intercâmbio urgente)

Data: 2026-07-28 | Chat ID: 364

## (a) O atendente entendeu minhas gírias?

Sim, muito bem. Respondeu "Blz!", espelhou o "kkkk", usou tom jovem e descontraído ("CALMA lá kkk", "tranquilão", "corre aí!"). Entendeu "intercâmbio", "prazo de uma semana", "autenticar cópia" sem precisar de explicação. Nesse quesito foi excelente — adaptou o registro ao meu.

## (b) Foi humano ou robótico?

Misto. O tom era bem humano e empático (espelhamento de gírias, empatia com a ansiedade, dica proativa sobre tradução juramentada do histórico — um toque realmente humano e útil). MAS os vazamentos quebraram totalmente a ilusão: caracteres chineses e russo no meio do texto, e mensagens de sistema em inglês ("⚡ Interrupting current task...") enviadas como se fossem mensagens do atendente. Ninguém humano mandaria isso.

## (c) Respondeu preço/urgência/endereço?

- **Preço:** sim, completo — R$ 11,21/folha, estimativa total R$ 22-33 pro meu caso.
- **Urgência:** sim — confirmou que 1 semana dá tempo, que fica pronto em minutos, e citou até serviço de urgência com +50% (numa resposta misturada).
- **Endereço/horário:** sim, repetido 3x — Rua Cel. Antônio Alves Pereira, 850, Centro (+ unidade Machado de Assis, 685), seg-sex 9h-17h, dica de chegar antes das 16h.
- **Agendamento:** sim — não precisa, ordem de chegada.
- **O que levar:** respondido (original + cópia), mas minha pergunta específica "as cópias eu levo prontas ou vocês tiram aí?" ficou SEM resposta — a mais prática das minhas dúvidas.

## (d) Algo estranho/errado?

Bastante coisa:
1. **Chinês no meio do português** na minha própria conversa: "então，大概 R$ 22-33" (id 4124). E no histórico recente do chat: russo ("есть") e frases inteiras em chinês repetidas 3x (ids 4116, 4118, 4120).
2. **Mensagens de sistema vazadas pro cliente**: "⚡ Interrupting current task. I'll respond to your message shortly." — 4 vezes durante a sessão (ids 4127, 4137, 4145, 4148). Em inglês, expondo a arquitetura de bot/filas.
3. **Contaminação cruzada de conversas**: o número estava atendendo várias personas ao mesmo tempo e o atendente misturou os assuntos — me desejou "Boa sorte com a matrícula do seu filho!" (id 4130), assunto de outra pessoa. Eu tenho 21 anos e falei de intercâmbio, não de filho.
4. **Mensagens ignoradas**: minhas 2 últimas mensagens (pergunta sobre cópias e despedida) ficaram sem resposta porque o atendente estava priorizando outras conversas no mesmo chat.
5. Pequenas falhas de formatação (espaço solto no início de parágrafo, id 4136) e typo "vizigo" no histórico (id 4118).

## (e) Notas

- **Humanidade: 5/10** — o tom textual seria 8-9, mas os vazamentos (chinês/russo/mensagens de sistema em inglês) e a mistura de contextos entregam que é máquina.
- **Utilidade: 7/10** — preço, endereço, horário, agendamento e documentos necessários todos respondidos com riqueza (incluindo dica proativa de tradução); perdeu pontos por deixar minha pergunta prática sobre as cópias sem resposta e pela despedida ignorada.

## 3 sugestões

1. **Sanitizar o output antes de enviar**: bloquear qualquer caractere não-latino (chinês/russo) e mensagens de sistema ("Interrupting current task") — isso destrói a credibilidade instantaneamente.
2. **Isolar contexto por conversa**: o modelo misturou assuntos de clientes diferentes no mesmo número ("matrícula do seu filho" pra um universitário de 21 anos). Se múltiplos atendimentos compartilham o canal, o contexto precisa ser estritamente por thread/remetente.
3. **Garantir resposta a toda mensagem do cliente**: duas mensagens minhas ficaram 90s+ sem resposta enquanto o atendente respondia outros. Fila única com prioridade por ordem de chegada, ou ao menos um "só um minutinho" humano, evitaria a sensação de abandono — crítico pra alguém com prazo urgente.
