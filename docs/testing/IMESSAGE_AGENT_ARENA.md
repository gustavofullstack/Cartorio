# Cartório OS — iMessage Agent Arena

Este harness prepara uma Arena controlada de seis agentes para homologar o Cartório OS. Ele não
inicia um cliente Spectrum, não lê segredos e não envia mensagens. O runtime canônico do Cartório
continua sendo Hermes profile `cartorio` com o sidecar Photon; iniciar `services/spectrum-gateway`
contra o mesmo projeto é proibido, pois criaria um segundo consumidor.

## Pré-condições para qualquer envio real

1. Registrar as seis linhas no console do provider e manter secrets exclusivamente nos runtimes
   individuais.
2. Confirmar a allowlist para cada rota 1:1. Linhas shared/test podem bloquear mensagens de
   usuários não cadastrados.
3. Criar o grupo manualmente a partir de um humano autorizado e enviar a primeira mensagem.
4. Confirmar que o plano do provider suporta o fluxo de grupo. Uma limitação do plano deve ser
   registrada como `BLOCKED_PROVIDER_PLAN`, jamais contornada.
5. Definir um operador com kill switch antes de qualquer bateria com mais de uma mensagem.

## Proteções obrigatórias

- Mensagem do próprio remetente: `SELF_MESSAGE` e nenhum envio.
- Mesmo `messageId` dentro de 60 segundos: `DUPLICATE` e nenhum envio.
- Uma pessoa por vez: `SPEAKER_LOCK`.
- Cooldown padrão de 1.500 ms.
- Limites padrão por cenário: 12 turnos e 8 hops.
- Mesmo payload três vezes ou sete alternâncias entre o mesmo par: `LOOP_DETECTED` e parada.

`ArenaRunner` é a única fronteira permitida para uma futura integração de envio. Ele consulta o
coordenador antes do transporte e registra somente hashes de payload e provider-message-id. Nenhum
runtime Hermes tester deve ser ativado como autoresponder da Arena até usar uma integração que
respeite essa fronteira.

## Ordem de execução

1. Usar `buildDirectedEdges()` para verificar as 30 rotas sem self-edge.
2. Validar cada rota individualmente, com uma única mensagem e confirmação humana de entrega.
3. Executar os seis testes de self-loop/deduplicação em ambiente controlado.
4. Fazer bootstrap do grupo, se suportado.
5. Subir gradualmente: 20 turnos, 100 turnos, depois 1.000 turnos controlados.

O catálogo offline tem exatamente 100 cenários (20 categorias para cada um dos cinco testers),
gerado por `buildCartorioScenarioCatalog()`. Ele não é evidência de execução: cada cenário só
vira resultado após outbound autorizado, inbound observado e confirmação de entrega.

Nenhum resultado de matriz deve ser marcado como `PASS` só porque o processo está conectado; cada
aresta precisa de inbound, execução e entrega observados.
