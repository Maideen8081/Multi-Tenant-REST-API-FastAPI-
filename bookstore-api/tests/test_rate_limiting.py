"""
Rate Limiting Tests

Verifies:
  - Tenant A hitting quota returns 429 with Retry-After header
  - Tenant B is completely unaffected when Tenant A is rate-limited
  - Rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining) are present
  - Configurable per-tenant quota override works
"""
from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from app.config import get_settings
from tests.conftest import make_tenant_headers

settings = get_settings()


class TestRateLimiting:

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, client: AsyncClient, tenant_a):
        """Successful requests include rate limit info headers."""
        t_a, _ = tenant_a
        resp = await client.get("/books", headers=make_tenant_headers(t_a))
        assert resp.status_code == 200
        assert "x-ratelimit-limit" in resp.headers
        assert "x-ratelimit-remaining" in resp.headers

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_429(
        self, client: AsyncClient, tenant_a, db_session
    ):
        """
        Override quota to 3 req/min, make 4 requests, assert 429 on 4th.
        """
        t_a, _ = tenant_a

        # Set a very low quota via override
        from app.repositories.tenant import TenantRepository
        repo = TenantRepository()
        await repo.update(db_session, t_a.id, {"rate_limit_override": 3})
        await db_session.commit()

        # Reload tenant with override by refreshing from db
        updated_tenant = await repo.get_by_id(db_session, t_a.id)

        headers = make_tenant_headers(updated_tenant)
        responses = []
        for _ in range(4):
            r = await client.get("/books", headers=headers)
            responses.append(r)

        status_codes = [r.status_code for r in responses]

        # First 3 must succeed, last must be 429
        assert all(s == 200 for s in status_codes[:3]), f"Expected 200s, got {status_codes[:3]}"
        assert status_codes[3] == 429, f"Expected 429, got {status_codes[3]}"

    @pytest.mark.asyncio
    async def test_retry_after_header_present_on_429(
        self, client: AsyncClient, tenant_a, db_session
    ):
        """429 response includes Retry-After header."""
        t_a, _ = tenant_a

        from app.repositories.tenant import TenantRepository
        repo = TenantRepository()
        await repo.update(db_session, t_a.id, {"rate_limit_override": 1})
        await db_session.commit()

        updated = await repo.get_by_id(db_session, t_a.id)
        headers = make_tenant_headers(updated)

        # First request allowed
        await client.get("/books", headers=headers)
        # Second request should be rate-limited
        resp = await client.get("/books", headers=headers)

        assert resp.status_code == 429
        assert "retry-after" in resp.headers
        retry_after = int(resp.headers["retry-after"])
        assert 0 < retry_after <= 60

    @pytest.mark.asyncio
    async def test_tenant_b_unaffected_when_tenant_a_rate_limited(
        self, client: AsyncClient, tenant_a, tenant_b, db_session
    ):
        """Tenant B's quota is completely independent from Tenant A."""
        t_a, _ = tenant_a
        t_b, _ = tenant_b

        from app.repositories.tenant import TenantRepository
        repo = TenantRepository()
        await repo.update(db_session, t_a.id, {"rate_limit_override": 1})
        await db_session.commit()

        updated_a = await repo.get_by_id(db_session, t_a.id)
        headers_a = make_tenant_headers(updated_a)
        headers_b = make_tenant_headers(t_b)

        # Exhaust Tenant A
        await client.get("/books", headers=headers_a)
        r_a = await client.get("/books", headers=headers_a)
        assert r_a.status_code == 429

        # Tenant B must still work fine
        r_b = await client.get("/books", headers=headers_b)
        assert r_b.status_code == 200, (
            f"Tenant B wrongly rate-limited! Status: {r_b.status_code}"
        )

    @pytest.mark.asyncio
    async def test_rate_limit_error_body_structure(
        self, client: AsyncClient, tenant_a, db_session
    ):
        """429 body follows standard error structure with RATE_LIMIT_EXCEEDED code."""
        t_a, _ = tenant_a

        from app.repositories.tenant import TenantRepository
        repo = TenantRepository()
        await repo.update(db_session, t_a.id, {"rate_limit_override": 1})
        await db_session.commit()

        updated = await repo.get_by_id(db_session, t_a.id)
        headers = make_tenant_headers(updated)

        await client.get("/books", headers=headers)
        resp = await client.get("/books", headers=headers)

        assert resp.status_code == 429
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry" in body["error"]["detail"] or "retry" in body["error"]["detail"].lower()
