"""
Tenant Isolation Tests

Critical guarantee: data created in Tenant A must be INVISIBLE from Tenant B,
even with direct ID manipulation. Cross-tenant leakage must be impossible.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import make_tenant_headers


class TestTenantIsolation:
    """Data isolation between two independent tenants."""

    @pytest.mark.asyncio
    async def test_book_created_in_tenant_a_invisible_from_tenant_b(
        self, client: AsyncClient, tenant_a, tenant_b
    ):
        """Book created for Tenant A returns 404 when fetched as Tenant B."""
        t_a, _ = tenant_a
        t_b, _ = tenant_b
        headers_a = make_tenant_headers(t_a)
        headers_b = make_tenant_headers(t_b)

        # Create a book as Tenant A
        resp = await client.post(
            "/books",
            json={"title": "Tenant A Secret Book", "stock": 5},
            headers=headers_a,
        )
        assert resp.status_code == 201
        book_id = resp.json()["id"]

        # Attempt to fetch it as Tenant B — must be 404
        resp = await client.get(f"/books/{book_id}", headers=headers_b)
        assert resp.status_code == 404, (
            f"Cross-tenant data leakage! Tenant B accessed Tenant A's book: {resp.json()}"
        )

    @pytest.mark.asyncio
    async def test_tenant_b_list_cannot_see_tenant_a_books(
        self, client: AsyncClient, tenant_a, tenant_b
    ):
        """Tenant B list endpoint returns empty list even if Tenant A has data."""
        t_a, _ = tenant_a
        t_b, _ = tenant_b

        # Create 3 books for Tenant A
        for i in range(3):
            resp = await client.post(
                "/books",
                json={"title": f"Book {i}", "stock": i},
                headers=make_tenant_headers(t_a),
            )
            assert resp.status_code == 201

        # Tenant B list must return their own books only (default categories were seeded)
        resp = await client.get("/books", headers=make_tenant_headers(t_b))
        assert resp.status_code == 200
        items = resp.json()["items"]
        for item in items:
            assert str(item["tenant_id"]) == str(t_b.id), (
                f"Book from wrong tenant found! Expected {t_b.id}, got {item['tenant_id']}"
            )

    @pytest.mark.asyncio
    async def test_author_cross_tenant_isolation(
        self, client: AsyncClient, tenant_a, tenant_b
    ):
        """Author created in Tenant A not visible from Tenant B."""
        t_a, _ = tenant_a
        t_b, _ = tenant_b

        resp = await client.post(
            "/authors",
            json={"first_name": "Jane", "last_name": "Doe"},
            headers=make_tenant_headers(t_a),
        )
        assert resp.status_code == 201
        author_id = resp.json()["id"]

        resp = await client.get(f"/authors/{author_id}", headers=make_tenant_headers(t_b))
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_category_cross_tenant_isolation(
        self, client: AsyncClient, tenant_a, tenant_b
    ):
        """Category created in Tenant A not visible from Tenant B."""
        t_a, _ = tenant_a
        t_b, _ = tenant_b

        resp = await client.post(
            "/categories",
            json={"name": "Sports", "slug": "sports"},
            headers=make_tenant_headers(t_a),
        )
        assert resp.status_code == 201
        cat_id = resp.json()["id"]

        resp = await client.get(f"/categories/{cat_id}", headers=make_tenant_headers(t_b))
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_in_tenant_a_has_no_effect_on_tenant_b(
        self, client: AsyncClient, tenant_a, tenant_b
    ):
        """Deleting a resource in Tenant A does not affect Tenant B's identical-ID resource."""
        t_a, _ = tenant_a
        t_b, _ = tenant_b

        # Create book in Tenant B
        resp_b = await client.post(
            "/books",
            json={"title": "Tenant B Book"},
            headers=make_tenant_headers(t_b),
        )
        assert resp_b.status_code == 201
        book_b_id = resp_b.json()["id"]

        # Create book in Tenant A
        resp_a = await client.post(
            "/books",
            json={"title": "Tenant A Book"},
            headers=make_tenant_headers(t_a),
        )
        assert resp_a.status_code == 201
        book_a_id = resp_a.json()["id"]

        # Delete Tenant A's book
        resp = await client.delete(f"/books/{book_a_id}", headers=make_tenant_headers(t_a))
        assert resp.status_code == 204

        # Tenant B's book must still exist
        resp = await client.get(f"/books/{book_b_id}", headers=make_tenant_headers(t_b))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_tenant_header_returns_403(self, client: AsyncClient):
        """No X-Tenant-ID header → 403 with structured error."""
        resp = await client.get("/books")
        assert resp.status_code == 403
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "MISSING_TENANT"

    @pytest.mark.asyncio
    async def test_invalid_tenant_id_returns_403(self, client: AsyncClient):
        """Unknown tenant ID → 403."""
        import uuid
        resp = await client.get("/books", headers={"X-Tenant-ID": str(uuid.uuid4())})
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "INVALID_TENANT"
