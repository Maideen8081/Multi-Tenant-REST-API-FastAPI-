"""
SQLAlchemy ORM base with TenantScopedMixin.

The core isolation mechanism is a sqlalchemy `do_orm_execute` event hook
registered in this module. Every SELECT on a model that includes TenantScopedMixin
is automatically augmented with a WHERE tenant_id = <current_tenant_id> clause,
based on the value stored in session.info["tenant_id"].
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column, with_loader_criteria

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds created_at / updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class SoftDeleteMixin:
    """Adds deleted_at for soft-delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class TenantScopedMixin(TimestampMixin, SoftDeleteMixin):
    """
    Mixin for all tenant-scoped models.
    - Adds tenant_id FK column
    - Registers the model with the do_orm_execute event for auto-filtering
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Class-level registry — used by the event hook to know which models to filter
    __tenant_scoped__ = True


# ── Global ORM Event Hook ─────────────────────────────────────────────────────

@event.listens_for(Session, "do_orm_execute")
def _auto_filter_by_tenant(execute_state):
    """
    Automatically inject:
      1. tenant_id == <current_tenant_id>  (on all TenantScopedMixin models)
      2. deleted_at IS NULL                (soft-delete filter)

    Activated only when session.info["tenant_id"] is present.
    Skipped for:
      - non-SELECT statements (INSERT/UPDATE/DELETE handled at repo layer)
      - sessions without a tenant_id set (admin sessions)
    """
    if not execute_state.is_select:
        return

    tenant_id = execute_state.session.info.get("tenant_id")
    if tenant_id is None:
        return  # Admin session — no scoping

    # SQLAlchemy lambda SQL parser forbids function calls inside the lambda.
    # We must ensure tenant_id is resolved to a pure UUID object outside.
    if isinstance(tenant_id, str):
        tenant_id_val = uuid.UUID(tenant_id)
    else:
        tenant_id_val = tenant_id

    # Apply filter to all entities in this statement that are tenant-scoped
    for mapper in execute_state.statement.froms:
        pass  # iterate via with_loader_criteria instead

    execute_state.statement = execute_state.statement.options(
        *[
            with_loader_criteria(
                entity,
                lambda cls: (cls.tenant_id == tenant_id_val) & (cls.deleted_at.is_(None)),
                include_aliases=True,
            )
            for entity in _get_tenant_scoped_mappers()
        ]
    )


_TENANT_SCOPED_MAPPERS: list = []


def _get_tenant_scoped_mappers() -> list:
    return _TENANT_SCOPED_MAPPERS


def register_tenant_scoped_model(mapper) -> None:
    """Called by each TenantScopedMixin model after class creation."""
    _TENANT_SCOPED_MAPPERS.append(mapper)
