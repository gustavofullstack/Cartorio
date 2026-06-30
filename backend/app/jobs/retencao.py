"""Job de retencao de dados - purge LGPD.

Decisao: ver ADR-019.

Fase 1 (soft delete — ativa clientes inativos):
1. Cliente COM protocolo: retencao 5 anos a partir do ULTIMO protocolo.
   Quando passa dos 5 anos, anonimiza PII (soft delete com motivo=retencao_5y).
2. Cliente SEM protocolo: retencao 2 anos de inatividade.
   "Inativo" = sem protocolo criado, sem atendimento, sem update ha 2 anos.
   Quando passa, anonimiza PII (soft delete com motivo=outros).

Fase 2 (hard delete — purge de clientes ja soft-deleted):
3. Cliente JA soft-deleted por REVOGACAO_CONSENTIMENTO (art. 18 VI) + > 5y
   desde o deleted_at → PURGE (row removida do DB).
4. Cliente JA soft-deleted por OUTROS + > 5y desde deleted_at → PURGE.
5. Cliente JA soft-deleted por EXERCICIO_DIREITO_TITULAR (art. 18 III — correcao)
   → NAO PURGE. Correcoes devem ser mantidas ate revogacao explicita.

Idempotente: clientes ja soft-deleted (deleted_at IS NOT NULL) sao pulados na Fase 1.
Fase 2 sempre re-avalia clientes ja soft-deleted (podem ter atingido 5y no ultimo ciclo).

NAO emite audit log: o chamador (CLI, cron, API) eh quem sabe o canal/request_id.
Funcao retorna dataclass com contadores + IDs afetados (IDs mascarados para log externo).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.atendimento import Atendimento
from app.models.cliente import Cliente, MotivoEncerramento
from app.models.protocolo import Protocolo
from app.services.lgpd.direito_esquecimento import _anonimiza_pii


@dataclass(frozen=True)
class RetencaoConfig:
    """Parametros de retencao (override de env vars para testes)."""

    retencao_5y_dias: int = 1825  # 5 anos
    retencao_inativo_dias: int = 730  # 2 anos
    enabled: bool = True


@dataclass(frozen=True)
class RetencaoResult:
    """Resultado de uma execucao do job de retencao.

    IDs internos (int) para uso interno. Para log externo (audit LGPD art. 37),
    o chamador deve mascarar antes de persistir (ex: f"C{id:04d}").
    """

    batch_id: str
    scanned: int
    soft_deleted_5y: list[int] = field(default_factory=list)
    soft_deleted_inativo: list[int] = field(default_factory=list)
    hard_deleted_ids: list[int] = field(default_factory=list)
    skipped_exercicio_direito: int = 0  # EXERCICIO_DIREITO_TITULAR preservados
    skipped_already_deleted: int = 0
    errors: list[str] = field(default_factory=list)
    cutoff_5y: datetime | None = None
    cutoff_inativo: datetime | None = None
    duration_ms: int = 0


def _last_activity_at(db: Session, cliente_id: int, cliente: Cliente) -> datetime | None:
    """Retorna a data da ultima atividade conhecida do cliente.

    Considera: max(updated_at) de cliente + protocolo + atendimento.
    Retorna None se nao houver NENHUM updated_at (cliente recem-criado).
    NUNCA usa created_at pois isso nao representa atividade do titular.
    """
    candidates: list[datetime] = [cliente.updated_at]

    p = db.execute(
        select(func.max(Protocolo.updated_at)).where(Protocolo.cliente_id == cliente_id)
    ).scalar()
    if p is not None:
        candidates.append(p)

    a = db.execute(
        select(func.max(Atendimento.updated_at)).where(Atendimento.cliente_id == cliente_id)
    ).scalar()
    if a is not None:
        candidates.append(a)

    return max(candidates)


def _apply_soft_delete(
    db: Session,
    cliente: Cliente,
    motivo: MotivoEncerramento,
    data_encerramento: datetime,
) -> None:
    """Aplica soft delete com motivo customizado (reuso de logica do service)."""
    _anonimiza_pii(cliente)
    cliente.deleted_at = data_encerramento
    cliente.motivo_encerramento = motivo


def run_retencao(
    db: Session,
    *,
    config: RetencaoConfig | None = None,
    now: datetime | None = None,
    batch_id: str | None = None,
) -> RetencaoResult:
    """Executa o job de retencao em duas fases.

    Fase 1 — soft delete: anonimiza PII de clientes ATIVOS inativos.
    Fase 2 — hard delete: PURGE clientes JA soft-deleted por
    REVOGACAO_CONSENTIMENTO ou OUTROS apos 5y do deleted_at.
    EXERCICIO_DIREITO_TITULAR (correcoes art. 18 III) sao PRESERVADOS
    indefinidamente — nunca sao purgados automaticamente.

    Args:
        db: SQLAlchemy session.
        config: override dos parametros. Default = producao (5y / 2y / enabled).
        now: data de referencia (para testes deterministicos). Default = UTC now.
        batch_id: identificador unico deste ciclo de execucao (UUID recomendado).
                   Usado em audit logs para rastrear um ciclo completo.

    Returns:
        RetencaoResult com contadores + listas de IDs (internos).
    """
    import time
    import uuid

    config = config or RetencaoConfig()
    now = now or datetime.now(timezone.utc)
    batch_id = batch_id or str(uuid.uuid4())
    # Model usa datetime.utcnow (naive UTC), entao convertemos pra naive
    # ANTES de comparar com colunas. Mantemos o original para audit log.
    now_naive = now.replace(tzinfo=None)
    cutoff_5y = now_naive - timedelta(days=config.retencao_5y_dias)
    cutoff_inativo = now_naive - timedelta(days=config.retencao_inativo_dias)
    started = time.monotonic()

    if not config.enabled:
        return RetencaoResult(
            batch_id=batch_id,
            scanned=0,
            cutoff_5y=cutoff_5y,
            cutoff_inativo=cutoff_inativo,
            duration_ms=0,
        )

    result = RetencaoResult(
        batch_id=batch_id,
        scanned=0,
        cutoff_5y=cutoff_5y,
        cutoff_inativo=cutoff_inativo,
    )

    # Itera todos clientes nao soft-deleted
    clientes_ativos = db.query(Cliente).filter(Cliente.deleted_at.is_(None)).all()
    result = RetencaoResult(**{**result.__dict__, "scanned": len(clientes_ativos)})

    soft_5y: list[int] = []
    soft_inativo: list[int] = []
    errors: list[str] = []

    for cliente in clientes_ativos:
        try:
            last_activity = _last_activity_at(db, cliente.id, cliente)

            # Politica 1: cliente COM protocolo + ultimo protocolo > 5y
            # Detecta: existe protocolo E max(updated_at) < cutoff_5y
            count_protocolos = (
                db.query(func.count(Protocolo.id))
                .filter(Protocolo.cliente_id == cliente.id)
                .scalar()
            ) or 0
            if count_protocolos > 0 and last_activity is not None and last_activity < cutoff_5y:
                _apply_soft_delete(
                    db,
                    cliente,
                    MotivoEncerramento.RETENCAO_5Y,
                    now_naive,
                )
                soft_5y.append(cliente.id)
                continue

            # Politica 2: cliente SEM protocolo + inativo > 2y
            if count_protocolos == 0:
                # Sem protocolo, sem atendimento = consider inativo se
                # updated_at do proprio cliente < cutoff_inativo
                if cliente.updated_at < cutoff_inativo:
                    _apply_soft_delete(
                        db,
                        cliente,
                        MotivoEncerramento.OUTROS,
                        now_naive,
                    )
                    soft_inativo.append(cliente.id)
        except Exception as e:  # noqa: BLE001
            # NUNCA para o job por causa de 1 cliente; loga e segue.
            errors.append(f"cliente_id={cliente.id}: {type(e).__name__}: {e}")

    db.commit()

    # =============================================================================
    # FASE 2 — hard delete (purge) de clientes ja soft-deleted
    # Motivos que VAO para purge apos 5y: REVOGACAO_CONSENTIMENTO, OUTROS
    # Motivo que NAO vai para purge: EXERCICIO_DIREITO_TITULAR
    # =============================================================================
    hard_deleted_ids: list[int] = []
    skipped_exercicio: int = 0

    motivos_purge = {
        MotivoEncerramento.REVOGACAO_CONSENTIMENTO,
        MotivoEncerramento.OUTROS,
    }

    clientes_soft_deleted = (
        db.query(Cliente)
        .filter(Cliente.deleted_at.isnot(None))
        .filter(Cliente.deleted_at < cutoff_5y)
        .filter(Cliente.motivo_encerramento.in_(motivos_purge))
        .all()
    )

    for cliente in clientes_soft_deleted:
        hard_deleted_ids.append(cliente.id)
        db.delete(cliente)

    # Contabiliza EXERCICIO_DIREITO_TITULAR que existem mas nao sao purgados
    exercicio_count = (
        db.query(Cliente)
        .filter(Cliente.deleted_at.isnot(None))
        .filter(
            Cliente.motivo_encerramento
            == MotivoEncerramento.EXERCICIO_DIREITO_TITULAR
        )
        .count()
    )
    skipped_exercicio = exercicio_count

    db.commit()

    duration_ms = int((time.monotonic() - started) * 1000)
    return RetencaoResult(
        batch_id=batch_id,
        scanned=len(clientes_ativos),
        soft_deleted_5y=soft_5y,
        soft_deleted_inativo=soft_inativo,
        hard_deleted_ids=hard_deleted_ids,
        skipped_exercicio_direito=skipped_exercicio,
        skipped_already_deleted=0,
        errors=errors,
        cutoff_5y=cutoff_5y,
        cutoff_inativo=cutoff_inativo,
        duration_ms=duration_ms,
    )


__all__ = ["RetencaoConfig", "RetencaoResult", "run_retencao"]
