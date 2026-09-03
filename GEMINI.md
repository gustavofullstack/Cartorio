# Gemini CLI & Antigravity Agent Rules — Cartório (Pietra)

> Consulte também: `AGENTS.md` (especificação canônica de compliance e persona) e `Makefile`
> Repositório: `Cartorio` | CNS: 05.799-2 (2º Tabelionato de Notas de Uberlândia / MG)

---

## Mandato do Projeto

Backend e assistente virtual (Pietra) do 2º Serviço Notarial de Uberlândia / MG.
Atendimento omnicanal (WhatsApp / Telegram / Web) com conformidade LGPD rigorosa, audit log imutável (cadeia SHA-256 + HMAC) e human-in-the-loop obrigatório para qualquer ato jurídico.

---

## Comandos Operacionais (via Makefile na raiz)

Execute sempre os comandos através do Makefile raiz:

```bash
# Ambiente e dependências (uv)
make install
make setup

# Desenvolvimento local
make dev

# Suíte de testes (com cobertura mínima de 90%)
make test
make test-fast

# Qualidade e Linting (Ruff + Mypy)
make lint
make format
make qa
```

---

## Diretivas Críticas de Segurança e Compliance (P0)

1. **Proteção LGPD & PII:** É terminantemente proibido registrar ou logar dados pessoais sensíveis (CPFs, nomes completos de outorgantes/partes, certidões, minutas de escrituras) em formato aberto. Utilize sempre o pipeline de PII scrubbing em 3 camadas.
2. **Audit Log Imutável:** Todas as transações e interações devem manter a integridade da cadeia de hash HMAC/SHA-256.
3. **Atos Notariais:** Qualquer sugestão ou elaboração de documento notarial (procurações, escrituras, testamentos) requer validação humana formal do tabelião ou escrevente autorizado.
