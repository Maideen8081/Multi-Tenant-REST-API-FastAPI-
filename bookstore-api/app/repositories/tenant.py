from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


class TenantRepository:
    """
    Unscoped repository for Tenant management.
    Operates across all tenants — used by admin and middleware only.
    """

    async def get_by_id(self, session: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, session: AsyncSession, slug: str) -> Tenant | None:
        result = await session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_api_key_hash(
        self, session: AsyncSession, key_hash: str
    ) -> Tenant | None:
        result = await session.execute(
            select(Tenant).where(Tenant.api_key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, data: dict) -> Tenant:
        tenant = Tenant(**data)
        session.add(tenant)
        await session.flush()
        await session.refresh(tenant)
        return tenant

    async def update(
        self, session: AsyncSession, tenant_id: uuid.UUID, data: dict
    ) -> Tenant | None:
        tenant = await self.get_by_id(session, tenant_id)
        if tenant is None:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(tenant, k, v)
        tenant.updated_at = datetime.now(timezone.utc)
        session.add(tenant)
        await session.flush()
        await session.refresh(tenant)
        return tenant

    async def soft_delete_with_cascade(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> bool:
        """
        Soft-delete tenant and cascade soft-delete to all child records.
        Child tables (books, authors, categories) are cascaded via FK ON DELETE CASCADE
        for hard deletes; for soft-delete we update deleted_at manually.
        """
        tenant = await self.get_by_id(session, tenant_id)
        if tenant is None:
            return False

        now = datetime.now(timezone.utc)

        # Cascade soft-delete to all child tables
        from app.models.book import Book
        from app.models.author import Author
        from app.models.category import Category

        for ChildModel in (Book, Author, Category):
            await session.execute(
                update(ChildModel)
                .where(ChildModel.tenant_id == tenant_id)
                .where(ChildModel.deleted_at.is_(None))
                .values(deleted_at=now)
            )

        tenant.deleted_at = now
        tenant.status = "offboarded"
        session.add(tenant)
        await session.flush()
        return True

    async def list_all(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Tenant], int]:
        from sqlalchemy import func

        stmt = select(Tenant)
        count_stmt = select(func.count()).select_from(Tenant)

        if search:
            like = f"%{search}%"
            stmt = stmt.where(Tenant.name.ilike(like) | Tenant.slug.ilike(like))
            count_stmt = count_stmt.where(Tenant.name.ilike(like) | Tenant.slug.ilike(like))

        if status:
            stmt = stmt.where(Tenant.status == status)
            count_stmt = count_stmt.where(Tenant.status == status)

        total = (await session.execute(count_stmt)).scalar_one()
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        items = (await session.execute(stmt)).scalars().all()
        return list(items), total
