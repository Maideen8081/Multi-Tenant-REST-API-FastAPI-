from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Query

from app.dependencies.auth import TenantDB, CurrentTenant
from app.schemas.book import BookCreate, BookUpdate, BookResponse
from app.schemas.common import PaginatedResponse
from app.services.book import book_service

router = APIRouter(prefix="/books", tags=["Books"])


@router.get("", response_model=PaginatedResponse[BookResponse])
async def list_books(
    db: TenantDB,
    tenant: CurrentTenant,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    items, total = await book_service.list(db, page=page, page_size=page_size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=BookResponse, status_code=201)
async def create_book(db: TenantDB, tenant: CurrentTenant, payload: BookCreate):
    return await book_service.create(db, payload)


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: uuid.UUID, db: TenantDB, tenant: CurrentTenant):
    return await book_service.get(db, book_id)


@router.patch("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: uuid.UUID, db: TenantDB, tenant: CurrentTenant, payload: BookUpdate
):
    return await book_service.update(db, book_id, payload)


@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: uuid.UUID, db: TenantDB, tenant: CurrentTenant):
    await book_service.delete(db, book_id)
