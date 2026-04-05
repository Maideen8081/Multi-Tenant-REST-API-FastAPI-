"""
Tenant Service — handles provisioning, offboarding, and API key management.
"""
from __future__ import annotations

import secrets
import uuid

from passlib.context import CryptContext
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.repositories.tenant import TenantRepository
from app.schemas.tenant import TenantCreate, TenantUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
tenant_repo = TenantRepository()

# Default categories seeded for every new tenant
DEFAULT_CATEGORIES = [
    {"name": "Fiction", "slug": "fiction"},
    {"name": "Non-Fiction", "slug": "non-fiction"},
    {"name": "Science", "slug": "science"},
    {"name": "History", "slug": "history"},
    {"name": "Technology", "slug": "technology"},
    {"name": "Children", "slug": "children"},
]


def generate_api_key() -> tuple[str, str]:
    """Returns (raw_key, hashed_key) — store only the hash."""
    raw_key = f"bk_{secrets.token_urlsafe(32)}"
    hashed = pwd_context.hash(raw_key)
    return raw_key, hashed


def verify_api_key(raw_key: str, hashed: str) -> bool:
    return pwd_context.verify(raw_key, hashed)


class TenantService:
    async def provision(
        self, session: AsyncSession, data: TenantCreate
    ) -> tuple[Tenant, str]:
        """
        Create a new tenant, seed default categories, return (tenant, raw_api_key).
        """
        # Check slug uniqueness
        existing = await tenant_repo.get_by_slug(session, data.slug)
        if existing:
            raise ValueError(f"Tenant slug '{data.slug}' is already taken")

        raw_key, hashed_key = generate_api_key()

        tenant = await tenant_repo.create(
            session,
            {
                "name": data.name,
                "slug": data.slug,
                "plan": data.plan,
                "api_key_hash": hashed_key,
                "status": "active",
                "rate_limit_override": data.rate_limit_override,
                "contact_email": str(data.contact_email) if data.contact_email else None,
            },
        )

        # Seed default categories for the new tenant
        from app.models.category import Category

        for cat_data in DEFAULT_CATEGORIES:
            cat = Category(
                tenant_id=tenant.id,
                name=cat_data["name"],
                slug=cat_data["slug"],
            )
            session.add(cat)

        await session.flush()
        return tenant, raw_key

    async def offboard(self, session: AsyncSession, tenant_id: uuid.UUID) -> bool:
        """Soft-delete tenant and cascade to all child records."""
        return await tenant_repo.soft_delete_with_cascade(session, tenant_id)

    async def update(
        self, session: AsyncSession, tenant_id: uuid.UUID, data: TenantUpdate
    ) -> Tenant | None:
        update_dict = data.model_dump(exclude_none=True)
        return await tenant_repo.update(session, tenant_id, update_dict)

    async def list_tenants(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Tenant], int]:
        return await tenant_repo.list_all(
            session, page=page, page_size=page_size, search=search, status=status
        )


tenant_service = TenantService()
