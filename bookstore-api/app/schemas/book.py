from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    isbn: str | None = Field(default=None, max_length=20)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    published_year: int | None = Field(default=None, ge=1000, le=2100)
    stock: int = Field(default=0, ge=0)
    author_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    isbn: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    published_year: int | None = None
    stock: int | None = Field(default=None, ge=0)
    author_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    isbn: str | None
    description: str | None
    price: Decimal | None
    published_year: int | None
    stock: int
    author_id: uuid.UUID | None
    category_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
