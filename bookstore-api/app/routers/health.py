"""
Health check endpoint — returns system and tenant-aware status.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.database import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check")
async def health_check(request: Request):
    db_ok = await check_db_connection()

    # Try Redis if available
    redis_ok = False
    redis = getattr(request.app.state, "redis", None)
    if redis:
        try:
            redis_ok = await redis.ping()
        except Exception:
            redis_ok = False

    tenant = getattr(request.state, "tenant", None)
    tenant_info = (
        {
            "id": str(tenant.id),
            "slug": tenant.slug,
            "plan": tenant.plan,
            "status": tenant.status,
        }
        if tenant
        else None
    )

    overall = "healthy" if db_ok else "degraded"

    return JSONResponse(
        status_code=200 if overall == "healthy" else 503,
        content={
            "status": overall,
            "services": {
                "database": "ok" if db_ok else "unavailable",
                "redis": "ok" if redis_ok else "unavailable",
            },
            "tenant": tenant_info,
        },
    )
