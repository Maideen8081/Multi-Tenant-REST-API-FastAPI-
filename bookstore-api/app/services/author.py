from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.author import author_repo
from app.schemas.author import AuthorCreate, AuthorUpdate


class AuthorService:
    async def get(self, session: AsyncSession, author_id: uuid.UUID):
        author = await author_repo.get_by_id(session, author_id)
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
        return author

    async def list(self, session: AsyncSession, *, page: int, page_size: int):
        return await author_repo.list_all(session, page=page, page_size=page_size)

    async def create(self, session: AsyncSession, data: AuthorCreate):
        return await author_repo.create(session, data.model_dump())

    async def update(self, session: AsyncSession, author_id: uuid.UUID, data: AuthorUpdate):
        author = await author_repo.update(
            session, author_id, data.model_dump(exclude_none=True)
        )
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
        return author

    async def delete(self, session: AsyncSession, author_id: uuid.UUID) -> None:
        deleted = await author_repo.soft_delete(session, author_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Author not found")


author_service = AuthorService()
