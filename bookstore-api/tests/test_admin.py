"""
Super-Admin Tests — cross-tenant operations.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import make_tenant_headers


class TestSuperAdmin:

    @pytest.mark.asyncio
    async def test_admin_list_tenants_returns_all(
        self, admin_client: AsyncClient, tenant_a, tenant_b
    ):
        """Admin can list all tenants across the platform."""
        resp = await admin_client.get("/admin/tenants")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 2

    @pytest.mark.asyncio
    async def test_admin_list_tenants_pagination(self, admin_client: AsyncClient):
        """Admin list supports pagination."""
        resp = await admin_client.get("/admin/tenants?page=1&page_size=5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 5

    @pytest.mark.asyncio
    async def test_admin_search_tenants_by_name(
        self, admin_client: AsyncClient, tenant_a
    ):
        """Admin can search tenants by name."""
        t_a, _ = tenant_a
        resp = await admin_client.get(f"/admin/tenants?search={t_a.slug[:8]}")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(item["id"] == str(t_a.id) for item in items)

    @pytest.mark.asyncio
    async def test_admin_get_tenant_by_id(self, admin_client: AsyncClient, tenant_a):
        """Admin can retrieve a specific tenant by ID."""
        t_a, _ = tenant_a
        resp = await admin_client.get(f"/admin/tenants/{t_a.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(t_a.id)

    @pytest.mark.asyncio
    async def test_admin_get_nonexistent_tenant_returns_404(
        self, admin_client: AsyncClient
    ):
        import uuid
        resp = await admin_client.get(f"/admin/tenants/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_update_tenant_plan(
        self, admin_client: AsyncClient, tenant_a
    ):
        """Admin can update tenant plan."""
        t_a, _ = tenant_a
        resp = await admin_client.patch(
            f"/admin/tenants/{t_a.id}", json={"plan": "pro"}
        )
        assert resp.status_code == 200
        assert resp.json()["plan"] == "pro"

    @pytest.mark.asyncio
    async def test_admin_filter_tenants_by_status(
        self, admin_client: AsyncClient, tenant_a, tenant_b
    ):
        """Admin can filter tenants by status."""
        resp = await admin_client.get("/admin/tenants?status=active")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "active"

    @pytest.mark.asyncio
    async def test_non_admin_cannot_list_tenants(self, client: AsyncClient, tenant_a):
        """Regular tenant request to admin endpoints returns 403."""
        t_a, _ = tenant_a
        resp = await client.get(
            "/admin/tenants", headers=make_tenant_headers(t_a)
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_wrong_admin_key_returns_403(self, client: AsyncClient):
        """Wrong X-Admin-Key returns 403."""
        resp = await client.get(
            "/admin/tenants", headers={"X-Admin-Key": "wrong-key"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Health endpoint always responds."""
        resp = await client.get("/health")
        assert resp.status_code in (200, 503)
        body = resp.json()
        assert "status" in body
        assert "services" in body
        assert "database" in body["services"]
