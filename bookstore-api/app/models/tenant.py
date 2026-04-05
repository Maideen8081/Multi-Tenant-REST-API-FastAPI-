from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.author import Author
    from app.models.category import Category


class Tenant(Base, TimestampMixin, SoftDeleteMixin):
    """
    Top-level tenant (company/organisation).
    NOT tenant-scoped itself — lives outside the isolation boundary.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default="free"
    )  # free | pro | enterprise
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active | suspended | offboarded
    rate_limit_override: Mapped[int | None] = mapped_column(nullable=True, default=None)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    books: Mapped[list["Book"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    authors: Mapped[list["Author"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    categories: Mapped[list["Category"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
