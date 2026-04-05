from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TenantScopedMixin, register_tenant_scoped_model

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.author import Author
    from app.models.category import Category


class Book(Base, TenantScopedMixin):
    __tablename__ = "books"
    __table_args__ = (
        Index("ix_books_tenant_id", "tenant_id", "id"),
        Index("ix_books_tenant_isbn", "tenant_id", "isbn"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    published_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # FK to author (also tenant-scoped)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("authors.id", ondelete="SET NULL"),
        nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="books")
    author: Mapped["Author | None"] = relationship(back_populates="books")
    category: Mapped["Category | None"] = relationship(back_populates="books")


# Register with the auto-filter hook
register_tenant_scoped_model(Book)
