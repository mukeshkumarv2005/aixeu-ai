"""Comprehensive Knowledge Base endpoint tests.

Covers KB CRUD, document CRUD within KBs, processing endpoints, semantic
search (pgvector gating), ownership isolation, pagination, and edge cases.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import (
    HAS_PGVECTOR,
    KnowledgeBase,
    KnowledgeBaseDocument,
)
from tests.conftest import auth_header, create_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_KB_BASE = "/api/v1/knowledge-bases"


async def _create_kb(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Test KB",
    description: str | None = None,
    embedding_model: str | None = None,
) -> dict:
    """Create a KB and return the JSON response body."""
    body: dict = {"name": name}
    if description is not None:
        body["description"] = description
    if embedding_model is not None:
        body["embedding_model"] = embedding_model
    resp = await client.post(_KB_BASE, json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def _add_doc(
    client: AsyncClient,
    kb_id: str,
    headers: dict[str, str],
    *,
    title: str = "Doc Title",
    content: str = "Document content here",
    metadata_json: str | None = None,
) -> dict:
    """Add a document to a KB and return the JSON response body."""
    body: dict = {"title": title, "content": content}
    if metadata_json is not None:
        body["metadata_json"] = metadata_json
    resp = await client.post(
        f"{_KB_BASE}/{kb_id}/documents",
        json=body,
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Knowledge Base CRUD
# ---------------------------------------------------------------------------


class TestKnowledgeBaseCRUD:
    """Create, list, get, update, delete knowledge bases."""

    async def test_create_knowledge_base(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Create a KB returns 201 with correct fields."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        resp = await client.post(
            _KB_BASE, json={"name": "My KB"}, headers=headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "My KB"
        assert body["description"] is None
        assert body["embedding_model"] == "text-embedding-3-small"
        assert body["document_count"] == 0
        assert body["total_chunks"] == 0
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body

    async def test_create_knowledge_base_with_description(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Create a KB with optional description."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        body = {"name": "My KB", "description": "A test knowledge base"}
        resp = await client.post(_KB_BASE, json=body, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["description"] == "A test knowledge base"

    async def test_create_knowledge_base_custom_model(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Create a KB with a custom embedding model."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        body = {
            "name": "Custom KB",
            "embedding_model": "text-embedding-ada-002",
        }
        resp = await client.post(_KB_BASE, json=body, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["embedding_model"] == "text-embedding-ada-002"
        assert data["dimension"] == 1536  # MockEmbeddingProvider default

    async def test_create_knowledge_base_without_name_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Create a KB without a required name field returns 422."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        resp = await client.post(_KB_BASE, json={}, headers=headers)
        assert resp.status_code == 422

    async def test_list_knowledge_bases_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """List KBs for a user with none returns empty."""
        user = await create_user(db_session)
        resp = await client.get(
            _KB_BASE,
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_knowledge_bases_with_items(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """List returns the user's KBs."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        await _create_kb(client, headers, name="KB Alpha")
        await _create_kb(client, headers, name="KB Beta")

        resp = await client.get(_KB_BASE, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        names = {item["name"] for item in body["items"]}
        assert names == {"KB Alpha", "KB Beta"}

    async def test_list_knowledge_bases_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """List KBs respects offset and limit."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        for i in range(5):
            await _create_kb(client, headers, name=f"KB {i}")

        resp = await client.get(
            _KB_BASE,
            params={"offset": 0, "limit": 2},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5

    async def test_other_users_kbs_not_visible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User A's KBs do not appear in user B's list."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        await _create_kb(
            client, auth_header(str(user_a.id)), name="Secret KB"
        )

        resp = await client.get(
            _KB_BASE,
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_get_knowledge_base(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Get a single KB by ID."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        created = await _create_kb(client, headers, name="My KB")

        resp = await client.get(
            f"{_KB_BASE}/{created['id']}",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == created["id"]
        assert body["name"] == "My KB"

    async def test_get_knowledge_base_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Get a nonexistent KB returns 404."""
        user = await create_user(db_session)
        resp = await client.get(
            f"{_KB_BASE}/{UUID(int=0)}",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    async def test_get_other_users_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Get of another user's KB returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        created = await _create_kb(
            client, auth_header(str(user_a.id)), name="Secret"
        )

        resp = await client.get(
            f"{_KB_BASE}/{created['id']}",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404

    async def test_update_knowledge_base(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Update KB name and description."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        created = await _create_kb(
            client, headers, name="Old Name", description="Old desc"
        )

        resp = await client.patch(
            f"{_KB_BASE}/{created['id']}",
            json={"name": "New Name", "description": "New desc"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "New Name"
        assert body["description"] == "New desc"
        assert body["id"] == created["id"]

    async def test_update_knowledge_base_partial(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Update only the name, description stays unchanged."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        created = await _create_kb(
            client, headers, name="Original", description="Original desc"
        )

        resp = await client.patch(
            f"{_KB_BASE}/{created['id']}",
            json={"name": "Updated"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Updated"
        assert body["description"] == "Original desc"

    async def test_update_knowledge_base_empty_body(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """PATCH with no fields is a no-op."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        created = await _create_kb(
            client, headers, name="Stable", description="Stable desc"
        )

        resp = await client.patch(
            f"{_KB_BASE}/{created['id']}",
            json={},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Stable"
        assert body["description"] == "Stable desc"

    async def test_update_other_users_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Update of another user's KB returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        created = await _create_kb(
            client, auth_header(str(user_a.id)), name="Mine"
        )

        resp = await client.patch(
            f"{_KB_BASE}/{created['id']}",
            json={"name": "Hacked"},
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404

    async def test_delete_knowledge_base(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delete a KB returns 204 and removes the record."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        created = await _create_kb(client, headers, name="Delete Me")

        resp = await client.delete(
            f"{_KB_BASE}/{created['id']}",
            headers=headers,
        )
        assert resp.status_code == 204

        result = await db_session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == UUID(created["id"])
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_knowledge_base_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delete of nonexistent KB returns 404."""
        user = await create_user(db_session)
        resp = await client.delete(
            f"{_KB_BASE}/{UUID(int=0)}",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_delete_other_users_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delete of another user's KB returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        created = await _create_kb(
            client, auth_header(str(user_a.id)), name="Mine"
        )

        resp = await client.delete(
            f"{_KB_BASE}/{created['id']}",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404

    async def test_double_delete_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Deleting an already-deleted KB returns 404."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        created = await _create_kb(client, headers, name="Double Delete")

        resp1 = await client.delete(
            f"{_KB_BASE}/{created['id']}",
            headers=headers,
        )
        assert resp1.status_code == 204

        resp2 = await client.delete(
            f"{_KB_BASE}/{created['id']}",
            headers=headers,
        )
        assert resp2.status_code == 404

    async def test_unauthorized_access_returns_401(
        self, client: AsyncClient
    ):
        """All KB endpoints require auth."""
        resp = await client.post(
            _KB_BASE, json={"name": "Hack"}
        )
        assert resp.status_code == 401

        resp = await client.get(_KB_BASE)
        assert resp.status_code == 401

        resp = await client.get(f"{_KB_BASE}/{UUID(int=0)}")
        assert resp.status_code == 401

        resp = await client.patch(
            f"{_KB_BASE}/{UUID(int=0)}",
            json={"name": "Hack"},
        )
        assert resp.status_code == 401

        resp = await client.delete(f"{_KB_BASE}/{UUID(int=0)}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Knowledge Base Document CRUD
# ---------------------------------------------------------------------------


class TestDocumentCRUD:
    """Add, list, get, delete documents within a KB."""

    async def test_add_document(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Add a document returns 201 with correct fields."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        resp = await client.post(
            f"{_KB_BASE}/{kb['id']}/documents",
            json={"title": "Test Doc", "content": "Hello world"},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Test Doc"
        assert body["content"] == "Hello world"
        assert body["status"] == "pending"
        assert body["knowledge_base_id"] == kb["id"]
        assert body["chunk_count"] is None
        assert "id" in body
        assert "created_at" in body

    async def test_add_document_with_metadata(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Add a document with optional metadata JSON."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        resp = await client.post(
            f"{_KB_BASE}/{kb['id']}/documents",
            json={
                "title": "Meta Doc",
                "content": "With metadata",
                "metadata_json": '{"source": "test", "page": 1}',
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["metadata_json"] == '{"source": "test", "page": 1}'

    async def test_add_document_without_title_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Add a document without required title/content returns 422."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        resp = await client.post(
            f"{_KB_BASE}/{kb['id']}/documents",
            json={},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_add_document_to_nonexistent_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Add document to a KB that doesn't exist returns 404."""
        user = await create_user(db_session)
        resp = await client.post(
            f"{_KB_BASE}/{UUID(int=0)}/documents",
            json={"title": "Orphan", "content": "No parent"},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_list_documents_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """List documents in an empty KB."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        resp = await client.get(
            f"{_KB_BASE}/{kb['id']}/documents",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_documents_with_items(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """List returns documents in a KB."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        await _add_doc(client, kb["id"], headers, title="Doc A")
        await _add_doc(client, kb["id"], headers, title="Doc B")

        resp = await client.get(
            f"{_KB_BASE}/{kb['id']}/documents",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        titles = {item["title"] for item in body["items"]}
        assert titles == {"Doc A", "Doc B"}

    async def test_list_documents_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """List documents respects offset and limit."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)
        for i in range(5):
            await _add_doc(
                client, kb["id"], headers, title=f"Doc {i}"
            )

        resp = await client.get(
            f"{_KB_BASE}/{kb['id']}/documents",
            params={"offset": 0, "limit": 2},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5

    async def test_list_documents_for_nonexistent_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """List documents for a KB that doesn't exist returns 404."""
        user = await create_user(db_session)
        resp = await client.get(
            f"{_KB_BASE}/{UUID(int=0)}/documents",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_get_document(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Get a single document by ID."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)
        doc = await _add_doc(client, kb["id"], headers, title="Get Me")

        resp = await client.get(
            f"{_KB_BASE}/{kb['id']}/documents/{doc['id']}",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == doc["id"]
        assert body["title"] == "Get Me"
        assert body["content"] == "Document content here"

    async def test_get_document_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Get a nonexistent document returns 404."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        resp = await client.get(
            f"{_KB_BASE}/{kb['id']}/documents/{UUID(int=0)}",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_get_document_wrong_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Get a document passing the wrong KB ID returns 404."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb_a = await _create_kb(client, headers, name="KB A")
        kb_b = await _create_kb(client, headers, name="KB B")
        doc = await _add_doc(client, kb_a["id"], headers, title="In A")

        resp = await client.get(
            f"{_KB_BASE}/{kb_b['id']}/documents/{doc['id']}",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_get_document_in_other_users_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Get a document from another user's KB returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        kb_a = await _create_kb(
            client, auth_header(str(user_a.id)), name="Secret KB"
        )
        doc = await _add_doc(
            client, kb_a["id"], auth_header(str(user_a.id)), title="Secret"
        )

        resp = await client.get(
            f"{_KB_BASE}/{kb_a['id']}/documents/{doc['id']}",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404

    async def test_delete_document(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delete a document returns 204 and removes the record."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)
        doc = await _add_doc(
            client, kb["id"], headers, title="Delete Me"
        )

        resp = await client.delete(
            f"{_KB_BASE}/{kb['id']}/documents/{doc['id']}",
            headers=headers,
        )
        assert resp.status_code == 204

        result = await db_session.execute(
            select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.id == UUID(doc["id"])
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_document_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delete nonexistent document returns 404."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        resp = await client.delete(
            f"{_KB_BASE}/{kb['id']}/documents/{UUID(int=0)}",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_delete_document_in_other_users_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delete a document from another user's KB returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        kb_a = await _create_kb(
            client, auth_header(str(user_a.id)), name="Secret KB"
        )
        doc = await _add_doc(
            client, kb_a["id"], auth_header(str(user_a.id)), title="Secret"
        )

        resp = await client.delete(
            f"{_KB_BASE}/{kb_a['id']}/documents/{doc['id']}",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404

    async def test_kb_document_counts_update(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """KB response reflects document and chunk counts."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        resp = await client.get(
            f"{_KB_BASE}/{kb['id']}", headers=headers
        )
        assert resp.json()["document_count"] == 0

        await _add_doc(client, kb["id"], headers, title="Doc 1")
        resp = await client.get(
            f"{_KB_BASE}/{kb['id']}", headers=headers
        )
        assert resp.json()["document_count"] == 1

        await _add_doc(client, kb["id"], headers, title="Doc 2")
        resp = await client.get(
            f"{_KB_BASE}/{kb['id']}", headers=headers
        )
        assert resp.json()["document_count"] == 2

        docs_resp = await client.get(
            f"{_KB_BASE}/{kb['id']}/documents", headers=headers
        )
        doc_id = docs_resp.json()["items"][0]["id"]
        await client.delete(
            f"{_KB_BASE}/{kb['id']}/documents/{doc_id}",
            headers=headers,
        )

        resp = await client.get(
            f"{_KB_BASE}/{kb['id']}", headers=headers
        )
        assert resp.json()["document_count"] == 1


# ---------------------------------------------------------------------------
# Process Endpoints (pgvector-gated)
# ---------------------------------------------------------------------------


class TestProcessEndpoint:
    """Document processing endpoints."""

    async def test_process_document_without_pgvector_returns_500(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Process a document without pgvector returns 500."""
        if HAS_PGVECTOR:
            pytest.skip("pgvector is available")

        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)
        doc = await _add_doc(
            client, kb["id"], headers,
            title="To Process",
            content="Some content that would be chunked and embedded.",
        )

        resp = await client.post(
            f"{_KB_BASE}/{kb['id']}/documents/{doc['id']}/process",
            headers=headers,
        )
        assert resp.status_code == 500

    async def test_process_knowledge_base_without_pgvector_returns_500(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Batch-process a KB without pgvector returns 500."""
        if HAS_PGVECTOR:
            pytest.skip("pgvector is available")

        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)
        await _add_doc(
            client, kb["id"], headers,
            title="Doc 1",
            content="Content one.",
        )

        resp = await client.post(
            f"{_KB_BASE}/{kb['id']}/process",
            headers=headers,
        )
        assert resp.status_code == 500

    async def test_process_document_without_body(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Process a document without a request body still works."""
        if HAS_PGVECTOR:
            pytest.skip("pgvector is available")

        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)
        doc = await _add_doc(
            client, kb["id"], headers,
            title="No Body",
            content="Testing without request body.",
        )

        resp = await client.post(
            f"{_KB_BASE}/{kb['id']}/documents/{doc['id']}/process",
            headers=headers,
        )
        assert resp.status_code == 500

    async def test_process_nonexistent_document_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Process a document that doesn't exist returns 404."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        resp = await client.post(
            f"{_KB_BASE}/{kb['id']}/documents/{UUID(int=0)}/process",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_process_document_in_other_users_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Process a document in another user's KB returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        kb_a = await _create_kb(
            client, auth_header(str(user_a.id)), name="Secret KB"
        )
        doc = await _add_doc(
            client, kb_a["id"], auth_header(str(user_a.id)),
            title="Secret",
            content="Secret content.",
        )

        resp = await client.post(
            f"{_KB_BASE}/{kb_a['id']}/documents/{doc['id']}/process",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404

    async def test_process_knowledge_base_with_nonexistent_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Batch process a KB that doesn't exist returns 404."""
        user = await create_user(db_session)
        resp = await client.post(
            f"{_KB_BASE}/{UUID(int=0)}/process",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Semantic Search (pgvector-gated)
# ---------------------------------------------------------------------------


class TestSemanticSearch:
    """Semantic search endpoint."""

    async def test_semantic_search_without_pgvector_returns_501(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Search without pgvector returns 501 Not Implemented."""
        if HAS_PGVECTOR:
            pytest.skip("pgvector is available")

        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        kb = await _create_kb(client, headers)

        resp = await client.post(
            f"{_KB_BASE}/{kb['id']}/search",
            json={"query": "test query", "top_k": 5},
            headers=headers,
        )
        assert resp.status_code == 501
        assert "pgvector" in resp.json()["detail"].lower()

    async def test_search_in_other_users_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Search in another user's KB returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        kb_a = await _create_kb(
            client, auth_header(str(user_a.id)), name="Secret KB"
        )

        resp = await client.post(
            f"{_KB_BASE}/{kb_a['id']}/search",
            json={"query": "secret", "top_k": 5},
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404

    async def test_search_nonexistent_kb_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Search in a nonexistent KB returns 404."""
        user = await create_user(db_session)
        resp = await client.post(
            f"{_KB_BASE}/{UUID(int=0)}/search",
            json={"query": "test", "top_k": 5},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404
