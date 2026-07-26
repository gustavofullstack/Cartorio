# Cartório Spectrum Gateway

Gateway isolado para normalizar iMessage/Spectrum antes de delegar ao Hermes.
Ele não é a authority layer: regras jurídicas, LGPD, audit e protocolos vivem
na API do Cartório. O processo não inicia sem credenciais injetadas por ambiente.

## Segurança operacional

- Linha compartilhada permanece provider-allowlisted; `SPECTRUM_LINE_MODE=public`
  falha de propósito até existir linha dedicada com inbound público suportado.
- Nenhum segredo é versionado. Copie `.env.example` para um arquivo local
  ignorado e injete-o por secret manager.
- Phantom Panel é uma interface não configurada: não há endpoint inventado nem
  dependência do core.
- Saída pro canal passa por scrub de PII; criação de protocolo e atos jurídicos
  continuam dependentes do backend/HITL.

## Verificação local

```bash
npm install
npm run typecheck
```

O teste real requer mensagem de um telefone permitido para a linha configurada
e resposta na mesma conversa. Não confunda `connected` com validação E2E.
