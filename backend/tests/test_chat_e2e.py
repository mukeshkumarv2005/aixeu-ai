"""End-to-end chat flow test.

Simulates the full user journey:
  create conversation -> send message -> receive SSE stream ->
  reload -> verify history persisted.

This is a single comprehensive test that exercises the real ASGI transport
and in-memory SQLite database provided by conftest fixtures.
"""

from __future__ import annotations

import json

import pytest

from tests.conftest import auth_header, create_user


@pytest.mark.asyncio
async def test_chat_e2e_flow(client, db_session):
    """Create conversation -> send message -> stream -> reload -> verify history."""
    # -- Step 1: Create a user ------------------------------------------------
    user = await create_user(db_session)
    user_id = str(user.id)
    headers = auth_header(user_id)

    # -- Step 2: Create a conversation ----------------------------------------
    resp = await client.post(
        "/api/v1/chat/conversations",
        json={"model": "gpt-4o"},
        headers=headers,
    )
    assert resp.status_code == 201, f"Create conv failed: {resp.text}"
    conv = resp.json()
    conv_id = conv["id"]
    print(f"\n  [OK] Created conversation: {conv_id}")

    # -- Step 3: Send a message and receive SSE stream ------------------------
    resp = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"content": "Hello, AI!"},
        headers=headers,
    )
    assert resp.status_code == 200, f"Send message failed: {resp.text}"
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

    assert len(chunks) >= 2, f"Expected >=2 SSE events, got {len(chunks)}"
    assert chunks[0]["type"] == "chunk"
    assert chunks[-1]["type"] == "done"
    assert chunks[-1]["finish_reason"] == "stop"

    # Reconstruct streamed content
    streamed_text = "".join(
        c.get("content", "") for c in chunks if c["type"] == "chunk"
    )
    print(f"  [OK] Received SSE stream ({len(chunks)} events, {len(streamed_text)} chars)")
    print(f"       Content preview: {streamed_text[:80]}...")

    # -- Step 4: Verify token tracking ----------------------------------------
    assert chunks[-1]["input_tokens"] is not None
    assert chunks[-1]["output_tokens"] is not None
    print(f"  [OK] Token tracking: in={chunks[-1]['input_tokens']} out={chunks[-1]['output_tokens']}")

    # -- Step 5: Reload -- list conversations and verify ----------------------
    resp = await client.get("/api/v1/chat/conversations", headers=headers)
    assert resp.status_code == 200
    conv_list = resp.json()
    assert conv_list["total"] >= 1

    target = next((c for c in conv_list["conversations"] if c["id"] == conv_id), None)
    assert target is not None, "Conversation not found in list after reload"
    assert target["message_count"] == 2  # user + assistant
    print(f"  [OK] Conversation found in list: message_count={target['message_count']}")

    # -- Step 6: Reload -- fetch messages -------------------------------------
    resp = await client.get(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=headers,
    )
    assert resp.status_code == 200
    msgs = resp.json()
    assert msgs["total"] == 2
    assert msgs["messages"][0]["role"] == "user"
    assert msgs["messages"][0]["content"] == "Hello, AI!"
    assert msgs["messages"][1]["role"] == "assistant"
    assert len(msgs["messages"][1]["content"]) > 0

    # Verify streamed content matches persisted content
    assert msgs["messages"][1]["content"] == streamed_text, (
        "Streamed content does not match persisted assistant message"
    )
    print(f"  [OK] Messages persisted correctly ({msgs['total']} messages)")
    print(f"  [OK] Streamed content matches persisted content")

    # -- Step 7: Verify title was auto-generated ------------------------------
    assert target["title"] is not None and len(target["title"]) > 0
    print(f"  [OK] Title auto-generated: {target['title']!r}")

    print(f"\n  [PASS] All E2E checks passed!")
