from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.book import book_repo
from app.schemas.book import BookCreate, BookUpdate


class BookService:
    async def get(self, session: AsyncSession, book_id: uuid.UUID):
        book = await book_repo.get_by_id(session, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

    async def list(self, session: AsyncSession, *, page: int, page_size: int):
        return await book_repo.list_all(session, page=page, page_size=page_size)

    async def create(self, session: AsyncSession, data: BookCreate):
        return await book_repo.create(session, data.model_dump())

    async def update(self, session: AsyncSession, book_id: uuid.UUID, data: BookUpdate):
        book = await book_repo.update(
            session, book_id, data.model_dump(exclude_none=True)
        )
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

    async def delete(self, session: AsyncSession, book_id: uuid.UUID) -> None:
        deleted = await book_repo.soft_delete(session, book_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Book not found")


book_service = BookService()
