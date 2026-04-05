"""
TenantScopedRepository — base class for all tenant-scoped data access.

All methods accept tenant_id and use the tenant-scoped session so the
do_orm_execute event hook automatically adds the WHERE tenant_id = X filter.
No manual WHERE clauses in subclasses or business logic.
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantScopedRepository(Generic[ModelT]):
    def __init__(self, model: Type[ModelT]):
        self.model = model

    async def get_by_id(
        self, session: AsyncSession, record_id: uuid.UUID
    ) -> ModelT | None:
        """Get a single record. Tenant filtering is applied by the event hook."""
        stmt = select(self.model).where(self.model.id == record_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> tuple[Sequence[ModelT], int]:
        """
        List records with pagination. Returns (items, total_count).
        Tenant filter is auto-applied by the event hook.
        """
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        if filters:
            for col, val in filters.items():
                if val is not None:
                    stmt = stmt.where(getattr(self.model, col) == val)
                    count_stmt = count_stmt.where(getattr(self.model, col) == val)

        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await session.execute(stmt)
        items = result.scalars().all()

        return items, total

    async def create(self, session: AsyncSession, data: dict[str, Any]) -> ModelT:
        """Create a new record pre-filled with tenant_id from the session."""
        tenant_id = session.info.get("tenant_id")
        if tenant_id and "tenant_id" not in data:
            data["tenant_id"] = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id

        instance = self.model(**data)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def update(
        self, session: AsyncSession, record_id: uuid.UUID, data: dict[str, Any]
    ) -> ModelT | None:
        """Update a record. Auto-filtered to current tenant."""
        instance = await self.get_by_id(session, record_id)
        if instance is None:
            return None

        for key, value in data.items():
            if value is not None:
                setattr(instance, key, value)

        instance.updated_at = datetime.now(timezone.utc)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def soft_delete(
        self, session: AsyncSession, record_id: uuid.UUID
    ) -> bool:
        """Soft-delete a record. Auto-filtered to current tenant."""
        instance = await self.get_by_id(session, record_id)
        if instance is None:
            return False

        instance.deleted_at = datetime.now(timezone.utc)
        session.add(instance)
        await session.flush()
        return True
