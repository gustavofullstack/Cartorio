# LLM Provider DPA Matrix (Matriz de Conformidade LGPD)
**2º Serviço Notarial de Uberlândia**

Este documento detalha o acordo de processamento de dados (Data Processing Agreement - DPA) dos 27 modelos/provedores integrados ao ecossistema de inteligência artificial do Cartório, garantindo conformidade com a LGPD e o Provimento 134 do CNJ.

---

## 🛡️ Governança de PII & IA Offline
Para mitigar os riscos de compartilhamento não autorizado de dados pessoais (PII) com APIs de IA públicas (Anthropic, OpenAI, etc.), o Cartório utiliza um modelo local offline **Llama 3.1 8B** rodando na infraestrutura própria (Tailscale VPN):

1. **Filtro Zero-Data**: Qualquer payload recebido é processado localmente pelo modelo Llama 3.1 8B local para identificação e anonimização de dados sensíveis antes de qualquer roteamento externo.
2. **Sem Vazamento**: Dados brutos de CPF, RG, assinaturas e escrituras nunca saem da VPS corporativa sem mascaramento prévio (PII Scrubbing).

---

## 📊 Matriz DPA (27 Modelos × Status DPA)

| ID | Nome do Modelo | Provedor / API | DPA Status | Base Legal / Justificativa |
|---|---|---|---|---|
| 1 | deepseek-v4-flash-free | opencode_free_3 | **SIGNED** | Infra local (DPA com Operador local firmado) |
| 2 | nemotron-3-ultra-free | opencode_free_1 | **SIGNED** | Infra local (DPA com Operador local firmado) |
| 3 | mimo-v2.5-free | opencode_free_2 | **SIGNED** | Infra local (DPA com Operador local firmado) |
| 4 | north-mini-code-free | opencode_free_1 | **SIGNED** | Infra local (DPA com Operador local firmado) |
| 5 | deepseek-v4-flash | opencode_go | **SIGNED** | Infra local (DPA com Operador local firmado) |
| 6 | gpt-5.5 | openclaw | **SIGNED** | Gateway local controlado via Tailscale |
| 7 | claude-sonnet-4.6 | openclaw | **SIGNED** | Gateway local controlado via Tailscale |
| 8 | gemini-3.1-pro-jules | jules | **PENDING** | API Pública (Requer opt-in e mascaramento total) |
| 9 | gemini-3.1-pro-antigravity | antigravity | **SIGNED** | VPN Tailscale + Token de serviço seguro |
| 10 | poolside-laguna-free | openrouter | **PENDING** | API Pública (Uso exclusivo após PII scrub) |
| 11 | north-mini-code-openrouter-free | openrouter | **PENDING** | API Pública (Uso exclusivo após PII scrub) |
| 12 | gemma-4-31b-free | openrouter | **PENDING** | API Pública (Uso exclusivo após PII scrub) |
| 13 | gemini-3.5-flash-free | google_ai_studio | **PENDING** | API Pública Google (Pendente assinatura corporativa) |
| 14 | gemini-3-flash-free | google_ai_studio | **PENDING** | API Pública Google (Pendente assinatura corporativa) |
| 15 | devstral-small | mistral | **PENDING** | API Pública Europeia (Processamento fora do BR) |
| 16 | compound | groq | **PENDING** | API Pública US (Processamento fora do BR) |
| 17 | llama-3.1-8b-local | local | **SIGNED** | Local Offline (Zero tráfego externo, 100% seguro) |
| 18 | gpt-4o | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 19 | gpt-4o-mini | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 20 | claude-3-5-sonnet | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 21 | claude-3-haiku | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 22 | llama-3.1-70b | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 23 | mixtral-8x7b | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 24 | qwen-2.5-72b | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 25 | deepseek-coder | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 26 | phi-3-medium | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 27 | gemma-2-9b | litellm | **PENDING** | Proxy LiteLLM (Pendente DPA com agregadores) |
| 28 | **MiniMax-M3 / M2.7** | **minimax** (LiteLLM / OpenClaw / bot multi-canal) | **READY_TO_SIGN** | Pacote G7.19.T2: `docs/DPA_MINIMAX_READY_TO_SIGN_G7.md` — só inputs **scrubbed** (NO raw CPF). Assinatura SUI Gustavo+DPO+MiniMax; após assinar → **SIGNED** + `LGPD_DPA_MINIMAX_SIGNED=true` |

---

### Status MiniMax (G7 Wave 27)

| Campo | Valor |
|-------|--------|
| DPA package | `docs/DPA_MINIMAX_READY_TO_SIGN_G7.md` |
| Template cláusulas | `docs/lgpd/dpa_minimax_template.md` |
| Status | **READY_TO_SIGN** (não é SIGNED) |
| Finalidade | Inferência LLM bot multi-canal + ops scrubbed |
| Dados | Scrubbed only — **proibido CPF/RG/protocolo raw** |
| Residual | HOLD-GUSTAVO checklist §11 do pacote |

---

## 📈 Regras de Roteamento baseadas em DPA
O orquestrador do Cartório aplica a seguinte heurística de privacidade:
* Se `consentimento_lgpd = False`, o envio ao LLM é abortado imediatamente (Consent Gate).
* Se o payload possui qualquer tag `DATASENSITIVE` (mesmo com consentimento), o roteamento prioriza estritamente os provedores com status **SIGNED** (como o Llama 3.1 local e opencode_go local).
* Modelos com status **PENDING** são acionados apenas como fallback secundário/terciário de dados gerais, nunca para processamento de PII brutas.
* Modelos com status **READY_TO_SIGN** (ex.: MiniMax) podem rodar em homologação / prompts já scrubbed, mas **não** devem ser preferidos para cargas com qualquer risco residual de PII até virarem **SIGNED**. Priorizar Llama local e providers **SIGNED**.

---

**Modified by Gustavo Almeida + cartorio-lgpd — G7 Wave 27 (MiniMax READY_TO_SIGN)**
