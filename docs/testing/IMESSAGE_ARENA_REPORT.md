# iMessage Agent Arena — Baseline Report

## Status

`UNVERIFIED`. O harness offline foi criado antes de qualquer envio real. A matriz e o grupo não
foram executados.

## Inventário vivo

Somente o runtime Hermes do Cartório está comprovadamente ativo. Os runtimes locais de Kimi, AGY e
Codex não estão em execução; Antigravity e Grok não têm runtime local correspondente comprovado.
Um estado persistido de gateway não substitui `hermes gateway list` e listener do sidecar.

## Evidência necessária para promoção

- 30/30 rotas 1:1 com inbound, execução e entrega ao destinatário.
- 6/6 proteções de self-loop/deduplicação.
- Grupo bootstrapado por humano e validado somente se o plano suportar grupos.
- Zero loops, vazamento de segredo, PII indevida, resposta ao usuário errado ou aprovação jurídica
  sem HITL.

## Próxima ação

Completar allowlists e obter o bootstrap humano. Só então operar a Arena com um coordenador e
kill switch.
