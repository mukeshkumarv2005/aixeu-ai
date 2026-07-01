"""Comprehensive file-storage endpoint tests.

Covers upload, list, get metadata, download, and delete — all with
ownership enforcement.
"""

from __future__ import annotations

import io
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from tests.conftest import auth_header, create_user


class TestUpload:
    async def test_success(self, client: AsyncClient, db_session: AsyncSession):
        """Upload a file returns 201 with metadata."""
        user = await create_user(db_session)
        content = b"hello world, this is a test file"
        resp = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["filename"] == "test.txt"
        assert body["mime_type"] == "text/plain"
        assert body["size_bytes"] == len(content)
        assert body["storage_path"]
        assert "id" in body
        assert "created_at" in body

        # Record exists in DB
        result = await db_session.execute(
            select(File).where(File.id == UUID(body["id"]))
        )
        record = result.scalar_one_or_none()
        assert record is not None
        assert record.filename == "test.txt"
        assert record.user_id == user.id

    async def test_without_filename(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Upload without a filename returns 400."""
        user = await create_user(db_session)
        resp = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("", io.BytesIO(b"data"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        # Starlette multipart parser rejects empty filenames before the handler
        assert resp.status_code == 422

    async def test_file_too_large(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Upload exceeding max size returns 413."""
        user = await create_user(db_session)
        # Create content larger than 50MB limit
        content = b"x" * (51 * 1024 * 1024)
        resp = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("big.txt", io.BytesIO(content), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 413

    async def test_unauthenticated(self, client: AsyncClient):
        """Upload without auth returns 401."""
        resp = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("test.txt", io.BytesIO(b"data"), "text/plain")},
        )
        assert resp.status_code == 401


class TestListFiles:
    async def test_empty(self, client: AsyncClient, db_session: AsyncSession):
        """Listing files for a user with no files returns empty list."""
        user = await create_user(db_session)
        resp = await client.get(
            "/api/v1/storage/files",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["files"] == []
        assert body["total"] == 0

    async def test_with_files(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Listing returns the user's files with correct metadata."""
        user = await create_user(db_session)
        # Upload two files
        for name in ("alpha.txt", "beta.txt"):
            await client.post(
                "/api/v1/storage/upload",
                files={"file": (name, io.BytesIO(b"data"), "text/plain")},
                headers=auth_header(str(user.id)),
            )

        resp = await client.get(
            "/api/v1/storage/files",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        filenames = {f["filename"] for f in body["files"]}
        assert filenames == {"alpha.txt", "beta.txt"}

    async def test_other_users_files_not_visible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """A user only sees their own files."""
        user_a = await create_user(db_session, email="a@test.com", username="usera")
        user_b = await create_user(db_session, email="b@test.com", username="userb")

        # User A uploads a file
        await client.post(
            "/api/v1/storage/upload",
            files={"file": ("a.txt", io.BytesIO(b"aaa"), "text/plain")},
            headers=auth_header(str(user_a.id)),
        )

        # User B lists — should be empty
        resp = await client.get(
            "/api/v1/storage/files",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestGetFile:
    async def test_success(self, client: AsyncClient, db_session: AsyncSession):
        """Get file metadata by ID."""
        user = await create_user(db_session)
        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("mydoc.txt", io.BytesIO(b"content"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        file_id = upload.json()["id"]

        resp = await client.get(
            f"/api/v1/storage/{file_id}",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == "mydoc.txt"
        assert body["mime_type"] == "text/plain"
        assert body["size_bytes"] == 7

    async def test_not_found(self, client: AsyncClient, db_session: AsyncSession):
        """Non-existent file ID returns 404."""
        user = await create_user(db_session)
        resp = await client.get(
            f"/api/v1/storage/{UUID(int=0)}",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_other_users_file_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Get of another user's file returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("secret.txt", io.BytesIO(b"data"), "text/plain")},
            headers=auth_header(str(user_a.id)),
        )
        file_id = upload.json()["id"]

        resp = await client.get(
            f"/api/v1/storage/{file_id}",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404


class TestDownload:
    async def test_success(self, client: AsyncClient, db_session: AsyncSession):
        """Download returns the raw file binary."""
        user = await create_user(db_session)
        content = b"downloadable content here"
        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("dl.txt", io.BytesIO(content), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        file_id = upload.json()["id"]

        resp = await client.get(
            f"/api/v1/storage/{file_id}/download",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        assert resp.content == content
        assert resp.headers["content-type"].startswith("text/plain")
        assert "attachment" in resp.headers["content-disposition"]
        assert "dl.txt" in resp.headers["content-disposition"]

    async def test_not_found(self, client: AsyncClient, db_session: AsyncSession):
        """Download of non-existent file returns 404."""
        user = await create_user(db_session)
        resp = await client.get(
            f"/api/v1/storage/{UUID(int=0)}/download",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_other_users_file_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Download of another user's file returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("secret.txt", io.BytesIO(b"data"), "text/plain")},
            headers=auth_header(str(user_a.id)),
        )
        file_id = upload.json()["id"]

        resp = await client.get(
            f"/api/v1/storage/{file_id}/download",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404


class TestDelete:
    async def test_success(self, client: AsyncClient, db_session: AsyncSession):
        """Delete a file returns 204 and removes the record."""
        user = await create_user(db_session)
        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("delete_me.txt", io.BytesIO(b"bye"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        file_id = upload.json()["id"]

        resp = await client.delete(
            f"/api/v1/storage/{file_id}",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 204

        # Verify record is gone
        result = await db_session.execute(
            select(File).where(File.id == UUID(file_id))
        )
        assert result.scalar_one_or_none() is None

    async def test_not_found(self, client: AsyncClient, db_session: AsyncSession):
        """Delete of non-existent file returns 404."""
        user = await create_user(db_session)
        resp = await client.delete(
            f"/api/v1/storage/{UUID(int=0)}",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_other_users_file_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delete of another user's file returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("secret.txt", io.BytesIO(b"data"), "text/plain")},
            headers=auth_header(str(user_a.id)),
        )
        file_id = upload.json()["id"]

        resp = await client.delete(
            f"/api/v1/storage/{file_id}",
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404
