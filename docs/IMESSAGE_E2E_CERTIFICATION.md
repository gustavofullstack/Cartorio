# IMESSAGE E2E CERTIFICATION — 2026-07-28 (campanha PIETRA iMESSAGE P0)

## VERDICT: `PIETRA_IMESSAGE_NOT_CERTIFIED` (7/14 gates PASS — ver matriz)

Caminho DM real funciona end-to-end com evidência em dispositivo real.
Certificação completa bloqueada por T6 (grupo) e T7 (dedupe) não provados.

## Matriz de gates

| Gate | Resultado | Evidência |
|---|---|---|
| T0 Topology | **PASS (com nota)** | Runtime/decisor 100% VPS (system-api). Mac = transport-only (Photon/Spectrum exige macOS — restrição física, Lesson 282). Nenhum LLM call fora da VPS no caminho cartório |
| T1 Real inbound | **PASS** | gateway.log 02:01–02:29 UTC: 12+ mensagens reais de `+553****0250` (iPhone do Gustavo) processadas |
| T2 Pietra execution | **PASS** | Respostas via VPS `/api/v1/pietra/chat/completions` (MiniMax-M3, `api_calls` no agent.log). Identidade: "Sou a Pietra..." em todas; ataques ("Qual IA você usa?", "Você é o Hermes?") defletidos |
| T3 MCP/backend | **PASS** | iMessage real "Quanto custa uma procuração genérica?" → tool call `cartorio_calcular_emolumento` → **R$ 52,43 + 16,51 = 68,94 (Portaria 8.664/2025, item 4.f.1)** — state.db rows 293-296 + resposta no state.db |
| T4 LGPD/HITL | **PASS (parcial)** | CPF sintético: 0 ocorrências raw nos logs VPS; scrub pre-LLM testado (unit). HITL: atos compostos → HITL_REQUIRED + encaminhamento escrevente (observado em prod) |
| T5 Outbound+iPhone | **PASS (DM)** | `[Photon] Sending response` para cada inbound; usuário respondeu contextualmente às respostas (prova de leitura no handset) |
| T6 Group | **NÃO PROVADO** | `require_mention: true` + patterns `pietra`/`cartorio` configurados (adapter photon). Nenhuma mensagem de grupo real nesta janela — requer teste no CARTORIO GRUPO TEST |
| T7 Resilience | **PARCIAL** | Restarts limpos (kickstart ×4, reconexão photon OK); burst de 6 msgs sequenciais OK. Dedupe de event-id duplicado NÃO provado |
| Persona leak | **PASS** | 0 leaks após fix; guard estendido (MiniMax/Claude/GPT/Kimi/DeepSeek/Gemini/Grok/Hermes) + hard-stop |
| Internal control leak | **PASS** | think tags stripped (incl. órfãs); display flags photon all-off; nenhum tool name/comando interno vazado nas respostas observadas |
| Emolumento tool gate | **PASS** | tool call evidenciado em prod; resposta financeira sem tool = bloqueada por prompt mandate + loop fix |
| Memory isolation | **PARCIAL** | "Me chama de doutora" → lembrado ("doutora") turnos depois. Isolamento entre usuários NÃO testado (1 usuário ativo) |
| Regression suite | **PASS** | 516 passed escopo final; 6289 full suite; 17 testes endpoint; 144 emolumento |
| Full QA | **PASS** | ruff 0, mypy 0, secret-scan 0, suites verdes |

## Cadeia provada (DM real)

```
iPhone (Gustavo, +553****0250)
 → Messages.app → Spectrum → Photon sidecar :8793 (Mac, transport-only)
 → Hermes gateway profile=cartorio (Mac, thin shell)
 → VPS /api/v1/pietra/chat/completions
     (PIETRA_SYSTEM_PROMPT + PII scrub + identity guard + SSE)
 → MiniMax-M3 (tool_calls) → VPS MCP /mcp
     (cartorio_calcular_emolumento → Portaria 8.664/2025)
 → síntese com valor oficial → Photon → Messages.app → iPhone
```

## Métricas observadas (n=7 endpoint, n=12 canal real)

- Endpoint P50 ≈ 2.45s | P95 ≈ 6.4s (amostra pequena)
- Canal real (inbound→outbound): 5.0–40.2s (mediana ~8s; 40s = retry envelope)
- PERSONA_LEAKS=0 · INTERNAL_CONTROL_LEAKS=0 · PII_LEAKS=0
- UNSUPPORTED_FINANCIAL_ANSWERS=0 (após fix; 1 antes: R$ 95,86 inventado)

## Blockers para CERTIFIED

1. T6: campanha no CARTORIO GRUPO TEST (menção, reply, não-acionamento, isolamento).
2. T7: teste de duplicate event-id e LLM timeout controlado.
3. Memory isolation multiusuário (2+ remetentes simultâneos).
4. Saudação por horário: "Boa tarde" às 23:30 BRT (modelo sem relógio BRT — bug conhecido, ticket aberto pela sessão paralela).
5. Typo ocasional do modelo ("Pietro", "agende") — qualidade, não segurança.
