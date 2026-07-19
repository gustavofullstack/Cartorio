# OpenCode Zen: roteamento de três contas

O backend oferece três slots independentes para OpenCode Zen, destinados a
continuidade de serviço de modelos gratuitos. Os slots são técnicos e não
devem carregar nome, e-mail ou outro identificador do titular.

## Configuração segura

Configure as variáveis abaixo exclusivamente no gerenciador de segredos do
ambiente (EasyPanel/Vault). Nunca as inclua em Git, `brain.md`, exports do
Postman, workflows n8n, logs, tickets ou documentação.

```text
OPENCODE_ZEN_ACCOUNT_1_API_KEY
OPENCODE_ZEN_ACCOUNT_1_BASE_URL
OPENCODE_ZEN_ACCOUNT_1_MODEL
OPENCODE_ZEN_ACCOUNT_2_API_KEY
OPENCODE_ZEN_ACCOUNT_2_BASE_URL
OPENCODE_ZEN_ACCOUNT_2_MODEL
OPENCODE_ZEN_ACCOUNT_3_API_KEY
OPENCODE_ZEN_ACCOUNT_3_BASE_URL
OPENCODE_ZEN_ACCOUNT_3_MODEL
```

Os exemplos de ambiente trazem somente o marcador
`<INJECT_FROM_SECRET_MANAGER>`. Uma chave compartilhada fora de um secret
manager deve ser considerada exposta e rotacionada antes do uso.

## Ordem e isolamento

O padrão é:

```text
opencode_zen_account_1
→ opencode_zen_account_2
→ opencode_zen_account_3
→ opencode_free_3/opencode_free_1/opencode_free_2
→ demais providers autorizados
```

Cada slot possui circuit breaker Redis próprio: três falhas transitórias em
60 segundos abrem apenas o respectivo circuito por cinco minutos. Um slot sem
segredo configurado é ignorado, sem contar como falha; isso permite rotação
gradual. Falta de consentimento LGPD sempre interrompe a cadeia inteira.

## Validação sem enviar dados pessoais

1. Injete os segredos pelo painel do ambiente, não por arquivos versionados.
2. Rode `make -C backend test-one TEST=tests/test_opencode_zen_multi_account.py`.
3. Em staging, faça uma chamada com consentimento de teste e conteúdo sintético.
4. Confirme no audit log apenas o nome do slot/modelo, nunca chave, prompt ou PII.
5. Remova a chave anterior do secret manager somente após o slot novo responder.

Modelos gratuitos e disponibilidade podem mudar. A lista efetivamente
autorizada deve ser validada no provedor e na matriz DPA antes de transportar
qualquer dado de cliente.
