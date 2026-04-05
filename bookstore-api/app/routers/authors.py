from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Query

from app.dependencies.auth import TenantDB, CurrentTenant
from app.schemas.author import AuthorCreate, AuthorUpdate, AuthorResponse
from app.schemas.common import PaginatedResponse
from app.services.author import author_service

router = APIRouter(prefix="/authors", tags=["Authors"])


@router.get("", response_model=PaginatedResponse[AuthorResponse])
async def list_authors(
    db: TenantDB,
    tenant: CurrentTenant,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    items, total = await author_service.list(db, page=page, page_size=page_size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=AuthorResponse, status_code=201)
async def create_author(db: TenantDB, tenant: CurrentTenant, payload: AuthorCreate):
    return await author_service.create(db, payload)


@router.get("/{author_id}", response_model=AuthorResponse)
async def get_author(author_id: uuid.UUID, db: TenantDB, tenant: CurrentTenant):
    return await author_service.get(db, author_id)


@router.patch("/{author_id}", response_model=AuthorResponse)
async def update_author(
    author_id: uuid.UUID, db: TenantDB, tenant: CurrentTenant, payload: AuthorUpdate
):
    return await author_service.update(db, author_id, payload)


@router.delete("/{author_id}", status_code=204)
async def delete_author(author_id: uuid.UUID, db: TenantDB, tenant: CurrentTenant):
    await author_service.delete(db, author_id)
