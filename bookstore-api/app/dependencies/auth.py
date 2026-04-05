"""
FastAPI dependencies — tenant, session, authentication.
"""
from __future__ import annotations

import uuid
from typing import Annotated, AsyncGenerator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import make_tenant_session, get_admin_db
from app.models.tenant import Tenant

settings = get_settings()


# ── Tenant ────────────────────────────────────────────────────────────────────

def get_current_tenant(
    request: Request,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-ID", description="Your Tenant Slug or ID")],
) -> Tenant:
    """Extract tenant injected by TenantMiddleware."""
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        raise HTTPException(status_code=403, detail="Tenant context missing")
    return tenant


CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]


# ── Tenant-Scoped DB Session ──────────────────────────────────────────────────

async def get_tenant_db(
    tenant: CurrentTenant,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a tenant-scoped AsyncSession — auto-filtered by tenant_id."""
    session = make_tenant_session(tenant.id)
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


TenantDB = Annotated[AsyncSession, Depends(get_tenant_db)]


# ── Admin DB Session (unscoped) ───────────────────────────────────────────────

async def get_admin_session() -> AsyncGenerator[AsyncSession, None]:
    """Admin session — no tenant filtering."""
    from app.database import AsyncSessionFactory
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


AdminDB = Annotated[AsyncSession, Depends(get_admin_session)]


# ── Super-Admin Auth ──────────────────────────────────────────────────────────

async def verify_super_admin(
    x_admin_key: Annotated[str, Header(alias="X-Admin-Key", description="Super Admin Secret Key")],
) -> None:
    """Verify static super-admin key from X-Admin-Key header."""
    if x_admin_key != settings.super_admin_key:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "UNAUTHORIZED_ADMIN",
                    "detail": "Valid X-Admin-Key header is required for admin access",
                }
            },
        )


SuperAdmin = Annotated[None, Depends(verify_super_admin)]
