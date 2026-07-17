# G7.21.T3 — Auditoria SQLAlchemy `Mapped[]` nos models (100% check)

**Data:** 2026-07-17  
**Autor:** cartorio-dev (Wave 25 slot A3)  
**Escopo:** `backend/app/models/**/*.py`  
**Meta:** 100% campos de coluna/relationship no estilo SQLAlchemy 2.0 (`Mapped[...]` + `mapped_column` / `relationship`)  
**Política:** report only — sem refactor de models nesta wave.

---

## 1. Método

```bash
# Legado SQLAlchemy 1.x
rg '=\s*Column\(' backend/app/models --type py

# Estilo 2.0
rg -c 'Mapped\[' backend/app/models --type py
rg -c 'mapped_column' backend/app/models --type py
rg 'relationship\(' backend/app/models --type py
```

Checklist por arquivo:

1. Existe `=\s*Column(` (legado)?  
2. Cada `mapped_column(` está anotado com `Mapped[...]`?  
3. Cada `relationship(` está anotado com `Mapped[...]`?  
4. Mixins (`TimestampMixin`, `SoftDeleteMixin`) também usam `Mapped`?

---

## 2. Resultado executivo

| Indicador | Valor |
|---|---|
| Arquivos em `app/models/` | 13 (12 código + `__init__`) |
| Classes ORM de tabela | **11** (`Base` declarativo + 10 entidades; mixins à parte) |
| Anotações `Mapped[]` | **144** |
| Chamadas `mapped_column(` | **135** |
| `relationship(` | **8** (todas com `Mapped[...]`) |
| Atribuições legadas `= Column(` | **0** |
| **Compliance Column → Mapped** | **100%** |
| **Compliance relationship Mapped** | **100%** (8/8) |

> `Mapped[]` (144) > `mapped_column` (135) porque relationships e alguns campos contam só como `Mapped` (sem `mapped_column`).

**Veredito:** **meta G7.21.T3 atingida** — models do cartório estão em SQLAlchemy 2.0 typed style. Nenhuma ação de migração pendente.

---

## 3. Tabela por arquivo

| Arquivo | Classes ORM | Mapped[] | mapped_column | rel Mapped | `Column(` legado | Status |
|---|---|---:|---:|---:|---:|---|
| `agendamento.py` | `Agendamento` | 15 | 13 | 2/2 | 0 | ✅ 100% |
| `atendimento.py` | `Atendimento` | 17 | 17 | 0 | 0 | ✅ 100% |
| `audit_log.py` | `AuditLog` | 15 | 15 | 0 | 0 | ✅ 100% |
| `base.py` | `Base`, `TimestampMixin` | 2 | 2 | 0 | 0 | ✅ 100% |
| `cliente.py` | `Cliente` | 19 | 17 | 2/2 | 0 | ✅ 100% |
| `conversa.py` | `Conversa` | 17 | 17 | 0 | 0 | ✅ 100% |
| `cpf_cnpj_validator.py` | — (funções DV) | 0 | 0 | 0 | 0 | N/A (sem tabela) |
| `documento.py` | `Documento` | 14 | 13 | 1/1 | 0 | ✅ 100% |
| `lgpd_consent.py` | `LGPDConsentLog` | 9 | 9 | 0 | 0 | ✅ 100% |
| `mixins.py` | `SoftDeleteMixin` | 1* | 2** | 0 | 0 | ✅ 100% |
| `outbox_message.py` | `OutboxMessage` | 9 | 9 | 0 | 0 | ✅ 100% |
| `protocolo.py` | `Protocolo` | 19 | 16 | 3/3 | 0 | ✅ 100% |
| `webhook_event.py` | `WebhookEvent` | 5 | 5 | 0 | 0 | ✅ 100% |

\* Contagem real de campo no mixin: `deleted_at` (+ property `is_deleted`). Ocorrências extras de `Mapped[` no arquivo vêm de **exemplos na docstring**.  
\** `mapped_column` na docstring de uso + coluna real — não há legado.

---

## 4. Herança de mixins (campos Mapped herdados)

| Model | Bases | Soft delete | Timestamps mixin |
|---|---|---|---|
| `Cliente` | `Base, TimestampMixin, SoftDeleteMixin` | sim | `created_at`/`updated_at` |
| `Protocolo` | idem | sim | sim |
| `Conversa` | idem | sim | sim |
| `Documento` | idem | sim | sim |
| `Agendamento` | idem | sim | sim (+ `criado_em`/`atualizado_em` próprios) |
| `Atendimento` | idem | sim | sim |
| `WebhookEvent` | idem | sim | sim |
| `AuditLog` | `Base` only | **não** (append-only chain) | timestamp próprio |
| `OutboxMessage` | `Base` only | **não** (DLQ retry) | `created_at`/`updated_at` próprios |
| `LGPDConsentLog` | `Base` only | não | `timestamp` próprio |

Alinhado a `mixins.py` / AGENTS.md: audit e outbox **não** usam soft-delete.

---

## 5. Relationships (amostra)

Todas no padrão:

```python
protocolos: Mapped[list["Protocolo"]] = relationship(back_populates="cliente")
cliente: Mapped["Cliente"] = relationship(back_populates="protocolos")
```

| Arquivo | Relationships |
|---|---|
| `cliente.py` | `protocolos`, `agendamentos` |
| `protocolo.py` | `cliente`, `documentos`, `agendamentos` |
| `documento.py` | `protocolo` |
| `agendamento.py` | `cliente`, `protocolo` |

---

## 6. Exemplo canônico (compliance)

```36:46:backend/app/models/cliente.py
    id: Mapped[int] = mapped_column(primary_key=True)
    # Hash SHA256 do CPF (com salt por cliente). CPF puro NUNCA persiste.
    cpf_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    telefone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Notificações e contatos
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sms_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

`TimestampMixin` / `SoftDeleteMixin`:

```11:15:backend/app/models/base.py
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
```

```67:72:backend/app/models/mixins.py
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        index=True,
    )
```

---

## 7. Observações / não-bloqueadores

| Item | Severidade | Nota |
|---|---|---|
| `datetime.utcnow` em defaults de mixin/model | Baixa (style/py311) | Preferível `datetime.now(timezone.utc)` em wave futura — **não** é gap de Mapped |
| `query_active` ainda usa `db.query()` (1.x style) em `mixins.py` | Baixa | Existe `select_active` 2.0; migrar call-sites depois |
| `LGPDConsentLog` / `OutboxMessage` fora de `SoftDeleteMixin` | OK | Decisão de domínio documentada |
| `cpf_cnpj_validator.py` no pacote models | N/A | Utilitário de DV, não ORM |
| Models não exportados em `__init__` (`LGPDConsentLog`) | Info | Import direto do submódulo — fora do escopo Mapped |

---

## 8. Gate de regressão sugerido (CI opcional)

```bash
# falha se reintroduzir Column legado em models
! rg -n '=\s*Column\(' backend/app/models --type py
```

Opcional no `make lint` / pre-push — **não** adicionado nesta wave.

---

## 9. Conclusão G7.21.T3

| Check | Resultado |
|---|---|
| Zero `Column(` legado em models | ✅ |
| 100% colunas com `Mapped` + `mapped_column` | ✅ |
| 100% relationships com `Mapped` | ✅ |
| Mixins em estilo 2.0 | ✅ |
| Refactor necessário | **Não** |

**Compliance reportada: 100%.**

---

Modified by Gustavo Almeida  
cartorio-dev · G7.21.T3 · Wave 25
