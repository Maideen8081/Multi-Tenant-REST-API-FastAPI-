"""
FastAPI Application Factory

Middleware resolution order (outermost = first to receive request):
  CORS → TenantMiddleware → RateLimitMiddleware → Router

TenantMiddleware and RateLimitMiddleware both read `app.state.redis`
at request time, so no circular init needed.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.database import close_db
from app.exceptions.handlers import register_exception_handlers

# Import all models so SQLAlchemy registers them before Alembic / engine use
import app.models.tenant   # noqa: F401
import app.models.book     # noqa: F401
import app.models.author   # noqa: F401
import app.models.category # noqa: F401

settings = get_settings()


# ── Middleware wrappers that pull redis from app.state ─────────────────────────

class TenantMiddlewareWrapper(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from app.middleware.tenant import TenantMiddleware
        redis_client = getattr(request.app.state, "redis", None)
        mw = TenantMiddleware(app=None, redis_client=redis_client)
        return await mw.dispatch(request, call_next)


class RateLimitMiddlewareWrapper(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from app.middleware.rate_limit import RateLimitMiddleware
        redis_client = getattr(request.app.state, "redis", None)
        if redis_client is None:
            return await call_next(request)
        mw = RateLimitMiddleware(app=None, redis_client=redis_client)
        return await mw.dispatch(request, call_next)


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    await redis_client.ping()
    app.state.redis = redis_client

    yield

    # Shutdown
    await redis_client.aclose()
    await close_db()


# ── App Factory ────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    from app.routers import admin, authors, books, categories, health, tenant_mgmt

    app = FastAPI(
        title="Bookstore Multi-Tenant API",
        description=(
            "Production-grade multi-tenant bookstore REST API.\n\n"
            "### Authentication\n"
            "- **Tenant**: pass `X-Tenant-ID` header (UUID or slug)\n"
            "- **Super-Admin**: pass `X-Admin-Key` header\n\n"
            "### Rate Limiting\n"
            "Sliding-window per-tenant: Free=100/min, Pro=1000/min, Enterprise=10k/min.\n"
            "Exceeded quota returns `429` with `Retry-After` header."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS (outermost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "X-Tenant-ID", "X-Admin-Key"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
    )

    # Rate limit runs after tenant is resolved
    app.add_middleware(RateLimitMiddlewareWrapper)
    # Tenant resolution (innermost of the two custom middlewares)
    app.add_middleware(TenantMiddlewareWrapper)

    # Routers
    app.include_router(health.router)
    app.include_router(tenant_mgmt.router)
    app.include_router(admin.router)
    app.include_router(books.router)
    app.include_router(authors.router)
    app.include_router(categories.router)

    # Global exception handlers
    register_exception_handlers(app)

    return app


app = create_app()
