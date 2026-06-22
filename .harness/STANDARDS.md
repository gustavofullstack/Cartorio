# STANDARDS — Cartorio Chatbot

Clean Code + SOLID + DDD aplicado ao dominio **cartorario**. Este doc e a fonte da verdade para qualidade de codigo. Toda PR deve respeitar.

> Conflito? Clean Code > SOLID > conveniencia pessoal. Duvida: perguntar ao `cartorio-dev` ou consultar livro de referencia (Uncle Bob, Vaughn Vernon).

---

## 1. Clean Code (Robert C. Martin)

### Naming

- **Variaveis**: substantivos. `cliente_cpf_hash`, nunca `x`, `temp`, `data`.
- **Funcoes**: verbos. `calcular_emolumento()`, `scrub_pii()`, `verificar_hash_chain()`.
- **Classes**: substantivos. `EmolumentoService`, `HashChainAudit`, nao `Manager`, `Helper`, `Util` genericos.
- **Booleanos**: `is_`, `has_`, `should_`, `can_`. `is_human_required`, `has_consent`, `should_handoff`.
- **Dominio cartorario**: usar termos do dominio real. `protocolo` (nao `case`), `escrivão` (nao `agent`), `emolumento` (nao `fee`), `ato` (nao `action`), `tabeliao` (nao `notary` em model, mas pode usar `notary` em comentario em ingles se preferir).

### Funcoes

- **Uma responsabilidade**. Se a funcao tem `and` no nome, quebre.
- **Tamanho**: alvo < 30 linhas. Maximo aceitavel 50. Acima disso, extrair.
- **Argumentos**: maximo 3. 4+ justifica objeto de parametro.
- **Zero side effects** surpresa. `calcular_emolumento()` nao deve escrever em DB. Se escreve, retorne o objeto.
- **Early return** em vez de nested if. Profundidade maxima 3.

```python
# BOM
def calcular_emolumento(ato: Ato, tabela: TabelaEmolumento) -> Emolumento:
    valor_base = tabela.buscar(ato.tipo)
    if ato.isento:
        return Emolumento.zerado(ato, motivo="isencao_legal")
    return Emolumento.aplicar_regras(valor_base, ato)

# RUIM
def calcular_emolumento(ato, tabela, cliente=None, agora=None):
    agora = agora or datetime.now()  # side effect implicito
    if cliente and cliente.isento and not ato.urgente:  # logica escondida
        return Emolumento(valor=0)
    ...
```

### Comentarios

- **Por que**, nao **o que**. Codigo limpo se explica sozinho.
- **TODO**: nome + data + issue. `# TODO(gustavo, 2026-06-25, #123): adicionar cache Redis`.
- **NUNCA** codigo comentado. Apaga. Git guarda historico.
- **NUNCA** print debug esquecido. Use `logging` com `logger.debug()`.

---

## 2. SOLID

### S — Single Responsibility

Cada modulo/funcao/classe tem **uma razao para mudar**.

- `app/services/audit.py` -> responsavel APENAS por append + verificacao do hash chain
- `app/services/pii.py` -> APENAS scrubbing de PII. NAO calcula emolumento. NAO decide HITL.
- `app/services/emolumento.py` -> APENAS regra de calculo. NAO acessa DB direto (recebe `TabelaEmolumento` injetada).

**Teste pratico**: se voce consegue descrever a classe sem usar "e" ("faz X e Y"), respeita SRP. Se precisa de "e", quebre.

### O — Open/Closed

Aberto para extensao, fechado para modificacao.

- Novas regras de emolumento: criar nova classe que implementa interface `RegraEmolumento`, nao editar `EmolumentoService.calcular()`.
- Novos tipos de PII: estender `PIIScrubber` via strategy, nao `if/elif` gigante.

```python
# BOM
class RegraIsencaoIdoso(RegraEmolumento):
    def aplicar(self, emolumento: Emolumento, ato: Ato) -> Emolumento:
        if ato.cliente.idade >= 65:
            return emolumento.com_desconto(percentual=100)
        return emolumento

# RUIM
def calcular(ato):
    if ato.cliente and ato.cliente.idade >= 65:
        return 0
    if ato.tipo == "escritura" and ato.valor > 100000:
        ...
```

### L — Liskov Substitution

Subclasses respeitam contrato da classe mae.

- `HashChainAudit` (Postgres) e `InMemoryHashChainAudit` (teste) devem ser intercambiaveis onde `HashChainAudit` e esperado.

### I — Interface Segregation

Interfaces especificas > interface generica.

- `PIIScrubber.scrub(text)` e `PIIScrubber.scrub_structured(dict)` sao metodos separados, nao um unico `scrub(obj)` que faz tudo.

### D — Dependency Inversion

Modulos de alto nivel NAO dependem de modulos de baixo nivel. Ambos dependem de abstracoes.

- `EmolumentoService` recebe `TabelaEmolumentoRepository` via construtor (FastAPI Depends). NAO instancia `PostgresTabelaEmolumentoRepository()` dentro.
- `AuditService` recebe `HashSigner` (interface). Implementacao `HMACHashSigner` injetada. Testes injetam `FakeHashSigner`.

```python
# BOM
class EmolumentoService:
    def __init__(self, repo: TabelaEmolumentoRepository, audit: AuditService):
        self._repo = repo
        self._audit = audit

# RUIM
class EmolumentoService:
    def calcular(self, ato):
        db = SessionLocal()  # acoplamento direto
        tabela = db.query(TabelaEmolumento).filter_by(estado="MG").first()
```

---

## 3. DDD — Domain-Driven Design (Vaughn Vernon)

O cartorio e o dominio. Codigo deve refletir a linguagem do cartorario.

### Linguagem ubiqua (Ubiquitous Language)

Glossario canonico (usar EXATAMENTE estes termos no codigo):

| Termo | Sinonimo proibido | Onde vive |
|-------|-------------------|-----------|
| Protocolo | case, ticket, order | `app/models/protocolo.py` |
| Ato | action, operation | `app/models/emolumento.py` |
| Emolumento | fee, price, cost | `app/models/emolumento.py` |
| Tabela de Emolumento | price table, fee schedule | snapshot imutavel |
| Cliente | user, customer | `app/models/cliente.py` |
| Conversa | chat, message, thread | `app/models/conversa.py` |
| Documento | file, attachment | `app/models/documento.py` |
| Tabeliao | notary | (NÃO em model; pode em log) |
| Escrevente | clerk, operator | (idem) |
| HITL (Human-in-the-Loop) | approval, manual review | `handoff_to_human` em conversa |
| Hash Chain | audit chain, blockchain | `audit_log` |

### Bounded Contexts

```
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│  Contexto: Atendimento  │  │  Contexto: Protocolo    │  │  Contexto: Compliance   │
│  (Conversa + Mensagem)  │  │  (Protocolo + Documento │  │  (LGPD + Audit + PII)   │
│                         │  │   + Ato)                │  │                         │
│  - conversa             │  │  - protocolo            │  │  - consentimento        │
│  - intencao             │  │  - documento            │  │  - retencao             │
│  - handoff              │  │  - emolumento (snapshot)│  │  - audit_log            │
│                         │  │                         │  │  - pii_scrubber         │
│  Rein: cartorio-n8n +   │  │  Rein: cartorio-dev     │  │  Rein: cartorio-lgpd    │
│       cartorio-dev      │  │                         │  │                         │
└─────────────────────────┘  └─────────────────────────┘  └─────────────────────────┘
```

### Aggregates

- **Aggregate Root: `Protocolo`** — controla `Documento` (parte do mesmo aggregate). Invariantes: `Documento` so existe se `Protocolo` existe. Soft delete em cascata.
- **Aggregate Root: `Conversa`** — controla mensagens. Invariantes: mensagem so pertence a uma conversa.
- **Aggregate Root: `Cliente`** — controla consentimentos LGPD. Invariante: NAO criar `Conversa` sem `Cliente.consentimento_lgpd=True`.

### Entities vs Value Objects

- **Entity**: tem identidade (id). `Protocolo(numero='12345')`, `Cliente(cpf_hash='abc')`. Dois protocolos com mesmo ato sao diferentes.
- **Value Object**: imutavel, sem identidade. `CPF(numero='12345678900')`, `ValorMonetario(centavos=5000)`, `HashSHA256(hex='...')`. Dois VOs com mesmo valor sao iguais.

### Repositories

- Interface em `app/domain/<aggregate>/repository.py` (abstrata)
- Implementacao em `app/infrastructure/postgres/<aggregate>_repo.py`
- `app/services/` depende da **interface**, nao da implementacao

### Domain Events

Eventos sao publicados quando algo importante acontece:

```python
class ProtocoloCriado(DomainEvent):
    protocolo_id: UUID
    cliente_id: UUID
    ato_tipo: str
    emolumento_snapshot_id: UUID
    timestamp: datetime

class ClienteConsentimentoRevogado(DomainEvent):
    cliente_id: UUID
    revogacao_timestamp: datetime
    conversas_afetadas: int
```

Cartorio-lgpd escuta `ClienteConsentimentoRevogado` para iniciar fluxo de anonimizacao.

### Anti-Corruption Layer (ACL)

Integracoes externas (Evolution API, n8n, LiteLLM, Supabase) ficam em `app/infrastructure/`. **Nunca** deixam modelo externo vazar para dominio.

```python
# BOM
@app.post("/webhook/evolution")
async def receber_mensagem(payload: EvolutionWebhookPayload):
    conversa = ConversaMapper.from_evolution(payload)  # ACL converte
    await atendimento_service.processar(conversa)

# RUIM
@app.post("/webhook/evolution")
async def receber_mensagem(payload: dict):
    conversa = Conversa(
        telefone=payload["data"]["key"]["remoteJid"],  # vazou estrutura Evolution
        ...
    )
```

---

## 4. Regras cartorarias especificas (golden rules)

### Audit log

- **Append-only**. UPDATE e DELETE em `audit_log` = crime. Bloquear via DB role.
- **Toda mutacao** gera entrada: `conversa.received`, `protocolo.read`, `protocolo.created`, `cliente.consent_revoked`.
- **Verificacao automatica** diaria via cron. Falha = alerta P0.

### PII scrubbing

- **3 camadas**: input, pre-LLM, output. Ver `backend/app/services/pii.py`.
- **Hash deterministico com salt por cartorio**: permite `WHERE cpf_hash = ?` sem armazenar CPF puro.
- **Output de erro nunca ecoa input bruto**. Se regex falha em detectar, descartar + logar evento suspeito.

### HITL

- Bot decide sozinho SE categoria = read_only E `confidence >= 0.85`.
- HITL obrigatorio: `isencao`, `urgencia`, `validacao_documento`, `emissao_certidao`, `escritura`.
- Toda transicao de estado em `protocolo` (criado -> em_andamento -> concluido) registra `actor` = 'bot' ou 'human:<user_id>'.

### Snapshot de emolumento

- Tabela de emolumento e **snapshotada** no momento do calculo. NUNCA recalcular protocolo antigo.
- Campo `tabela_referencia` e `valido_ate` no `emolumento` gravado.
- Job diario carrega nova tabela do DO do estado (MG).

---

## 5. Performance e operacao

- Latencia alvo por endpoint: P95 < 200ms (exceto LLM call, que pode ir ate 3s).
- Query N+1 = bug. Usar `selectinload` / `joinedload`.
- Redis para cache de: tabela emolumento do dia (TTL 24h), sessoes de protocolo consultado (TTL 5min).
- Health check em `GET /health` que valida DB + Redis + audit chain (smoke).

## 6. Referencias

- Clean Code — Robert C. Martin
- Clean Architecture — Robert C. Martin
- Implementing Domain-Driven Design — Vaughn Vernon
- LGPD Lei 13.709/2018
- Provimento 74/2018 CNJ (cartorio eletronico)

Modified by Gustavo Almeida
