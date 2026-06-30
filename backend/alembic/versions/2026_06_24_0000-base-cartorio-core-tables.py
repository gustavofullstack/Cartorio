"""base cartorio core tables — D0.1 migration BASE

Revision ID: 2026_06_24_0000
Revises: 2026_06_23_0001
Create Date: 2026-06-24 23:50:00.000000

D0.1 (PLAN_GIGANTE 2026-06-24): criar migration BASE que documenta o schema
oficial das 8 tabelas core do cartorio + 3 auxiliares. Esta migration eh
IDEMPOTENTE (CREATE TABLE / CREATE INDEX IF NOT EXISTS) porque as tabelas
foram criadas via Sprint 0 manual antes do Alembic ser adotado.

Tabelas (sincronizadas com backend/app/models/):
  core (5):    clientes, conversas, protocolos, documentos, atendimentos
  auxiliares:  audit_log, outbox_messages, webhook_events

Nota sobre `emolumento`: nao existe model emolumento.py nesta revisao.
Os campos de emolumento (valor_base, valor_adicional, valor_total,
tabela_referencia) vivem DENTRO de `protocolos` como snapshot da tabela
oficial de emolumentos (Provimento CNJ 74/2018). A tabela legacy
`emolumentos` existe no DB desde Sprint 0 (seed MG 2026) e nao tem
model no codigo novo - sua manutencao eh via script seed
(T2.SUP.T7 / E0.S0.5.T4 WIP).

LGPD-by-design:
- clientes.cpf_hash / telefone_hash: SHA256 com salt por cliente (PI).
  CPF puro NUNCA persiste. Acessor: pii/crypto services.
- audit_log.ip: dado pessoal (LGPD art. 5 II), acesso DPO-only.
- audit_log.ip_truncated: /24 (IPv4) ou /32 (IPv6) para OUTPUT.
- conversas.raw_message_scrubbed: conteudo JA scrubbed pre-persist.
- outbox_messages.payload: SEMPRE scrubbed pre-enqueue.
- clientes.audit_encerramento_id: encerra cliente SEM perder historico
  (LGPD art. 18 VI + ADR-018).

Chain:
- down_revision = "2026_06_23_0001" (UNICO valor possivel: 2026_06_23_0001
  ja tem down_revision=None. Briefing pediu None, mas isso causaria
  "Multiple roots" no alembic).
- Resultado: chain agora tem 2 heads (2026_06_24_0000 e 2026_06_24_0002).
  Resolucao: criar merge migration em sprint futura. Nao eh bloqueador
  para esta entrega porque a migration eh idempotente e roda em
  qualquer ordem.

Compat: PostgreSQL (UUID nativo, JSONB nativo, SAEnum nativo) +
SQLite (UUID como CHAR(32), JSON serializado, SAEnum como VARCHAR).

Modified by Gustavo Almeida
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2026_06_24_0000"
down_revision: Union[str, None] = "2026_06_23_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria schema BASE cartorio (idempotente).

    Cada CREATE TABLE / CREATE INDEX usa IF NOT EXISTS para ser
    safely re-aplicavel em DB ja migrado (Sprint 0 manual).
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_pg = bind.dialect.name == "postgresql"
    existing_tables = set(inspector.get_table_names())

    # ----- ENUMS -----
    motivo_encerramento_enum = (
        postgresql.ENUM(
            "revogacao_consentimento",
            "retencao_5y",
            "exercicio_direito_titular",
            "outros",
            name="motivo_encerramento_enum",
            create_type=False,  # ja existe no DB prod
        )
        if is_pg
        else sa.Enum(
            "revogacao_consentimento",
            "retencao_5y",
            "exercicio_direito_titular",
            "outros",
            name="motivo_encerramento_enum",
        )
    )

    # Garante tipo enum existe (IF NOT EXISTS via create_type)
    if is_pg:
        motivo_encerramento_enum.create(bind, checkfirst=True)

    # ----- AUDIT_LOG -----
    # Tabela de hash chain (tamper-evident). PK + indices.
    if "audit_log" not in existing_tables:
        op.create_table(
            "audit_log",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("actor_id", sa.String(length=128), nullable=False),
            sa.Column("actor_type", sa.String(length=32), nullable=False, server_default="user"),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("resource", sa.String(length=128), nullable=False),
            sa.Column(
                "payload",
                sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
            sa.Column("ip", sa.String(length=45), nullable=True),
            sa.Column("ip_truncated", sa.String(length=50), nullable=True),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=True),
            sa.Column("canal", sa.String(length=32), nullable=True),
            sa.Column("prev_hash", sa.String(length=64), nullable=True),
            sa.Column("hash", sa.String(length=64), nullable=False),
            sa.Column("hmac_signature", sa.String(length=128), nullable=False),
            sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
    # Indices audit_log (SQL: IF NOT EXISTS para idempotencia)
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_actor_id ON audit_log (actor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log (action)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_resource ON audit_log (resource)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_request_id ON audit_log (request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_canal ON audit_log (canal)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_hash ON audit_log (hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log (timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ip_truncated ON audit_log (ip_truncated)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_resource_action ON audit_log (resource, action)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_actor_action ON audit_log (actor_id, action)")

    # ----- CLIENTES -----
    # NUNCA armazenar CPF/telefone em texto puro, apenas hash.
    if "clientes" not in existing_tables:
        op.create_table(
            "clientes",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("cpf_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column("nome", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("telefone_hash", sa.String(length=64), nullable=True),
            # LGPD
            sa.Column(
                "consentimento_lgpd", sa.Boolean, nullable=False, server_default=sa.text("false")
            ),
            sa.Column("consentimento_em", sa.DateTime, nullable=True),
            sa.Column("consentimento_ip", sa.String(length=45), nullable=True),
            sa.Column("consentimento_canal", sa.String(length=32), nullable=True),
            # Soft delete (LGPD art. 18 VI + D4)
            sa.Column("deleted_at", sa.DateTime, nullable=True),
            sa.Column("motivo_encerramento", motivo_encerramento_enum, nullable=True),
            sa.Column("audit_encerramento_id", sa.Integer, nullable=True),
            # Timestamps
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_clientes_cpf_hash ON clientes (cpf_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clientes_email ON clientes (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clientes_telefone_hash ON clientes (telefone_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_clientes_deleted_at ON clientes (deleted_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_clientes_motivo_encerramento ON clientes (motivo_encerramento)"
    )
    # FK clientes.audit_encerramento_id -> audit_log.id (ON DELETE SET NULL)
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints "
        "  WHERE constraint_name = 'clientes_audit_encerramento_id_fkey') THEN "
        "  ALTER TABLE clientes ADD CONSTRAINT clientes_audit_encerramento_id_fkey "
        "  FOREIGN KEY (audit_encerramento_id) REFERENCES audit_log(id) "
        "  ON DELETE SET NULL; "
        "END IF; END $$"
    )

    # ----- CONVERSAS -----
    if "conversas" not in existing_tables:
        op.create_table(
            "conversas",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("cliente_id", sa.Integer, sa.ForeignKey("clientes.id"), nullable=True),
            sa.Column("canal", sa.String(length=32), nullable=False),
            sa.Column("external_id", sa.String(length=128), nullable=False),
            sa.Column("raw_message_hash", sa.String(length=64), nullable=False),
            sa.Column("raw_message_scrubbed", sa.Text, nullable=False),
            sa.Column("intent_detected", sa.String(length=64), nullable=True),
            sa.Column("confidence_score", sa.Float, nullable=True),
            sa.Column("bot_response", sa.Text, nullable=True),
            sa.Column(
                "handoff_to_human", sa.Boolean, nullable=False, server_default=sa.text("false")
            ),
            sa.Column("handoff_at", sa.DateTime, nullable=True),
            sa.Column("handoff_reason", sa.String(length=255), nullable=True),
            sa.Column("handoff_agent", sa.String(length=128), nullable=True),
            sa.Column("llm_model", sa.String(length=64), nullable=True),
            sa.Column("llm_tokens_in", sa.Integer, nullable=True),
            sa.Column("llm_tokens_out", sa.Integer, nullable=True),
            sa.Column("llm_latency_ms", sa.Integer, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversas_cliente_id ON conversas (cliente_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversas_canal ON conversas (canal)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversas_external_id ON conversas (external_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conversas_intent_detected ON conversas (intent_detected)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conversas_handoff_to_human ON conversas (handoff_to_human)"
    )

    # ----- PROTOCOLOS -----
    if "protocolos" not in existing_tables:
        op.create_table(
            "protocolos",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("numero", sa.String(length=32), nullable=False, unique=True),
            sa.Column("cliente_id", sa.Integer, sa.ForeignKey("clientes.id"), nullable=False),
            sa.Column("tipo", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="aberto"),
            # Financeiro (snapshot emolumento)
            sa.Column("valor_base", sa.Numeric(10, 2), nullable=True),
            sa.Column("valor_adicional", sa.Numeric(10, 2), nullable=True),
            sa.Column("valor_total", sa.Numeric(10, 2), nullable=True),
            sa.Column("tabela_referencia", sa.String(length=64), nullable=True),
            # Prazos
            sa.Column("prazo_dias", sa.Integer, nullable=True),
            sa.Column("previsao_conclusao", sa.DateTime, nullable=True),
            sa.Column("concluido_em", sa.DateTime, nullable=True),
            # PDF assinado
            sa.Column("pdf_storage_path", sa.String(length=512), nullable=True),
            sa.Column("pdf_hash_sha256", sa.String(length=64), nullable=True),
            sa.Column("pdf_assinado_por", sa.String(length=255), nullable=True),
            # Origem
            sa.Column("canal_origem", sa.String(length=32), nullable=False),
            # Timestamps
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_protocolos_numero ON protocolos (numero)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_protocolos_cliente_id ON protocolos (cliente_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_protocolos_tipo ON protocolos (tipo)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_protocolos_status ON protocolos (status)")

    # ----- DOCUMENTOS -----
    if "documentos" not in existing_tables:
        op.create_table(
            "documentos",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("protocolo_id", sa.Integer, sa.ForeignKey("protocolos.id"), nullable=False),
            sa.Column("tipo", sa.String(length=64), nullable=False),
            sa.Column("storage_path", sa.String(length=512), nullable=False),
            sa.Column(
                "storage_provider", sa.String(length=32), nullable=False, server_default="supabase"
            ),
            sa.Column("tamanho_bytes", sa.BigInteger, nullable=True),
            sa.Column("mime_type", sa.String(length=128), nullable=True),
            sa.Column("hash_sha256", sa.String(length=64), nullable=False),
            sa.Column("uploaded_by", sa.String(length=128), nullable=False),
            sa.Column(
                "uploaded_by_tipo", sa.String(length=32), nullable=False, server_default="cliente"
            ),
            sa.Column("validado_por", sa.String(length=128), nullable=True),
            sa.Column("validado_em", sa.DateTime, nullable=True),
            sa.Column("validacao_notas", sa.String(length=1024), nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_documentos_protocolo_id ON documentos (protocolo_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documentos_tipo ON documentos (tipo)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documentos_hash_sha256 ON documentos (hash_sha256)")

    # ----- ATENDIMENTOS -----
    # Registro de atendimento humano (Chatwoot handoff).
    if "atendimentos" not in existing_tables:
        op.create_table(
            "atendimentos",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("protocolo_id", sa.Integer, sa.ForeignKey("protocolos.id"), nullable=True),
            sa.Column("cliente_id", sa.Integer, sa.ForeignKey("clientes.id"), nullable=True),
            sa.Column("canal", sa.String(length=32), nullable=False),
            sa.Column("external_id", sa.String(length=128), nullable=False),
            sa.Column("chatwoot_conversation_id", sa.Integer, nullable=True),
            sa.Column("chatwoot_inbox_id", sa.Integer, nullable=True),
            sa.Column("chatwoot_agent_id", sa.Integer, nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="aberto"),
            sa.Column("tipo", sa.String(length=64), nullable=False),
            sa.Column("contexto_scrubbed", sa.Text, nullable=True),
            sa.Column("pesquisa_enviada_em", sa.DateTime, nullable=True),
            sa.Column("pesquisa_nota", sa.Integer, nullable=True),
            sa.Column("pesquisa_comentario", sa.Text, nullable=True),
            sa.Column("iniciado_em", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("concluido_em", sa.DateTime, nullable=True),
            sa.Column(
                "handoff_para_humano", sa.Boolean, nullable=False, server_default=sa.text("false")
            ),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_atendimentos_protocolo_id ON atendimentos (protocolo_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_atendimentos_cliente_id ON atendimentos (cliente_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_atendimentos_canal ON atendimentos (canal)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_atendimentos_external_id ON atendimentos (external_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_atendimentos_status ON atendimentos (status)")

    # ----- OUTBOX_MESSAGES -----
    # DLQ para integracoes externas. Criado por 2026_06_24_0002 mas
    # IF NOT EXISTS aqui garante idempotencia em DB que ja tem tabela.
    if "outbox_messages" not in existing_tables:
        op.create_table(
            "outbox_messages",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True) if is_pg else sa.String(length=36),
                primary_key=True,
            ),  # type: ignore[misc]
            sa.Column("queue", sa.String(length=32), nullable=False),
            sa.Column(
                "payload", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False
            ),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text, nullable=True),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_outbox_messages_queue ON outbox_messages (queue)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_outbox_messages_status ON outbox_messages (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_outbox_messages_next_retry_at ON outbox_messages (next_retry_at)"
    )

    # ----- WEBHOOK_EVENTS -----
    # Tabela de deduplicacao. Idempotencia via UNIQUE(source, event_id).
    if "webhook_events" not in existing_tables:
        op.create_table(
            "webhook_events",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("event_id", sa.String(length=256), nullable=False),
            sa.Column("received_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.UniqueConstraint("source", "event_id", name="uq_webhook_events_source_event"),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_webhook_events_source ON webhook_events (source)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_webhook_events_event_id ON webhook_events (event_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_webhook_events_received_at ON webhook_events (received_at)"
    )


def downgrade() -> None:
    """Drop schema BASE cartorio (ordem reversa por causa das FKs)."""
    op.execute("DROP TABLE IF EXISTS webhook_events CASCADE")
    op.execute("DROP TABLE IF EXISTS outbox_messages CASCADE")
    op.execute("DROP TABLE IF EXISTS atendimentos CASCADE")
    op.execute("DROP TABLE IF EXISTS documentos CASCADE")
    op.execute("DROP TABLE IF EXISTS protocolos CASCADE")
    op.execute("DROP TABLE IF EXISTS conversas CASCADE")
    op.execute("DROP TABLE IF EXISTS clientes CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
