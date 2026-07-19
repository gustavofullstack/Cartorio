# Filtro de segredos em logs — G8.23.T1

## Objetivo

Impedir que credenciais carregadas por Pydantic Settings a partir de `.env` apareçam em mensagens de logging emitidas durante o startup ou a execução da API.

O filtro está em `backend/app/core/secrets_log_filter.py`. O `lifespan` de `backend/app/main.py` registra uma instância em cada handler do root logger antes de inicializar Sentry, OpenTelemetry, banco de dados, auditoria e schedulers.

## Cobertura

As expressões regulares são compiladas uma única vez na importação do módulo e removem:

- atribuições com nomes `api_key`, `secret`, `token`, `password`, `passwd` ou `pwd`;
- JWTs compactos com três segmentos;
- chaves com prefixos OpenAI e Anthropic;
- identificadores de access key AWS.

A substituição canônica é `[SECRET-REDACTED]`. O filtro resolve argumentos de `LogRecord`, sanitiza a mensagem resultante e limpa `record.args`, evitando que o formatter reinsira o valor original.

## Uso operacional

Código de startup e rotas devem usar `logging`, nunca `print()`, para mensagens operacionais. O filtro protege mensagens processadas pelos handlers registrados; não autoriza registrar configurações completas nem substitui a proibição de imprimir `os.environ`, valores de `settings` ou conteúdo de `.env`.

Ao adicionar um novo formato de credencial:

1. incluir uma expressão compilada em `SECRET_PATTERNS`;
2. usar dados sintéticos construídos em runtime no teste, sem chave literal;
3. executar `make test-one TEST=tests/test_secrets_log_filter_g8.py`;
4. executar `make lint` e `make test-fast`.

## LGPD Art. 46

O Art. 46 da LGPD exige medidas técnicas e administrativas aptas a proteger dados contra acesso não autorizado e comunicação acidental ou ilícita. Credenciais expostas em stdout ou stderr podem liberar acesso indireto a dados pessoais, documentos e trilhas de auditoria.

A medida atua em defesa em profundidade:

1. segredos permanecem em `.env` e fora do Git;
2. o código não imprime ambiente ou configuração;
3. mensagens de logging passam pelo `SecretScrubLogFilter`;
4. scanners de segredo continuam bloqueando literais no repositório.

## Validação

`backend/tests/test_secrets_log_filter_g8.py` cobre atribuição de API key, JWT, OpenAI, Anthropic, AWS, mensagem limpa, interpolação por argumentos, Unicode, ausência de `print()` de ambiente no carregamento de `main.py` e registro do filtro no `lifespan`.
