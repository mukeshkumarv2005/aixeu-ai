"""Dashboard API endpoint tests.

Covers the aggregate ``/dashboard`` endpoint and the
``/dashboard/usage`` endpoint — all with ownership enforcement.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from tests.conftest import auth_header, create_user


class TestGetDashboard:
    async def test_empty_dashboard(self, client: AsyncClient, db_session: AsyncSession):
        """Dashboard returns zeroed stats for a new user."""
        user = await create_user(db_session)
        resp = await client.get(
            "/api/v1/dashboard",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_conversations"] == 0
        assert data["stats"]["total_messages"] == 0
        assert data["stats"]["total_files"] == 0
        assert data["stats"]["total_storage_bytes"] == 0
        assert data["stats"]["total_input_tokens"] == 0
        assert data["stats"]["total_output_tokens"] == 0
        assert data["recent_chats"] == []
        assert data["recent_files"] == []
        assert data["recent_activity"] == []

    async def test_with_data(self, client: AsyncClient, db_session: AsyncSession):
        """Dashboard reflects real data after conversations and uploads."""
        user = await create_user(db_session)
        user_id = str(user.id)
        headers = auth_header(user_id)

        # Create a conversation and send a message (creates user + assistant msg)
        conv_resp = await client.post(
            "/api/v1/chat/conversations",
            json={"model": "gpt-4o"},
            headers=headers,
        )
        assert conv_resp.status_code == 201
        conv_id = conv_resp.json()["id"]

        await client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages",
            json={"content": "Hello"},
            headers=headers,
        )

        # Upload a file
        await client.post(
            "/api/v1/storage/upload",
            headers=headers,
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )

        # Fetch dashboard
        resp = await client.get("/api/v1/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        # Stats
        assert data["stats"]["total_conversations"] >= 1
        assert data["stats"]["total_messages"] >= 2  # user + assistant
        assert data["stats"]["total_files"] >= 1
        assert data["stats"]["total_storage_bytes"] >= 11  # "hello world"
        # MockAIProvider returns tokens
        assert data["stats"]["total_input_tokens"] > 0
        assert data["stats"]["total_output_tokens"] > 0

        # Recent chats
        assert len(data["recent_chats"]) >= 1
        assert data["recent_chats"][0]["message_count"] >= 2

        # Recent files
        assert len(data["recent_files"]) >= 1
        assert data["recent_files"][0]["filename"] == "test.txt"

        # Activity feed
        assert len(data["recent_activity"]) >= 1

    async def test_ownership_isolation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User A's data doesn't leak into User B's dashboard."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        # User A creates some data
        headers_a = auth_header(str(user_a.id))
        resp = await client.post(
            "/api/v1/chat/conversations",
            json={"model": "gpt-4o"},
            headers=headers_a,
        )
        assert resp.status_code == 201

        # User B's dashboard should be empty
        resp = await client.get(
            "/api/v1/dashboard",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["total_conversations"] == 0
        assert data["recent_chats"] == []

    async def test_unauthenticated(self, client: AsyncClient):
        """Dashboard returns 401 without auth."""
        resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 401


class TestGetUsage:
    async def test_empty_usage(self, client: AsyncClient, db_session: AsyncSession):
        """Usage returns zeroed data for a new user."""
        user = await create_user(db_session)
        resp = await client.get(
            "/api/v1/dashboard/usage",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_input_tokens"] == 0
        assert data["total_output_tokens"] == 0
        assert data["total_messages"] == 0
        assert data["total_conversations"] == 0
        assert data["daily_usage"] == []
        assert data["storage_total_bytes"] == 0
        assert data["storage_total_files"] == 0

    async def test_with_data(self, client: AsyncClient, db_session: AsyncSession):
        """Usage returns token data after chat messages."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))

        # Create conversation and send message
        conv_resp = await client.post(
            "/api/v1/chat/conversations",
            json={"model": "gpt-4o"},
            headers=headers,
        )
        conv_id = conv_resp.json()["id"]

        await client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages",
            json={"content": "Count tokens"},
            headers=headers,
        )

        resp = await client.get("/api/v1/dashboard/usage", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_input_tokens"] > 0
        assert data["total_output_tokens"] > 0
        assert data["total_messages"] >= 1
        assert data["total_conversations"] >= 1

    async def test_unauthenticated(self, client: AsyncClient):
        """Usage returns 401 without auth."""
        resp = await client.get("/api/v1/dashboard/usage")
        assert resp.status_code == 401
