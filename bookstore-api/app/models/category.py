from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TenantScopedMixin, register_tenant_scoped_model

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.book import Book


class Category(Base, TenantScopedMixin):
    __tablename__ = "categories"
    __table_args__ = (
        Index("ix_categories_tenant_id", "tenant_id", "id"),
        Index("ix_categories_tenant_slug", "tenant_id", "slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="categories")
    books: Mapped[list["Book"]] = relationship(back_populates="category")


register_tenant_scoped_model(Category)
