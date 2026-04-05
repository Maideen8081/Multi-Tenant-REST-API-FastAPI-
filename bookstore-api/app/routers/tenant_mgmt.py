"""
Tenant management endpoints — onboarding and offboarding.
Protected by X-Admin-Key (super-admin only).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.dependencies.auth import AdminDB, SuperAdmin
from app.repositories.tenant import TenantRepository
from app.schemas.tenant import TenantCreate, TenantProvisionResponse, TenantUpdate, TenantResponse
from app.services.tenant import tenant_service

router = APIRouter(prefix="/admin/tenants", tags=["Tenant Management"])
tenant_repo = TenantRepository()


@router.post(
    "",
    response_model=TenantProvisionResponse,
    status_code=201,
    summary="Provision a new tenant",
    description="Creates a tenant record, seeds default categories, and returns the API key (shown once).",
)
async def onboard_tenant(
    _: SuperAdmin,
    db: AdminDB,
    payload: TenantCreate,
):
    tenant, raw_api_key = await tenant_service.provision(db, payload)
    return TenantProvisionResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        status=tenant.status,
        contact_email=tenant.contact_email,
        rate_limit_override=tenant.rate_limit_override,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        api_key=raw_api_key,
    )


@router.delete(
    "/{tenant_id}",
    status_code=204,
    summary="Offboard (soft-delete) a tenant",
    description="Soft-deletes the tenant and cascades deletion to all books, authors, and categories.",
)
async def offboard_tenant(
    tenant_id: uuid.UUID,
    _: SuperAdmin,
    db: AdminDB,
):
    success = await tenant_service.offboard(db, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")


@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant details",
)
async def update_tenant(
    tenant_id: uuid.UUID,
    _: SuperAdmin,
    db: AdminDB,
    payload: TenantUpdate,
):
    tenant = await tenant_service.update(db, tenant_id, payload)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
