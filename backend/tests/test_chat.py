"""Comprehensive chat endpoint tests.

Covers conversation CRUD, message listing, and SSE streaming — all with
ownership enforcement and edge cases.
"""

from __future__ import annotations

import json
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from tests.conftest import auth_header, create_user


# ─── Helpers ──────────────────────────────────────────────────────────────


async def _create_conv(
    client: AsyncClient,
    user_id: str,
    title: str | None = None,
    model: str = "gpt-4o",
) -> dict:
    """Create a conversation and return the response JSON."""
    body: dict = {"model": model}
    if title is not None:
        body["title"] = title
    resp = await client.post(
        "/api/v1/chat/conversations",
        json=body,
        headers=auth_header(user_id),
    )
    assert resp.status_code == 201
    return resp.json()


# ─── Conversation CRUD ────────────────────────────────────────────────────


class TestCreateConversation:
    async def test_success(self, client: AsyncClient, db_session: AsyncSession):
        """Create a conversation returns 201 with metadata."""
        user = await create_user(db_session)
        body = {"title": "My Chat", "model": "gpt-4o"}
        resp = await client.post(
            "/api/v1/chat/conversations",
            json=body,
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My Chat"
        assert data["model"] == "gpt-4o"
        assert not data["is_archived"]
        assert data["message_count"] == 0
        assert "id" in data
        assert "created_at" in data

        # Record exists in DB
        result = await db_session.execute(
            select(Conversation).where(Conversation.id == UUID(data["id"]))
        )
        conv = result.scalar_one_or_none()
        assert conv is not None
        assert conv.title == "My Chat"
        assert conv.user_id == user.id

    async def test_default_model(self, client: AsyncClient, db_session: AsyncSession):
        """Create without model defaults to gpt-4o."""
        user = await create_user(db_session)
        resp = await client.post(
            "/api/v1/chat/conversations",
            json={},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 201
        assert resp.json()["model"] == "gpt-4o"

    async def test_unauthenticated(self, client: AsyncClient):
        """Create without auth returns 401."""
        resp = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Test"},
        )
        assert resp.status_code == 401


class TestListConversations:
    async def test_empty(self, client: AsyncClient, db_session: AsyncSession):
        """List conversations for a user with none returns empty."""
        user = await create_user(db_session)
        resp = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["conversations"] == []
        assert body["total"] == 0

    async def test_with_conversations(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """List returns the user's conversations with message counts."""
        user = await create_user(db_session)
        conv1 = await _create_conv(client, str(user.id), title="First")
        conv2 = await _create_conv(client, str(user.id), title="Second")

        resp = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        titles = {c["title"] for c in body["conversations"]}
        assert titles == {"First", "Second"}
        # All have 0 message_count
        for c in body["conversations"]:
            assert c["message_count"] == 0

    async def test_does_not_include_archived(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Archived conversations are excluded from the list."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id), title="Archivable")

        # Archive it
        await client.put(
            f"/api/v1/chat/conversations/{conv['id']}",
            json={"is_archived": True},
            headers=auth_header(str(user.id)),
        )

        resp = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_other_users_conversations_not_visible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """A user only sees their own conversations."""
        user_a = await create_user(db_session, email="a@test.com", username="usera")
        user_b = await create_user(db_session, email="b@test.com", username="userb")

        await _create_conv(client, str(user_a.id), title="A's Chat")

        resp = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestUpdateConversation:
    async def test_rename(self, client: AsyncClient, db_session: AsyncSession):
        """Update title returns updated conversation."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id), title="Old Title")

        resp = await client.put(
            f"/api/v1/chat/conversations/{conv['id']}",
            json={"title": "New Title"},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

        # Verify DB
        result = await db_session.execute(
            select(Conversation).where(Conversation.id == UUID(conv["id"]))
        )
        assert result.scalar_one().title == "New Title"

    async def test_archive(self, client: AsyncClient, db_session: AsyncSession):
        """Archive flag can be toggled."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id))

        resp = await client.put(
            f"/api/v1/chat/conversations/{conv['id']}",
            json={"is_archived": True},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        assert resp.json()["is_archived"] is True

    async def test_not_found(self, client: AsyncClient, db_session: AsyncSession):
        """Update non-existent conversation returns 404."""
        user = await create_user(db_session)
        resp = await client.put(
            f"/api/v1/chat/conversations/{UUID(int=0)}",
            json={"title": "Nope"},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_other_users_conversation_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Update another user's conversation returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        conv = await _create_conv(client, str(user_a.id))

        resp = await client.put(
            f"/api/v1/chat/conversations/{conv['id']}",
            json={"title": "Hacked"},
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404


class TestDeleteConversation:
    async def test_success(self, client: AsyncClient, db_session: AsyncSession):
        """Delete conversation returns 204 and removes the record."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id))

        resp = await client.delete(
            f"/api/v1/chat/conversations/{conv['id']}",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 204

        # Verify record is gone
        result = await db_session.execute(
            select(Conversation).where(Conversation.id == UUID(conv["id"]))
        )
        assert result.scalar_one_or_none() is None

    async def test_cascades_to_messages(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Deleting a conversation also deletes its messages."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id), title="Cascade Test")

        # Send a message (creates user msg + AI response)
        await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": "Hello"},
            headers=auth_header(str(user.id)),
        )

        # Verify messages exist
        msg_result = await db_session.execute(
            select(Message).where(Message.conversation_id == UUID(conv["id"]))
        )
        assert len(msg_result.scalars().all()) > 0

        # Delete conversation
        await client.delete(
            f"/api/v1/chat/conversations/{conv['id']}",
            headers=auth_header(str(user.id)),
        )

        # Verify messages are also gone
        msg_result = await db_session.execute(
            select(Message).where(Message.conversation_id == UUID(conv["id"]))
        )
        assert msg_result.scalar_one_or_none() is None

    async def test_not_found(self, client: AsyncClient, db_session: AsyncSession):
        """Delete non-existent conversation returns 404."""
        user = await create_user(db_session)
        resp = await client.delete(
            f"/api/v1/chat/conversations/{UUID(int=0)}",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_other_users_conversation_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delete another user's conversation returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        conv = await _create_conv(client, str(user_a.id))

        resp = await client.delete(
            f"/api/v1/chat/conversations/{conv['id']}",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404


# ─── Messages ─────────────────────────────────────────────────────────────


class TestListMessages:
    async def test_empty(self, client: AsyncClient, db_session: AsyncSession):
        """List messages for a conversation with none returns empty."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id))

        resp = await client.get(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["messages"] == []
        assert body["total"] == 0

    async def test_returns_messages_in_order(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Messages are returned oldest-first."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id))

        # Send a message to populate messages
        await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": "First message"},
            headers=auth_header(str(user.id)),
        )

        resp = await client.get(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2  # user msg + assistant response
        # First message should be user's
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "First message"
        # Second should be assistant's
        assert body["messages"][1]["role"] == "assistant"

    async def test_other_users_conversation_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Listing messages for another user's conversation returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        conv = await _create_conv(client, str(user_a.id))

        resp = await client.get(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404


class TestSendMessage:
    async def test_streams_response(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Sending a message returns SSE stream with chunk and done events."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id), title="Stream Test")

        resp = await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": "Hello, AI!"},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        # Parse SSE events
        chunks = []
        for raw_event in resp.text.split("\n\n"):
            event = raw_event.strip()
            if not event:
                continue
            if event == "data: [DONE]":
                break
            if event.startswith("data: "):
                chunks.append(json.loads(event[6:]))

        # Should have chunk events and a done event
        assert len(chunks) >= 2
        assert chunks[0]["type"] == "chunk"
        assert chunks[-1]["type"] == "done"
        assert chunks[-1]["finish_reason"] == "stop"
        # MockAIProvider reports token counts
        assert chunks[-1]["input_tokens"] is not None
        assert chunks[-1]["output_tokens"] is not None

    async def test_saves_user_message(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """User message is persisted to the database."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id))

        await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": "Save me!"},
            headers=auth_header(str(user.id)),
        )

        result = await db_session.execute(
            select(Message).where(
                Message.conversation_id == UUID(conv["id"]),
                Message.role == "user",
            )
        )
        msgs = result.scalars().all()
        assert len(msgs) == 1
        assert msgs[0].content == "Save me!"

    async def test_saves_assistant_message(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Assistant response is persisted after streaming."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id))

        await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": "Tell me something"},
            headers=auth_header(str(user.id)),
        )

        result = await db_session.execute(
            select(Message).where(
                Message.conversation_id == UUID(conv["id"]),
                Message.role == "assistant",
            )
        )
        msgs = result.scalars().all()
        assert len(msgs) == 1
        assert len(msgs[0].content) > 0
        # MockAIProvider tracks token counts
        assert msgs[0].input_tokens is not None
        assert msgs[0].output_tokens is not None

    async def test_auto_generates_title(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """First message auto-generates a conversation title."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id))
        assert conv["title"] is None  # no title provided

        await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": "Hello world"},
            headers=auth_header(str(user.id)),
        )

        # Verify title was set
        result = await db_session.execute(
            select(Conversation).where(Conversation.id == UUID(conv["id"]))
        )
        updated_conv = result.scalar_one()
        assert updated_conv.title is not None
        assert len(updated_conv.title) > 0

    async def test_stream_content_matches_mock(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Streamed content equals the persisted assistant message."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id))

        resp = await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": "Test match"},
            headers=auth_header(str(user.id)),
        )

        # Reconstruct full response from stream
        full = ""
        for raw_event in resp.text.split("\n\n"):
            event = raw_event.strip()
            if not event or event == "data: [DONE]":
                continue
            if event.startswith("data: "):
                chunk = json.loads(event[6:])
                if chunk["type"] == "chunk":
                    full += chunk.get("content", "")

        # Verify persisted match
        result = await db_session.execute(
            select(Message).where(
                Message.conversation_id == UUID(conv["id"]),
                Message.role == "assistant",
            )
        )
        saved = result.scalar_one()
        assert saved.content == full

    async def test_message_count_increments(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Conversation message_count reflects sent messages."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id), title="Count Test")

        # Send two messages → 2 user + 2 assistant = 4 total
        for msg in ("First", "Second"):
            await client.post(
                f"/api/v1/chat/conversations/{conv['id']}/messages",
                json={"content": msg},
                headers=auth_header(str(user.id)),
            )

        # Check from list endpoint
        resp = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_header(str(user.id)),
        )
        conv_list = resp.json()["conversations"]
        target = next(c for c in conv_list if c["id"] == conv["id"])
        assert target["message_count"] == 4

    async def test_other_users_conversation_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Sending to another user's conversation returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        conv = await _create_conv(client, str(user_a.id))

        resp = await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": "Hack the planet"},
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404

    async def test_unauthenticated(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Sending without auth returns 401."""
        user = await create_user(db_session)
        conv = await _create_conv(client, str(user.id))
        resp = await client.post(
            f"/api/v1/chat/conversations/{conv['id']}/messages",
            json={"content": "No auth"},
        )
        assert resp.status_code == 401
