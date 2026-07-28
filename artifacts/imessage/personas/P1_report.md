# Relatório P1 — Avaliação do atendimento (persona: Maria José, 72 anos)

## Avaliação qualitativa

**(a) Foi humano/caloroso com uma senhora de 72 anos?**
Sim, na maior parte do tempo. O atendente usou o nome dela, acolheu a insegurança ("com calma, sem pressa", "não fica aflita"), recusou a ideia de incômodo ("Que isso, não incomoda nada") e encerrou com afeto ("Um abraço bem apertado de volta! :)"). O tom foi adequado e empático para um idoso. Porém, as mensagens de sistema "⚡ Interrupting current task..." quebraram totalmente a ilusão de atendimento humano — para uma senhora real seria confuso e frio.

**(b) Formal adequado?**
Sim, formal na medida: respeitoso sem ser engessado, com linguagem simples e estrutura em bullets que ajuda quem tem dificuldade. Pequeno deslize: "te ajudar" em vez de "ajudá-la" e o emoji no final — aceitáveis, mas um cartório real tenderia a um pouco mais de formalidade.

**(c) Resolveu a dúvida?**
Parcialmente. Identificou corretamente a solução (notário itinerante / atendimento em domicílio), listou documentos necessários (RG/CNH + documento do INSS) e deu canais de contato (2 telefones + WhatsApp) com horário. Falhas: (1) nunca respondeu objetivamente sobre o custo da visita — a pergunta da taxa foi feita duas vezes e ficou sem valor; (2) desviou o agendamento para ligação telefônica em vez de resolver no próprio canal; (3) a resposta sobre urgência/emolumento (id 4104) respondeu a uma pergunta que Maria José não fez (mensagem fantasma do sistema), criando confusão.

**(d) Algo robótico/estranho/errado/frio?**
- Mensagens "⚡ Interrupting current task. I'll respond to your message shortly." em inglês, expondo que é um bot — grave.
- Mensagens automáticas enviadas em nome do cliente ("Quais documentos devo apresentar?", "Qual o emolumento para uma ata de aproximadamente três folhas?") — o sistema "falou pela cliente", bizarro e potencialmente assustador para um idoso.
- Typo "airi" na mensagem id 4088 ("— airi, o cartório vai até ela") — parece glitch de geração.
- Resposta a pergunta inexistente (urgência/50% de acréscimo) gerada a partir da mensagem fantasma.
- A dúvida sobre taxa/custo nunca foi respondida com valor, apenas "o escrevente passa quando ligar".

## Notas

- **Humanidade: 7/10** — Tom caloroso e empático, mas vazamentos de sistema ("Interrupting current task", quick-replies automáticas, typo "airi") derrubam a ilusão e seriam desconcertantes para um idoso real.
- **Utilidade: 6/10** — Solução correta identificada e documentos esclarecidos, mas não resolveu no canal (empurrou para telefone), não informou custo, e gerou ruído respondendo pergunta que não foi feita.

## 3 sugestões de melhoria

1. **Eliminar vazamentos de sistema:** nunca enviar mensagens técnicas ("⚡ Interrupting current task...") nem quick-replies automáticas em nome do cliente; manter apenas respostas redigidas do atendente.
2. **Responder perguntas de custo diretamente:** manter tabela de emolumentos (incluindo taxa de deslocamento do notário itinerante) acessível ao atendente para dar valor ou faixa de valor, essencial para idosos/aposentados se programarem.
3. **Resolver no próprio canal:** oferecer o agendamento da visita domiciliar diretamente pelo iMessage/WhatsApp (coletar endereço e preferência de horário) em vez de redirecionar para ligação — canal escrito é justamente o preferido de quem tem dificuldade com tecnologia ou mobilidade.
