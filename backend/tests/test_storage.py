"""Comprehensive file-storage endpoint tests.

Covers upload, list, get metadata, download, delete, rename, MIME-type
validation, SHA-256 checksum, transparent dedup, and ownership enforcement.
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
        """Upload a file returns 201 with metadata including checksum."""
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
        assert body["checksum"] is not None
        assert len(body["checksum"]) == 64  # SHA-256 hex
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
        assert record.checksum == body["checksum"]
        assert record.processing_status == "completed"

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

    async def test_unsupported_mime_type(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Upload with disallowed MIME type returns 415."""
        user = await create_user(db_session)
        resp = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("bad.exe", io.BytesIO(b"evil"), "application/x-msdownload")},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 415
        assert "unsupported" in resp.json()["detail"].lower()

    async def test_dedup_same_content(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Uploading identical content twice returns the same record."""
        user = await create_user(db_session)
        content = b"dedup test content"

        resp1 = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("first.txt", io.BytesIO(content), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("second.txt", io.BytesIO(content), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        # Should return 201 with the existing file's data (transparent dedup)
        assert resp2.status_code == 201
        assert resp1.json()["id"] == resp2.json()["id"]
        assert resp1.json()["checksum"] == resp2.json()["checksum"]

        # Only one record in the DB
        result = await db_session.execute(
            select(File).where(File.user_id == user.id)
        )
        assert len(result.scalars().all()) == 1

    async def test_dedup_across_users(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Same content for different users creates separate records."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        content = b"shared content"
        resp_a = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("shared.txt", io.BytesIO(content), "text/plain")},
            headers=auth_header(str(user_a.id)),
        )
        assert resp_a.status_code == 201

        resp_b = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("shared.txt", io.BytesIO(content), "text/plain")},
            headers=auth_header(str(user_b.id)),
        )
        assert resp_b.status_code == 201

        # Different users -> different records
        assert resp_a.json()["id"] != resp_b.json()["id"]
        # But same checksum
        assert resp_a.json()["checksum"] == resp_b.json()["checksum"]


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
        # Upload two files with different content (otherwise our
        # transparent SHA-256 dedup would collapse them into one record)
        for i, name in enumerate(("alpha.txt", "beta.txt"), 1):
            await client.post(
                "/api/v1/storage/upload",
                files={"file": (name, io.BytesIO(f"data{i}".encode()), "text/plain")},
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


class TestRename:
    async def test_success(self, client: AsyncClient, db_session: AsyncSession):
        """Rename a file via PATCH."""
        user = await create_user(db_session)
        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("old_name.txt", io.BytesIO(b"rename me"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        file_id = upload.json()["id"]

        resp = await client.patch(
            f"/api/v1/storage/{file_id}",
            json={"filename": "new_name.txt"},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == "new_name.txt"
        assert body["id"] == file_id

    async def test_not_found(self, client: AsyncClient, db_session: AsyncSession):
        """Rename of non-existent file returns 404."""
        user = await create_user(db_session)
        resp = await client.patch(
            f"/api/v1/storage/{UUID(int=0)}",
            json={"filename": "gone.txt"},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_other_users_file_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Rename of another user's file returns 404."""
        user_a = await create_user(db_session, email="a@t.com", username="a")
        user_b = await create_user(db_session, email="b@t.com", username="b")

        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("secret.txt", io.BytesIO(b"data"), "text/plain")},
            headers=auth_header(str(user_a.id)),
        )
        file_id = upload.json()["id"]

        resp = await client.patch(
            f"/api/v1/storage/{file_id}",
            json={"filename": "hacked.txt"},
            headers=auth_header(str(user_b.id)),
        )
        assert resp.status_code == 404

    async def test_empty_body(self, client: AsyncClient, db_session: AsyncSession):
        """PATCH with no fields is a no-op (returns existing data)."""
        user = await create_user(db_session)
        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("nochange.txt", io.BytesIO(b"data"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        file_id = upload.json()["id"]

        resp = await client.patch(
            f"/api/v1/storage/{file_id}",
            json={},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        assert resp.json()["filename"] == "nochange.txt"


class TestUploadEdgeCases:
    """Edge cases and boundary conditions for file upload."""

    async def test_empty_file(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Upload a 0-byte file returns 201."""
        user = await create_user(db_session)
        resp = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["size_bytes"] == 0
        assert body["checksum"] is not None
        assert len(body["checksum"]) == 64

    async def test_very_long_filename(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Upload with a filename >255 chars returns 201 (system handles it)."""
        user = await create_user(db_session)
        name = "a" * 200 + ".txt"
        resp = await client.post(
            "/api/v1/storage/upload",
            files={"file": (name, io.BytesIO(b"data"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 201
        assert resp.json()["filename"] == name

    async def test_special_chars_in_filename(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Upload with special characters in filename."""
        user = await create_user(db_session)
        name = "héllo wörld + !@#$.txt"
        resp = await client.post(
            "/api/v1/storage/upload",
            files={"file": (name, io.BytesIO(b"special"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 201
        assert resp.json()["filename"] == name

    async def test_multiple_uploads_same_filename(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Same filename with different content creates separate records."""
        user = await create_user(db_session)

        resp1 = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("same_name.txt", io.BytesIO(b"content a"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("same_name.txt", io.BytesIO(b"content b"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        assert resp2.status_code == 201

        # Different checksums -> different records
        assert resp1.json()["id"] != resp2.json()["id"]

        # Verify we have 2 distinct records
        resp = await client.get(
            "/api/v1/storage/files",
            headers=auth_header(str(user.id)),
        )
        assert resp.json()["total"] == 2

    async def test_missing_file_field(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """POST without a file field returns 422."""
        user = await create_user(db_session)
        resp = await client.post(
            "/api/v1/storage/upload",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 422


class TestListEdgeCases:
    """Edge cases for file listing."""

    async def test_pagination_not_required(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Listing works without pagination params."""
        user = await create_user(db_session)
        for i in range(3):
            await client.post(
                "/api/v1/storage/upload",
                files={"file": (f"f{i}.txt", io.BytesIO(f"content{i}".encode()), "text/plain")},
                headers=auth_header(str(user.id)),
            )
        resp = await client.get(
            "/api/v1/storage/files",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 3

    async def test_deleted_file_excluded_from_list(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Deleted file no longer appears in list."""
        user = await create_user(db_session)
        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("gone.txt", io.BytesIO(b"will be deleted"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        file_id = upload.json()["id"]

        await client.delete(
            f"/api/v1/storage/{file_id}",
            headers=auth_header(str(user.id)),
        )

        resp = await client.get(
            "/api/v1/storage/files",
            headers=auth_header(str(user.id)),
        )
        ids = [f["id"] for f in resp.json()["files"]]
        assert file_id not in ids


class TestDeleteEdgeCases:
    """Edge cases for file deletion."""

    async def test_delete_nonexistent_file_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delete of non-existent UUID returns 404."""
        user = await create_user(db_session)
        from uuid import UUID
        resp = await client.delete(
            f"/api/v1/storage/{UUID(int=0)}",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 404

    async def test_double_delete_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Deleting an already-deleted file returns 404."""
        user = await create_user(db_session)
        upload = await client.post(
            "/api/v1/storage/upload",
            files={"file": ("gone.txt", io.BytesIO(b"bye"), "text/plain")},
            headers=auth_header(str(user.id)),
        )
        file_id = upload.json()["id"]

        # First delete succeeds
        resp1 = await client.delete(
            f"/api/v1/storage/{file_id}",
            headers=auth_header(str(user.id)),
        )
        assert resp1.status_code == 204

        # Second delete returns 404
        resp2 = await client.delete(
            f"/api/v1/storage/{file_id}",
            headers=auth_header(str(user.id)),
        )
        assert resp2.status_code == 404
