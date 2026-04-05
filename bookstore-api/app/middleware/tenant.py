"""
Tenant Resolution Middleware

Resolution order:
  1. X-Tenant-ID header  (UUID)
  2. Subdomain           (e.g. acme.api.bookstore.com -> slug "acme")

On success:  request.state.tenant is set to the Tenant ORM object
On failure:
  - Missing / unknown tenant  -> 403 Forbidden
  - Offboarded / soft-deleted -> 410 Gone
"""
from __future__ import annotations

import json
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.database import AsyncSessionFactory
from app.models.tenant import Tenant

settings = get_settings()

# Paths that do NOT require tenant context
_PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}
_ADMIN_PATH_PREFIX = "/admin"


class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self._redis = redis_client

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path

        # Skip tenant resolution for public + admin paths
        if path in _PUBLIC_PATHS or path.startswith(_ADMIN_PATH_PREFIX):
            return await call_next(request)

        tenant = await self._resolve_tenant(request)
        if isinstance(tenant, Response):
            return tenant  # error response

        request.state.tenant = tenant
        return await call_next(request)

    async def _resolve_tenant(self, request: Request) -> Tenant | Response:
        # 1. Try X-Tenant-ID header (UUID)
        tenant_header = request.headers.get("X-Tenant-ID")

        # 2. Try subdomain
        tenant_slug = None
        if not tenant_header:
            host = request.headers.get("host", "")
            parts = host.split(".")
            if len(parts) >= 3:
                tenant_slug = parts[0]

        if not tenant_header and not tenant_slug:
            return _error(403, "MISSING_TENANT", "X-Tenant-ID header or subdomain is required")

        tenant = await self._load_tenant(tenant_header=tenant_header, slug=tenant_slug)

        if tenant is None:
            return _error(403, "INVALID_TENANT", "Tenant not found or invalid credentials")

        if tenant.deleted_at is not None or tenant.status == "offboarded":
            return _error(410, "TENANT_GONE", "This tenant has been offboarded")

        if tenant.status == "suspended":
            return _error(403, "TENANT_SUSPENDED", "This tenant account is suspended")

        return tenant

    async def _load_tenant(
        self, *, tenant_header: str | None, slug: str | None
    ) -> Tenant | None:
        # Check Redis cache first
        cache_key = f"tenant:{tenant_header or slug}"
        if self._redis:
            cached = await self._redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                t = Tenant(**data)
                return t

        # Load from DB
        async with AsyncSessionFactory() as session:
            stmt = select(Tenant)
            if tenant_header:
                try:
                    tid = uuid.UUID(tenant_header)
                    stmt = stmt.where(Tenant.id == tid)
                except ValueError:
                    # Not a UUID — treat as slug
                    stmt = stmt.where(Tenant.slug == tenant_header)
            elif slug:
                stmt = stmt.where(Tenant.slug == slug)

            result = await session.execute(stmt)
            tenant = result.scalar_one_or_none()

        if tenant and self._redis:
            payload = {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "plan": tenant.plan,
                "api_key_hash": tenant.api_key_hash,
                "status": tenant.status,
                "rate_limit_override": tenant.rate_limit_override,
                "contact_email": tenant.contact_email,
                "deleted_at": tenant.deleted_at.isoformat() if tenant.deleted_at else None,
                "created_at": tenant.created_at.isoformat(),
                "updated_at": tenant.updated_at.isoformat(),
            }
            await self._redis.setex(
                cache_key,
                settings.tenant_cache_ttl_seconds,
                json.dumps(payload),
            )

        return tenant


def _error(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "detail": detail}},
    )
