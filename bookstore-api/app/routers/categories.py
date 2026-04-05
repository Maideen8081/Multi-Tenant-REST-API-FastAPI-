from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Query

from app.dependencies.auth import TenantDB, CurrentTenant
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.common import PaginatedResponse
from app.services.category import category_service

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    db: TenantDB,
    tenant: CurrentTenant,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    items, total = await category_service.list(db, page=page, page_size=page_size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(db: TenantDB, tenant: CurrentTenant, payload: CategoryCreate):
    return await category_service.create(db, payload)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: uuid.UUID, db: TenantDB, tenant: CurrentTenant):
    return await category_service.get(db, category_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID, db: TenantDB, tenant: CurrentTenant, payload: CategoryUpdate
):
    return await category_service.update(db, category_id, payload)


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: uuid.UUID, db: TenantDB, tenant: CurrentTenant):
    await category_service.delete(db, category_id)
