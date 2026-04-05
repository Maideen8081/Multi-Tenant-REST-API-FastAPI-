"""
Books CRUD Tests — tenant-scoped operations.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import make_tenant_headers


class TestBooks:

    @pytest.mark.asyncio
    async def test_create_book(self, client: AsyncClient, tenant_a):
        t_a, _ = tenant_a
        resp = await client.post(
            "/books",
            json={
                "title": "The Great Gatsby",
                "isbn": "9780743273565",
                "price": "12.99",
                "published_year": 1925,
                "stock": 50,
            },
            headers=make_tenant_headers(t_a),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "The Great Gatsby"
        assert body["isbn"] == "9780743273565"
        assert str(body["tenant_id"]) == str(t_a.id)

    @pytest.mark.asyncio
    async def test_list_books_pagination(self, client: AsyncClient, tenant_a):
        t_a, _ = tenant_a
        headers = make_tenant_headers(t_a)

        # Create 5 books
        for i in range(5):
            await client.post("/books", json={"title": f"Book {i}"}, headers=headers)

        resp = await client.get("/books?page=1&page_size=3", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 3
        assert body["page"] == 1
        assert body["page_size"] == 3
        assert "total" in body
        assert "pages" in body

    @pytest.mark.asyncio
    async def test_get_book_by_id(self, client: AsyncClient, tenant_a):
        t_a, _ = tenant_a
        headers = make_tenant_headers(t_a)

        create_resp = await client.post("/books", json={"title": "Dune"}, headers=headers)
        book_id = create_resp.json()["id"]

        resp = await client.get(f"/books/{book_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Dune"

    @pytest.mark.asyncio
    async def test_update_book(self, client: AsyncClient, tenant_a):
        t_a, _ = tenant_a
        headers = make_tenant_headers(t_a)

        create_resp = await client.post("/books", json={"title": "Old Title"}, headers=headers)
        book_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/books/{book_id}",
            json={"title": "New Title", "stock": 99},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"
        assert resp.json()["stock"] == 99

    @pytest.mark.asyncio
    async def test_soft_delete_book(self, client: AsyncClient, tenant_a):
        t_a, _ = tenant_a
        headers = make_tenant_headers(t_a)

        create_resp = await client.post("/books", json={"title": "To Delete"}, headers=headers)
        book_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/books/{book_id}", headers=headers)
        assert delete_resp.status_code == 204

        # Should return 404 after soft-delete
        get_resp = await client.get(f"/books/{book_id}", headers=headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_book_returns_404(self, client: AsyncClient, tenant_a):
        t_a, _ = tenant_a
        resp = await client.get(f"/books/{uuid.uuid4()}", headers=make_tenant_headers(t_a))
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_book_invalid_payload_returns_422(
        self, client: AsyncClient, tenant_a
    ):
        t_a, _ = tenant_a
        # Missing required field 'title'
        resp = await client.post(
            "/books", json={"stock": -1}, headers=make_tenant_headers(t_a)
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"
