"""
Tenant Lifecycle Tests — Onboarding and Offboarding

Verifies:
  - Onboarding creates tenant, seeds default categories, returns API key
  - Offboarded tenant requests return 410 Gone
  - Cascade soft-delete removes all child data
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import make_tenant_headers


class TestTenantOnboarding:

    @pytest.mark.asyncio
    async def test_onboard_tenant_returns_api_key_and_seeds_categories(
        self, admin_client: AsyncClient, client: AsyncClient
    ):
        """Provisioning creates tenant, returns API key, and seeds default categories."""
        resp = await admin_client.post(
            "/admin/tenants",
            json={"name": "New Corp", "slug": "new-corp", "plan": "pro"},
        )
        assert resp.status_code == 201
        body = resp.json()

        assert "api_key" in body
        assert body["api_key"].startswith("bk_")
        assert body["slug"] == "new-corp"
        assert body["plan"] == "pro"
        assert body["status"] == "active"

        # Verify default categories were seeded
        import uuid
        tenant_id = uuid.UUID(body["id"])
        resp = await client.get(
            "/categories",
            headers={"X-Tenant-ID": str(tenant_id)},
        )
        assert resp.status_code == 200
        categories = resp.json()["items"]
        slugs = {c["slug"] for c in categories}
        assert "fiction" in slugs
        assert "non-fiction" in slugs
        assert "technology" in slugs

    @pytest.mark.asyncio
    async def test_onboard_duplicate_slug_returns_error(
        self, admin_client: AsyncClient
    ):
        """Duplicate slug returns 400 / 409."""
        payload = {"name": "Dup Co", "slug": "unique-slug-xyz", "plan": "free"}
        resp1 = await admin_client.post("/admin/tenants", json=payload)
        assert resp1.status_code == 201

        resp2 = await admin_client.post("/admin/tenants", json=payload)
        assert resp2.status_code in (400, 409)

    @pytest.mark.asyncio
    async def test_onboard_requires_admin_key(self, client: AsyncClient):
        """Onboarding without X-Admin-Key returns 403."""
        resp = await client.post(
            "/admin/tenants",
            json={"name": "Hacker Corp", "slug": "hacker", "plan": "free"},
        )
        assert resp.status_code == 403


class TestTenantOffboarding:

    @pytest.mark.asyncio
    async def test_offboard_tenant_returns_410_on_subsequent_requests(
        self, admin_client: AsyncClient, client: AsyncClient, tenant_a
    ):
        """After offboarding, any tenant request returns 410 Gone."""
        t_a, _ = tenant_a

        # Create some data first
        await client.post(
            "/books",
            json={"title": "Soon Gone Book"},
            headers=make_tenant_headers(t_a),
        )

        # Offboard the tenant
        resp = await admin_client.delete(f"/admin/tenants/{t_a.id}")
        assert resp.status_code == 204

        # Subsequent requests must return 410
        resp = await client.get("/books", headers=make_tenant_headers(t_a))
        assert resp.status_code == 410
        body = resp.json()
        assert body["error"]["code"] == "TENANT_GONE"

    @pytest.mark.asyncio
    async def test_offboard_cascades_soft_delete_to_books(
        self, admin_client: AsyncClient, client: AsyncClient, tenant_b, db_session
    ):
        """After offboarding, all child records (books, authors, categories) are soft-deleted."""
        from app.repositories.tenant import TenantRepository
        from app.models.book import Book
        from sqlalchemy import select

        t_b, _ = tenant_b

        # Create a book
        resp = await client.post(
            "/books",
            json={"title": "Cascade Book"},
            headers=make_tenant_headers(t_b),
        )
        assert resp.status_code == 201
        book_id = resp.json()["id"]

        # Offboard
        await admin_client.delete(f"/admin/tenants/{t_b.id}")

        # Book should be soft-deleted (deleted_at is set)
        import uuid
        result = await db_session.execute(
            select(Book).where(Book.id == uuid.UUID(book_id))
        )
        book = result.scalar_one_or_none()
        assert book is not None
        assert book.deleted_at is not None, "Book was not soft-deleted after offboarding"

    @pytest.mark.asyncio
    async def test_offboard_nonexistent_tenant_returns_404(
        self, admin_client: AsyncClient
    ):
        """Offboarding a non-existent tenant returns 404."""
        import uuid
        resp = await admin_client.delete(f"/admin/tenants/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_offboard_requires_admin_key(self, client: AsyncClient, tenant_a):
        """Offboarding without admin key returns 403."""
        t_a, _ = tenant_a
        resp = await client.delete(f"/admin/tenants/{t_a.id}")
        assert resp.status_code == 403
