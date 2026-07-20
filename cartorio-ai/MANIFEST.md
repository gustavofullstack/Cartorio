# cartorio-ai · MANIFEST

| Campo | Valor |
|---|---|
| Pacote | `cartorio-ai/` — camada de identidade, memória e governança |
| Projeto | Backend API 2º Serviço Notarial de Uberlândia (Cartório 2º Notas) |
| Dono | Gustavo Almeida |
| Criado | 2026-07-20 (scaffold) · Núcleo preenchido 2026-07-20 (sessão C4 / G9.11–G9.12) |
| Status | **Núcleo completo (15 arquivos)** · Layout estendido pendente (ver `ROADMAP.md`) |
| Tipo | Documentação viva — nenhum código executável |
| Licença/Uso | Interno do serventia; contém referências a dados sensíveis (nunca valores) |

## Escopo do núcleo

Raiz: `AGENTS.md`, `README.md`, `ARCHITECTURE.md`, `MANIFEST.md`, `INDEX.md`, `BOOTSTRAP.md`, `ROADMAP.md`
Domínio: `brain/BRAIN.md`, `identity/SOUL.md`, `identity/IDENTITY.md`,
`planning/GOALS.md`, `planning/TASKS.md`, `memory/MEMORY.md`,
`security/SECURITY.md`, `compliance/CNJ.md`

## Fora de escopo (fase posterior)

Os demais arquivos dos diretórios `agents/`, `autonomy/`, `channels/`, `commands/`, `contracts/`,
`evaluation/`, `events/`, `evolution/`, `governance/`, `guardrails/`, `hooks/`, `integrations/`,
`knowledge/`, `mcp/`, `models/`, `observability/`, `operations/`, `prompts/`, `recovery/`,
`runtimes/`, `skills/`, `tools/`, `workflows/` e os arquivos irmãos não-núcleo dentro de
`brain/`, `identity/`, `planning/`, `memory/`, `security/`, `compliance/` (~400 arquivos).
Detalhes e critérios de promoção em `ROADMAP.md`.

## Dependências de verdade

- `../AGENTS.md`, `../.harness/AGENTS.md` — regras operacionais (vencem em conflito).
- `../SUPER_PLANO_G9_100_TASKS.md` — plano ativo referenciado por `planning/TASKS.md`.
- `../.harness/memory/MEMORY.md` e `../.brain/memory/` — memória de projeto/sessão.
