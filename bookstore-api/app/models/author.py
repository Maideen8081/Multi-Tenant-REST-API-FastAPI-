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


class Author(Base, TenantScopedMixin):
    __tablename__ = "authors"
    __table_args__ = (
        Index("ix_authors_tenant_id", "tenant_id", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="authors")
    books: Mapped[list["Book"]] = relationship(back_populates="author")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


register_tenant_scoped_model(Author)
