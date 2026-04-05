"""
Super-admin router — cross-tenant list/search with full visibility.
All endpoints require X-Admin-Key header.
"""
from __future__ import annotations

import math

from fastapi import APIRouter, Query

from app.dependencies.auth import AdminDB, SuperAdmin
from app.repositories.tenant import TenantRepository
from app.schemas.common import PaginatedResponse
from app.schemas.tenant import TenantResponse

router = APIRouter(prefix="/admin", tags=["Super Admin"])
tenant_repo = TenantRepository()


@router.get(
    "/tenants",
    response_model=PaginatedResponse[TenantResponse],
    summary="List all tenants (cross-tenant)",
)
async def list_all_tenants(
    _: SuperAdmin,
    db: AdminDB,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by name or slug"),
    status: str | None = Query(default=None, pattern=r"^(active|suspended|offboarded)$"),
):
    tenants, total = await tenant_repo.list_all(
        db, page=page, page_size=page_size, search=search, status=status
    )
    return PaginatedResponse(
        items=tenants,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Get a specific tenant by ID",
)
async def get_tenant(
    tenant_id: str,
    _: SuperAdmin,
    db: AdminDB,
):
    import uuid
    from fastapi import HTTPException

    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant UUID")

    tenant = await tenant_repo.get_by_id(db, tid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
