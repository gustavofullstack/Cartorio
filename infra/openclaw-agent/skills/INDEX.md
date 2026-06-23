# Cartório Bot - Skills Index

Skills disponíveis para o OpenClaw Agent (CartorioBot).

## Skills ativas

| Skill | Categoria | Quando usar | Endpoints API |
|-------|-----------|-------------|---------------|
| [cartorio-saudacoes.md](cartorio-saudacoes.md) | Atendimento | Primeira mensagem do cliente | (nenhum) |
| [cartorio-protocolo-tracker.md](cartorio-protocolo-tracker.md) | Consulta | Cliente pergunta status de protocolo | `GET /api/v1/protocolo/{numero}` |
| [cartorio-emolumento-calc.md](cartorio-emolumento-calc.md) | Consulta | Cliente pergunta valor de emolumento | `GET /api/v1/emolumento/calcular` |

## Skills futuras (planejadas Sprint 3.5+)

- `cartorio-agendamento` - agendar atendimento no cartório
- `cartorio-segunda-via` - emitir segunda via de documento
- `cartorio-handoff-trigger` - detectar quando escalar para humano

## Como adicionar uma nova skill

1. Criar `skills/cartorio-{nome}.md`
2. Adicionar entrada na tabela acima
3. Atualizar `cartorio-saudacoes.md` (opcional) para mencionar a nova skill
4. Adicionar tests em `backend/tests/test_skills_integration.py` (opcional)

## Convenção de nomenclatura

- Arquivo: `cartorio-{verb}-{object}.md` (kebab-case)
- Header H1: "Cartório Bot - {Descrição Curta}"
- Endpoint API: sempre documentado com exemplo curl
- LGPD: secao obrigatoria em toda skill que acessa API
- Cache: TTL documentado (in-memory, sem persistencia)
