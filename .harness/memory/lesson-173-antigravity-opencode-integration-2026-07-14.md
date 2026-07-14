# Lesson 173 — Integração Antigravity (AGY) no OpenCode (YOLO / All Trust)

## Contexto
O usuário solicitou a integração da IA Antigravity (AGY) nas configurações do OpenCode/OpenCode-Server/OpenCode-Web/OpenCode-Mobile, habilitando múltiplos modelos de ponta com configurações de bypass total de permissão (YOLO, Danger Skip Permission, Bypass Mode On, Always Skip Permission, Root Mode, All Trust), tudo sem desligar, matar processos (kill), remover (rm/rf) ou interromper o serviço em execução.

## Modelos Configurados
*   **Provedor:** `antigravity` (Antigravity (AGY)) via OpenAI-compatible proxy pointing to local listener `127.0.0.1:8805` (defined in plist `com.gustavoalmeida.opencode-bridge.plist`).
*   **Modelos Mapeados:**
    *   `gemini-3.5-flash-high` / `gemini-3.5-flash-medium` / `gemini-3.5-flash-low`
    *   `gemini-3.1-pro-high` / `gemini-3.1-pro-low`
    *   `claude-4.6-opus` / `claude-4.6-sonnet`
    *   `gpt-oss-120b-medium`

## Ações de Implementação
1.  **Configuração Local do Projeto (`opencode.json`):**
    *   Adicionado o bloco `"provider": { "antigravity": { ... } }` contendo todos os 8 modelos mapeados.
    *   Configurado as opções de `baseURL` para `http://127.0.0.1:8805/v1` e `apiKey` de bypass `sk-antigravity-local-bypass-2026`.
    *   Ajustado as permissões locais para permitir tudo de forma transparente (`"*": "allow"`, `"question": "deny"`).
2.  **Configuração Global do OpenCode (`~/.config/opencode/opencode.jsonc`):**
    *   Criado o arquivo global incluindo o plugin `opencode-mobile@latest`, o provedor `antigravity` com todos os seus modelos, e as permissões globais totalmente liberadas (All Trust YOLO mode).
3.  **Configuração das Reins do Harness (`cartorio-dev`, `cartorio-n8n`, `cartorio-lgpd`):**
    *   Inserido o bloco do provedor `antigravity` e seus respectivos modelos em cada um dos arquivos `opencode.json` sob `.harness/reins/*/opencode/opencode.json`.
4.  **Validação de Integridade do Backend:**
    *   Executado o conjunto completo de testes rápidos com `make test-fast`.
    *   **Resultado:** 2626 testes executados e todos passaram com sucesso em 98.86s, confirmando que as modificações de arquivos JSON estáticos não alteraram a estabilidade nem violaram as premissas de execução do backend.

## Gotchas & Práticas Adotadas
*   **Sem Restarts / Kills:** Nenhuma interrupção foi feita no processo `861` (ponte local Python rodando em background na porta 8805) nem nos processos ativos do OpenCode Helper.
*   **All Trust / YOLO Mode:** Ao configurar `"permission": { "*": "allow", "question": "deny" }`, o OpenCode não interromperá os agentes automáticos em execução solicitando permissão humana para leituras, escritas ou comandos Bash, operando sob o escopo absoluto de Root/Bypass desejado.
