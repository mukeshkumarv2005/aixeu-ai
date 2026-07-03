"""Comprehensive task management tests.

Covers CRUD, status transitions, labels, comments, attachments,
board/calendar views, stats, ownership isolation, search, filtering,
pagination, and validation edge-cases.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.file import File
from app.models.knowledge import KnowledgeBase, KnowledgeBaseDocument
from app.models.task import Task, TaskAttachment, TaskComment, TaskLabel
from app.schemas.task import TASK_PRIORITIES, TASK_STATUSES
from tests.conftest import auth_header, create_user

# ── Helpers ──────────────────────────────────────────────────────────────────


async def create_task(
    db_session: AsyncSession,
    user_id: UUID,
    **kwargs,
) -> Task:
    """Factory: create a task directly in the DB and return the ORM object."""
    task = Task(
        owner_id=user_id,
        title=kwargs.pop("title", "Test task"),
        description=kwargs.pop("description", None),
        status=kwargs.pop("status", "todo"),
        priority=kwargs.pop("priority", "medium"),
        **kwargs,
    )
    db_session.add(task)
    await db_session.flush()
    return task


async def create_file(db_session: AsyncSession, user_id: UUID) -> File:
    """Factory: create a File record."""
    f = File(
        user_id=user_id,
        filename="test.txt",
        mime_type="text/plain",
        size_bytes=100,
        storage_path="/tmp/test.txt",
    )
    db_session.add(f)
    await db_session.flush()
    return f


async def create_conversation(db_session: AsyncSession, user_id: UUID) -> Conversation:
    """Factory: create a Conversation record."""
    c = Conversation(
        user_id=user_id,
        title="Test conversation",
    )
    db_session.add(c)
    await db_session.flush()
    return c


async def create_kb_document(db_session: AsyncSession, user_id: UUID) -> KnowledgeBaseDocument:
    """Factory: create a KnowledgeBase + Document owned by user."""
    kb = KnowledgeBase(
        user_id=user_id,
        name="Test KB",
    )
    db_session.add(kb)
    await db_session.flush()
    doc = KnowledgeBaseDocument(
        knowledge_base_id=kb.id,
        title="Test doc",
        content="Hello world",
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


def future_dt(**kwargs) -> str:
    """Return an ISO 8601 datetime string in the future."""
    return (datetime.now(UTC) + timedelta(**kwargs)).isoformat()


def past_dt(**kwargs) -> str:
    """Return an ISO 8601 datetime string in the past."""
    return (datetime.now(UTC) - timedelta(**kwargs)).isoformat()


STATUSES = sorted(TASK_STATUSES)
PRIORITIES = sorted(TASK_PRIORITIES)


class TestCreateTask:
    """POST /api/v1/tasks"""

    async def test_create_basic(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Minimal creation succeeds with defaults."""
        resp = await client.post("/api/v1/tasks", json={"title": "Hello"}, headers=auth_header(str(user_id)))
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Hello"
        assert data["status"] == "todo"
        assert data["priority"] == "medium"
        assert data["owner_id"] == str(user_id)
        assert UUID(data["id"])

    async def test_create_with_all_fields(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """All optional fields are accepted."""
        due = future_dt(days=7)
        reminder = future_dt(days=6)
        payload = {
            "title": "Full task",
            "description": "A longer description.",
            "status": "in_progress",
            "priority": "high",
            "due_date": due,
            "reminder_at": reminder,
            "estimated_minutes": 120,
        }
        resp = await client.post("/api/v1/tasks", json=payload, headers=auth_header(str(user_id)))
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Full task"
        assert data["description"] == "A longer description."
        assert data["status"] == "in_progress"
        assert data["priority"] == "high"
        assert data["estimated_minutes"] == 120

    async def test_create_with_resource_links(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Resource links (file, conversation, KB doc) are accepted when they exist."""
        file_ = await create_file(db_session, user_id)
        conv = await create_conversation(db_session, user_id)
        doc = await create_kb_document(db_session, user_id)

        payload = {
            "title": "Linked task",
            "uploaded_document_id": str(file_.id),
            "chat_conversation_id": str(conv.id),
            "kb_document_id": str(doc.id),
        }
        resp = await client.post("/api/v1/tasks", json=payload, headers=auth_header(str(user_id)))
        assert resp.status_code == 201
        data = resp.json()
        assert data["uploaded_document_id"] == str(file_.id)
        assert data["chat_conversation_id"] == str(conv.id)
        assert data["kb_document_id"] == str(doc.id)

    async def test_create_rejects_missing_resource(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Linking to a non-existent resource returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        payload = {"title": "Bad link", "uploaded_document_id": fake_id}
        resp = await client.post("/api/v1/tasks", json=payload, headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_create_rejects_resource_owned_by_other(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Linking to a resource owned by another user returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        file_ = await create_file(db_session, other.id)
        payload = {"title": "Stolen link", "uploaded_document_id": str(file_.id)}
        resp = await client.post("/api/v1/tasks", json=payload, headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_create_past_due_date_rejected(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """due_date in the past returns 422."""
        payload = {"title": "Past", "due_date": past_dt(days=1)}
        resp = await client.post("/api/v1/tasks", json=payload, headers=auth_header(str(user_id)))
        assert resp.status_code == 422

    async def test_create_past_reminder_rejected(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """reminder_at in the past returns 422."""
        payload = {"title": "Past reminder", "reminder_at": past_dt(hours=1)}
        resp = await client.post("/api/v1/tasks", json=payload, headers=auth_header(str(user_id)))
        assert resp.status_code == 422

    async def test_create_reminder_after_due_rejected(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """reminder_at after due_date returns 422."""
        payload = {
            "title": "Bad order",
            "due_date": future_dt(days=5),
            "reminder_at": future_dt(days=6),
        }
        resp = await client.post("/api/v1/tasks", json=payload, headers=auth_header(str(user_id)))
        assert resp.status_code == 422

    async def test_create_invalid_status(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Invalid status returns 422."""
        resp = await client.post("/api/v1/tasks", json={"title": "X", "status": "invalid"}, headers=auth_header(str(user_id)))
        assert resp.status_code == 422

    async def test_create_invalid_priority(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Invalid priority returns 422."""
        resp = await client.post("/api/v1/tasks", json={"title": "X", "priority": "urgent"}, headers=auth_header(str(user_id)))
        assert resp.status_code == 422

    async def test_create_unauthenticated(self, client: AsyncClient):
        """Missing auth token returns 401."""
        resp = await client.post("/api/v1/tasks", json={"title": "X"})
        assert resp.status_code == 401


class TestListTasks:
    """GET /api/v1/tasks"""

    async def test_list_empty(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """No tasks returns empty list."""
        resp = await client.get("/api/v1/tasks", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_pagination(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Pagination returns correct slice."""
        for i in range(5):
            await create_task(db_session, user_id, title=f"Task {i}")
        resp = await client.get("/api/v1/tasks?offset=0&limit=2", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["offset"] == 0
        assert data["limit"] == 2

    async def test_list_filter_by_status(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Filtering by status returns only matching tasks."""
        await create_task(db_session, user_id, title="Todo", status="todo")
        await create_task(db_session, user_id, title="Done", status="done")
        resp = await client.get("/api/v1/tasks?status=done", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Done"

    async def test_list_filter_by_priority(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Filtering by priority works."""
        await create_task(db_session, user_id, title="Low", priority="low")
        await create_task(db_session, user_id, title="High", priority="high")
        resp = await client.get("/api/v1/tasks?priority=high", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "High"

    async def test_list_search(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Search matches title and description."""
        await create_task(db_session, user_id, title="Alpha", description="Something about omega")
        await create_task(db_session, user_id, title="Beta")
        resp = await client.get("/api/v1/tasks?search=omega", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Alpha"

    async def test_list_ownership_isolation(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Only the owning user's tasks are returned."""
        other = await create_user(db_session, email="other@example.com", username="other")
        await create_task(db_session, user_id, title="Mine")
        await create_task(db_session, other.id, title="Theirs")
        resp = await client.get("/api/v1/tasks", headers=auth_header(str(user_id)))
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Mine"


class TestGetTask:
    """GET /api/v1/tasks/{task_id}"""

    async def test_get_own_task(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Getting own task returns it."""
        task = await create_task(db_session, user_id)
        resp = await client.get(f"/api/v1/tasks/{task.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        assert resp.json()["id"] == str(task.id)

    async def test_get_other_user_task_returns_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Getting another user's task returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        task = await create_task(db_session, other.id)
        resp = await client.get(f"/api/v1/tasks/{task.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_get_nonexistent(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Getting a non-existent task returns 404."""
        resp = await client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000", headers=auth_header(str(user_id)))
        assert resp.status_code == 404


class TestUpdateTask:
    """PATCH /api/v1/tasks/{task_id}"""

    async def test_update_title(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Partial update changes only the provided field."""
        task = await create_task(db_session, user_id)
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"title": "Updated"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    async def test_valid_status_transition(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """todo → in_progress is allowed."""
        task = await create_task(db_session, user_id, status="todo")
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"status": "in_progress"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    async def test_invalid_status_transition(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """todo → review is rejected (not a direct transition)."""
        task = await create_task(db_session, user_id, status="todo")
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"status": "review"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 400

    async def test_self_transition_not_allowed(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Setting status to current value is a no-op (no transition needed)."""
        task = await create_task(db_session, user_id, status="in_progress")
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"status": "in_progress"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200  # same status is a no-op, not an error
        assert resp.json()["status"] == "in_progress"

    async def test_update_completed_at(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Moving to 'done' sets completed_at."""
        task = await create_task(db_session, user_id, status="in_progress")
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"status": "done"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["completed_at"] is not None

    async def test_update_other_user_task_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Updating another user's task returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        task = await create_task(db_session, other.id)
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}",
            json={"title": "Hacked"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestDeleteTask:
    """DELETE /api/v1/tasks/{task_id}"""

    async def test_delete_own_task(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Deleting own task returns 204."""
        task = await create_task(db_session, user_id)
        resp = await client.delete(f"/api/v1/tasks/{task.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 204

    async def test_delete_other_user_task_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Deleting another user's task returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        task = await create_task(db_session, other.id)
        resp = await client.delete(f"/api/v1/tasks/{task.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 404


class TestStatusTransitions:
    """POST /api/v1/tasks/{task_id}/{complete|archive|restore}"""

    async def test_complete(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        resp = await client.post(f"/api/v1/tasks/{task.id}/complete", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"
        assert resp.json()["completed_at"] is not None

    async def test_complete_idempotent(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id, status="done")
        resp = await client.post(f"/api/v1/tasks/{task.id}/complete", headers=auth_header(str(user_id)))
        assert resp.status_code == 200

    async def test_archive(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        resp = await client.post(f"/api/v1/tasks/{task.id}/archive", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    async def test_archive_idempotent(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id, status="archived")
        resp = await client.post(f"/api/v1/tasks/{task.id}/archive", headers=auth_header(str(user_id)))
        assert resp.status_code == 200

    async def test_restore(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id, status="archived")
        resp = await client.post(f"/api/v1/tasks/{task.id}/restore", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        assert resp.json()["status"] == "todo"

    async def test_restore_idempotent(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id, status="todo")
        resp = await client.post(f"/api/v1/tasks/{task.id}/restore", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        assert resp.json()["status"] == "todo"

    async def test_status_endpoint_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        other = await create_user(db_session, email="other@example.com", username="other")
        task = await create_task(db_session, other.id)
        for ep in ("complete", "archive", "restore"):
            resp = await client.post(f"/api/v1/tasks/{task.id}/{ep}", headers=auth_header(str(user_id)))
            assert resp.status_code == 404, f"{ep} should 404"


class TestLabels:
    """POST/DELETE /api/v1/tasks/{task_id}/labels[/{label_id}]"""

    async def test_add_label(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        resp = await client.post(
            f"/api/v1/tasks/{task.id}/labels",
            json={"name": "bug"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "bug"

    async def test_add_label_with_color(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        resp = await client.post(
            f"/api/v1/tasks/{task.id}/labels",
            json={"name": "feature", "color": "#00ff00"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        assert resp.json()["color"] == "#00ff00"

    async def test_duplicate_label_rejected(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        await client.post(f"/api/v1/tasks/{task.id}/labels", json={"name": "bug"}, headers=auth_header(str(user_id)))
        resp = await client.post(f"/api/v1/tasks/{task.id}/labels", json={"name": "bug"}, headers=auth_header(str(user_id)))
        assert resp.status_code == 409

    async def test_invalid_color_rejected(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        resp = await client.post(
            f"/api/v1/tasks/{task.id}/labels",
            json={"name": "bad", "color": "not-a-hex"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422

    async def test_remove_label(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        add = await client.post(f"/api/v1/tasks/{task.id}/labels", json={"name": "bug"}, headers=auth_header(str(user_id)))
        label_id = add.json()["id"]
        resp = await client.delete(f"/api/v1/tasks/{task.id}/labels/{label_id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 204

    async def test_label_appears_in_task(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        await client.post(f"/api/v1/tasks/{task.id}/labels", json={"name": "bug"}, headers=auth_header(str(user_id)))
        resp = await client.get(f"/api/v1/tasks/{task.id}", headers=auth_header(str(user_id)))
        assert len(resp.json()["labels"]) == 1
        assert resp.json()["labels"][0]["name"] == "bug"

    async def test_label_on_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        other = await create_user(db_session, email="other@example.com", username="other")
        task = await create_task(db_session, other.id)
        resp = await client.post(f"/api/v1/tasks/{task.id}/labels", json={"name": "x"}, headers=auth_header(str(user_id)))
        assert resp.status_code == 404


class TestComments:
    """CRUD for /api/v1/tasks/{task_id}/comments[/{comment_id}]"""

    async def test_add_comment(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        resp = await client.post(
            f"/api/v1/tasks/{task.id}/comments",
            json={"content": "Nice work"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        comments = resp.json()["comments"]
        assert len(comments) == 1
        assert comments[0]["content"] == "Nice work"
        assert comments[0]["author_id"] == str(user_id)

    async def test_update_own_comment(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        add = await client.post(f"/api/v1/tasks/{task.id}/comments", json={"content": "Old"}, headers=auth_header(str(user_id)))
        comment_id = add.json()["comments"][0]["id"]
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/comments/{comment_id}",
            json={"content": "Updated"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        found = [c for c in resp.json()["comments"] if c["id"] == comment_id]
        assert found[0]["content"] == "Updated"

    async def test_update_other_author_comment(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Non-owners get 404 when trying to update any comment on a task."""
        other = await create_user(db_session, email="other@example.com", username="other")
        task = await create_task(db_session, user_id)
        # Task owner adds a comment
        add = await client.post(
            f"/api/v1/tasks/{task.id}/comments",
            json={"content": "Owner comment"},
            headers=auth_header(str(user_id)),
        )
        comment_id = add.json()["comments"][0]["id"]
        # Other user tries to update it
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/comments/{comment_id}",
            json={"content": "Hacked"},
            headers=auth_header(str(other.id)),
        )
        assert resp.status_code == 404

    async def test_delete_own_comment(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        add = await client.post(f"/api/v1/tasks/{task.id}/comments", json={"content": "Bye"}, headers=auth_header(str(user_id)))
        comment_id = add.json()["comments"][0]["id"]
        resp = await client.delete(f"/api/v1/tasks/{task.id}/comments/{comment_id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 204

    async def test_task_owner_can_delete_any_comment(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """The task owner can delete a comment on their task (own comment)."""
        task = await create_task(db_session, user_id)
        add = await client.post(
            f"/api/v1/tasks/{task.id}/comments",
            json={"content": "By owner"},
            headers=auth_header(str(user_id)),
        )
        comment_id = add.json()["comments"][0]["id"]
        resp = await client.delete(f"/api/v1/tasks/{task.id}/comments/{comment_id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 204

    async def test_comment_on_other_user_task_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        other = await create_user(db_session, email="other@example.com", username="other")
        task = await create_task(db_session, other.id)
        resp = await client.post(f"/api/v1/tasks/{task.id}/comments", json={"content": "X"}, headers=auth_header(str(user_id)))
        assert resp.status_code == 404


class TestAttachments:
    """CRUD for /api/v1/tasks/{task_id}/attachments[/{attachment_id}]"""

    async def test_add_attachment(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        file_ = await create_file(db_session, user_id)
        resp = await client.post(
            f"/api/v1/tasks/{task.id}/attachments",
            json={"file_id": str(file_.id)},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        attachments = resp.json()["attachments"]
        assert len(attachments) == 1
        assert attachments[0]["file_id"] == str(file_.id)

    async def test_add_attachment_missing_file(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        resp = await client.post(
            f"/api/v1/tasks/{task.id}/attachments",
            json={"file_id": "00000000-0000-0000-0000-000000000000"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_add_attachment_other_user_file(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Attaching a file owned by another user returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        task = await create_task(db_session, user_id)
        file_ = await create_file(db_session, other.id)
        resp = await client.post(
            f"/api/v1/tasks/{task.id}/attachments",
            json={"file_id": str(file_.id)},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_remove_attachment(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        task = await create_task(db_session, user_id)
        file_ = await create_file(db_session, user_id)
        add = await client.post(
            f"/api/v1/tasks/{task.id}/attachments",
            json={"file_id": str(file_.id)},
            headers=auth_header(str(user_id)),
        )
        attachment_id = add.json()["attachments"][0]["id"]
        resp = await client.delete(f"/api/v1/tasks/{task.id}/attachments/{attachment_id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 204

    async def test_attachment_on_other_user_task_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        other = await create_user(db_session, email="other@example.com", username="other")
        task = await create_task(db_session, other.id)
        file_ = await create_file(db_session, user_id)
        resp = await client.post(
            f"/api/v1/tasks/{task.id}/attachments",
            json={"file_id": str(file_.id)},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestBoard:
    """GET /api/v1/tasks/board"""

    async def test_board_groups_by_status(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        await create_task(db_session, user_id, title="Todo")
        await create_task(db_session, user_id, title="In Progress", status="in_progress")
        await create_task(db_session, user_id, title="Done", status="done")
        resp = await client.get("/api/v1/tasks/board", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["todo"]) == 1
        assert len(data["in_progress"]) == 1
        assert len(data["done"]) == 1

    async def test_board_ownership(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        other = await create_user(db_session, email="other@example.com", username="other")
        await create_task(db_session, user_id, title="Mine")
        await create_task(db_session, other.id, title="Theirs")
        resp = await client.get("/api/v1/tasks/board", headers=auth_header(str(user_id)))
        data = resp.json()
        total = len(data["todo"]) + len(data["in_progress"]) + len(data["review"]) + len(data["done"]) + len(data["archived"])
        assert total == 1

    async def test_board_limit(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Board respects the limit parameter."""
        for i in range(5):
            await create_task(db_session, user_id, title=f"Task {i}")
        resp = await client.get("/api/v1/tasks/board?limit=2", headers=auth_header(str(user_id)))
        data = resp.json()
        assert len(data["todo"]) <= 2


class TestCalendar:
    """GET /api/v1/tasks/calendar"""

    async def test_calendar_default_to_current_month(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Tasks with a due date this month appear in the calendar view."""
        due = future_dt(days=2)
        await create_task(db_session, user_id, title="Soon", due_date=datetime.fromisoformat(due))
        resp = await client.get("/api/v1/tasks/calendar", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_calendar_date_range(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Only tasks within the specified range are returned."""
        await create_task(
            db_session, user_id, title="Next week",
            due_date=datetime.fromisoformat(future_dt(days=10)),
        )
        await create_task(
            db_session, user_id, title="Next month",
            due_date=datetime.fromisoformat(future_dt(days=60)),
        )
        start = future_dt(days=5)[:10]  # YYYY-MM-DD
        end = future_dt(days=20)[:10]
        resp = await client.get(f"/api/v1/tasks/calendar?start_date={start}&end_date={end}", headers=auth_header(str(user_id)))
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Next week"


class TestStats:
    """GET /api/v1/tasks/stats"""

    async def test_stats_counts(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        await create_task(db_session, user_id, title="T1", status="todo")
        await create_task(db_session, user_id, title="T2", status="in_progress")
        await create_task(db_session, user_id, title="T3", status="done")
        resp = await client.get("/api/v1/tasks/stats", headers=auth_header(str(user_id)))
        data = resp.json()
        assert data["total"] == 3
        assert data["todo"] == 1
        assert data["in_progress"] == 1
        assert data["done"] == 1

    async def test_stats_ownership(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Stats only count the current user's tasks."""
        other = await create_user(db_session, email="other@example.com", username="other")
        await create_task(db_session, user_id, title="Mine")
        await create_task(db_session, other.id, title="Theirs")
        resp = await client.get("/api/v1/tasks/stats", headers=auth_header(str(user_id)))
        assert resp.json()["total"] == 1


class TestSearch:
    """GET /api/v1/tasks/search"""

    async def test_search_by_query(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        await create_task(db_session, user_id, title="Find me")
        await create_task(db_session, user_id, title="Ignore me")
        resp = await client.get("/api/v1/tasks/search?q=Find", headers=auth_header(str(user_id)))
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Find me"

    async def test_search_requires_min_length(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        resp = await client.get("/api/v1/tasks/search?q=", headers=auth_header(str(user_id)))
        assert resp.status_code == 422


class TestByResource:
    """GET /api/v1/tasks/by-resource"""

    async def test_by_kb_document(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        doc = await create_kb_document(db_session, user_id)
        await create_task(db_session, user_id, title="Linked to KB", kb_document_id=doc.id)
        resp = await client.get(f"/api/v1/tasks/by-resource?kb_document_id={doc.id}", headers=auth_header(str(user_id)))
        data = resp.json()
        assert data["total"] == 1

    async def test_by_chat_conversation(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        conv = await create_conversation(db_session, user_id)
        await create_task(db_session, user_id, title="Chat linked", chat_conversation_id=conv.id)
        resp = await client.get(f"/api/v1/tasks/by-resource?chat_conversation_id={conv.id}", headers=auth_header(str(user_id)))
        data = resp.json()
        assert data["total"] == 1

    async def test_by_uploaded_document(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        file_ = await create_file(db_session, user_id)
        await create_task(db_session, user_id, title="File linked", uploaded_document_id=file_.id)
        resp = await client.get(f"/api/v1/tasks/by-resource?uploaded_document_id={file_.id}", headers=auth_header(str(user_id)))
        data = resp.json()
        assert data["total"] == 1


class TestOverdue:
    """GET /api/v1/tasks/overdue"""

    async def test_overdue_tasks(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        past = past_dt(days=1)
        await create_task(
            db_session, user_id, title="Overdue",
            due_date=datetime.fromisoformat(past),
        )
        resp = await client.get("/api/v1/tasks/overdue", headers=auth_header(str(user_id)))
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Overdue"

    async def test_completed_tasks_not_overdue(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        past = past_dt(days=1)
        await create_task(
            db_session, user_id, title="Done but overdue", status="done",
            due_date=datetime.fromisoformat(past),
        )
        resp = await client.get("/api/v1/tasks/overdue", headers=auth_header(str(user_id)))
        assert resp.json()["total"] == 0


class TestOwnershipIsolation:
    """Every endpoint on another user's task returns 404."""

    @pytest_asyncio.fixture
    async def other_task(self, db_session: AsyncSession) -> tuple[UUID, Task]:
        other = await create_user(db_session, email="bob@example.com", username="bob")
        task = await create_task(db_session, other.id)
        return other.id, task

    async def test_get_404(self, client: AsyncClient, user_id: UUID, other_task):
        _, task = other_task
        resp = await client.get(f"/api/v1/tasks/{task.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_patch_404(self, client: AsyncClient, user_id: UUID, other_task):
        _, task = other_task
        resp = await client.patch(f"/api/v1/tasks/{task.id}", json={"title": "x"}, headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_delete_404(self, client: AsyncClient, user_id: UUID, other_task):
        _, task = other_task
        resp = await client.delete(f"/api/v1/tasks/{task.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_complete_404(self, client: AsyncClient, user_id: UUID, other_task):
        _, task = other_task
        resp = await client.post(f"/api/v1/tasks/{task.id}/complete", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_archive_404(self, client: AsyncClient, user_id: UUID, other_task):
        _, task = other_task
        resp = await client.post(f"/api/v1/tasks/{task.id}/archive", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_restore_404(self, client: AsyncClient, user_id: UUID, other_task):
        _, task = other_task
        resp = await client.post(f"/api/v1/tasks/{task.id}/restore", headers=auth_header(str(user_id)))
        assert resp.status_code == 404


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def user_id(db_session: AsyncSession) -> UUID:
    """Create a test user and return their ID."""
    user = await create_user(db_session)
    return user.id
