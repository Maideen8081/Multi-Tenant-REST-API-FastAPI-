from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.category import category_repo
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    async def get(self, session: AsyncSession, category_id: uuid.UUID):
        cat = await category_repo.get_by_id(session, category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        return cat

    async def list(self, session: AsyncSession, *, page: int, page_size: int):
        return await category_repo.list_all(session, page=page, page_size=page_size)

    async def create(self, session: AsyncSession, data: CategoryCreate):
        return await category_repo.create(session, data.model_dump())

    async def update(
        self, session: AsyncSession, category_id: uuid.UUID, data: CategoryUpdate
    ):
        cat = await category_repo.update(
            session, category_id, data.model_dump(exclude_none=True)
        )
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        return cat

    async def delete(self, session: AsyncSession, category_id: uuid.UUID) -> None:
        deleted = await category_repo.soft_delete(session, category_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Category not found")


category_service = CategoryService()
