"""
Redis Sliding Window Rate Limiter Middleware

Algorithm:
  - Key:    rl:{tenant_id}
  - Uses a sorted set where score = timestamp (ms)
  - ZADD current_time -> ZREMRANGEBYSCORE old entries -> ZCARD = request count
  - If count > limit: return 429 with Retry-After header

Tenant quota precedence:
  tenant.rate_limit_override > plan default (from settings)
"""
from __future__ import annotations

import math
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings

settings = get_settings()

_ADMIN_PATH_PREFIX = "/admin"
_PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client):
        super().__init__(app)
        self._redis = redis_client

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path

        # Skip rate limiting for public and admin paths
        if path in _PUBLIC_PATHS or path.startswith(_ADMIN_PATH_PREFIX):
            return await call_next(request)

        tenant = getattr(request.state, "tenant", None)
        if tenant is None:
            # TenantMiddleware will have already returned 403 — this shouldn't run
            return await call_next(request)

        allowed, limit, remaining, retry_after = await self._check_rate_limit(tenant)

        if not allowed:
            return JSONResponse(
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(retry_after),
                },
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "detail": f"Rate limit of {limit} requests/min exceeded. "
                                  f"Retry after {retry_after} seconds.",
                    }
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    async def _check_rate_limit(
        self, tenant
    ) -> tuple[bool, int, int, int]:
        """
        Returns: (allowed, limit, remaining, retry_after_seconds)
        """
        # Determine quota
        if tenant.rate_limit_override:
            limit = tenant.rate_limit_override
        else:
            limit = settings.get_rate_limit_for_plan(tenant.plan)

        now_ms = int(time.time() * 1000)
        window_ms = 60 * 1000  # 1-minute sliding window
        window_start_ms = now_ms - window_ms

        key = f"rl:{tenant.id}"

        # Lua script for atomic sliding window
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local member = ARGV[4]

        -- Remove expired entries
        redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

        -- Count current window requests
        local count = redis.call('ZCARD', key)

        if count < limit then
            -- Add this request
            redis.call('ZADD', key, now, member)
            redis.call('PEXPIRE', key, 60000)
            return {1, count + 1}
        else
            return {0, count}
        end
        """
        member = f"{now_ms}"

        result = await self._redis.eval(
            lua_script,
            1,  # numkeys
            key,
            now_ms,
            window_start_ms,
            limit,
            member,
        )

        allowed = bool(result[0])
        count = int(result[1])
        remaining = max(0, limit - count)

        # Retry-After = seconds until oldest request in window expires
        if not allowed:
            # Get the oldest entry in the window
            oldest = await self._redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_ts_ms = int(oldest[0][1])
                retry_after = math.ceil((oldest_ts_ms + window_ms - now_ms) / 1000)
            else:
                retry_after = 60
        else:
            retry_after = 0

        return allowed, limit, remaining, retry_after
