from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=not settings.is_production,
    pool_pre_ping=True,
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""

    pass


# ── Tenant-Scoped Session ─────────────────────────────────────────────────────

def make_tenant_session(tenant_id: uuid.UUID) -> AsyncSession:
    """
    Return an AsyncSession pre-configured with tenant_id execution option.
    The do_orm_execute event hook on the session will auto-inject
    a tenant_id filter on every SELECT for tenant-scoped models.
    """
    session = AsyncSessionFactory()
    session.sync_session.info["tenant_id"] = str(tenant_id)
    return session


@asynccontextmanager
async def get_tenant_db(tenant_id: uuid.UUID) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager providing a tenant-scoped database session."""
    async with make_tenant_session(tenant_id) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    """Admin session — no tenant scoping applied."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── DB Lifecycle ──────────────────────────────────────────────────────────────

async def check_db_connection() -> bool:
    """Ping the database to verify connectivity."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_db() -> None:
    await engine.dispose()
