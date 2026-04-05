"""
Shared test fixtures using testcontainers for isolated PostgreSQL + Redis.

Key fixtures:
  - engine        : AsyncEngine connected to throwaway Postgres container
  - db_session    : Admin AsyncSession (unscoped)
  - tenant_a/b    : Two provisioned test tenants
  - client        : httpx.AsyncClient bound to the FastAPI app
  - tenant_client : Helper to get a client pre-configured for a specific tenant
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── testcontainers ────────────────────────────────────────────────────────────
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# ── App imports ───────────────────────────────────────────────────────────────
from app.config import get_settings
from app.database import Base
from app.main import create_app
from app.models.tenant import Tenant
from app.services.tenant import tenant_service, DEFAULT_CATEGORIES
from app.schemas.tenant import TenantCreate

import app.models.book     # noqa: F401  — register models
import app.models.author   # noqa: F401
import app.models.category # noqa: F401

# ── Postgres container (session-scoped = shared across all tests) ─────────────

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as rd:
        yield rd


# ── Async engine + tables ─────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container):
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )
    _engine = create_async_engine(url, echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Unscoped (admin) session for test setup."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ── Tenant fixtures ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def tenant_a(db_session) -> tuple[Tenant, str]:
    """Provision Tenant A (free plan). Returns (tenant, raw_api_key)."""
    slug = f"tenant-a-{uuid.uuid4().hex[:6]}"
    data = TenantCreate(name="Tenant Alpha", slug=slug, plan="free")
    tenant, api_key = await tenant_service.provision(db_session, data)
    await db_session.commit()
    return tenant, api_key


@pytest_asyncio.fixture(scope="function")
async def tenant_b(db_session) -> tuple[Tenant, str]:
    """Provision Tenant B (pro plan). Returns (tenant, raw_api_key)."""
    slug = f"tenant-b-{uuid.uuid4().hex[:6]}"
    data = TenantCreate(name="Tenant Beta", slug=slug, plan="pro")
    tenant, api_key = await tenant_service.provision(db_session, data)
    await db_session.commit()
    return tenant, api_key


# ── FastAPI test client ────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def app_instance(engine, redis_container):
    """FastAPI app wired to test containers."""
    import redis.asyncio as aioredis

    redis_url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}/1"

    test_app = create_app()

    # Override DB engine
    from app import database as db_module
    db_module.engine = engine
    db_module.AsyncSessionFactory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    redis_client = aioredis.from_url(redis_url, decode_responses=True)
    test_app.state.redis = redis_client

    yield test_app

    await redis_client.aclose()


@pytest_asyncio.fixture(scope="function")
async def client(app_instance) -> AsyncGenerator[AsyncClient, None]:
    """Base HTTPX client (no tenant header)."""
    async with AsyncClient(
        transport=ASGITransport(app=app_instance), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def admin_client(app_instance) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX client with super-admin key."""
    settings = get_settings()
    async with AsyncClient(
        transport=ASGITransport(app=app_instance),
        base_url="http://test",
        headers={"X-Admin-Key": settings.super_admin_key},
    ) as c:
        yield c


def make_tenant_headers(tenant: Tenant) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant.id)}
