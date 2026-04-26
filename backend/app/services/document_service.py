"""
DocumentService — CRUD for user_documents table + Supabase Storage.

Mock mode (USE_MOCK_DATA=True): returns fixture data, no DB/storage calls.
Live mode: asyncpg for DB, Supabase Python client for file storage.
"""
from __future__ import annotations

import asyncio
import functools
import uuid
from pathlib import Path

from app.services.document_extractor import DocumentExtractor


class DocumentService:
    """Service layer for document upload, listing, and deletion, scoped to one user."""

    _ALLOWED_EXTENSIONS = {"pdf": "PDF", "docx": "DOCX"}

    def __init__(self, user_id: str, use_mock: bool = False) -> None:
        self.user_id = user_id
        self.use_mock = use_mock

    # ── Public interface ──────────────────────────────────────────────────────

    @staticmethod
    def detect_file_type(filename: str) -> str:
        """Return 'PDF' or 'DOCX', raise ValueError for unsupported extensions."""
        if not filename:
            raise ValueError("Filename is required to determine file type.")
        ext = Path(filename).suffix.lstrip(".").lower()
        ft = DocumentService._ALLOWED_EXTENSIONS.get(ext)
        if not ft:
            raise ValueError(
                f"Unsupported file type: {ext!r}. Only PDF and DOCX are accepted."
            )
        return ft

    async def list_documents(self) -> list[dict]:
        if self.use_mock:
            return self._mock_list()
        return await self._live_list()

    async def create_document(
        self,
        filename: str,
        file_bytes: bytes,
        doc_type: str,
        target_context: str | None,
    ) -> dict:
        """Upload file, extract text, persist row. Returns doc metadata dict."""
        file_type = self.detect_file_type(filename)
        loop = asyncio.get_event_loop()
        extracted_text = await loop.run_in_executor(
            None, functools.partial(DocumentExtractor.extract, file_bytes, file_type)
        )

        if self.use_mock:
            return self._mock_create(filename, file_type, doc_type, target_context)

        return await self._live_create(
            filename=filename,
            file_bytes=file_bytes,
            file_type=file_type,
            doc_type=doc_type,
            target_context=target_context,
            extracted_text=extracted_text,
        )

    async def delete_document(self, doc_id: str) -> dict:
        if self.use_mock:
            return {"deleted": True, "doc_id": doc_id}
        return await self._live_delete(doc_id)

    # ── Mock implementations ──────────────────────────────────────────────────

    def _mock_list(self) -> list[dict]:
        return [
            {
                "id": "doc-001",
                "user_id": self.user_id,
                "filename": "resume_hec_mba.pdf",
                "file_type": "PDF",
                "doc_type": "RESUME",
                "target_context": None,
                "extraction_status": "EXTRACTED",
                "created_at": "2026-04-25T10:00:00Z",
            }
        ]

    def _mock_create(
        self,
        filename: str,
        file_type: str,
        doc_type: str,
        target_context: str | None,
    ) -> dict:
        return {
            "doc_id": str(uuid.uuid4()),
            "filename": filename,
            "file_type": file_type,
            "doc_type": doc_type,
            "target_context": target_context,
            "extraction_status": "EXTRACTED",
        }

    # ── Live implementations ──────────────────────────────────────────────────

    async def _live_list(self) -> list[dict]:
        import asyncpg
        from app.db.session import get_asyncpg_db_url

        conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
        try:
            rows = await conn.fetch(
                """SELECT id, user_id, filename, file_type, doc_type,
                          target_context, extraction_status, created_at
                   FROM user_documents
                   WHERE user_id = $1
                   ORDER BY created_at DESC""",
                uuid.UUID(self.user_id),
            )
            return [
                {
                    "id": str(r["id"]),
                    "user_id": str(r["user_id"]),
                    "filename": r["filename"],
                    "file_type": r["file_type"],
                    "doc_type": r["doc_type"],
                    "target_context": r["target_context"],
                    "extraction_status": r["extraction_status"],
                    "created_at": r["created_at"].isoformat(),
                }
                for r in rows
            ]
        finally:
            await conn.close()

    async def _live_create(
        self,
        filename: str,
        file_bytes: bytes,
        file_type: str,
        doc_type: str,
        target_context: str | None,
        extracted_text: str,
    ) -> dict:
        import asyncpg
        from app.core.config import get_settings
        from app.db.session import get_asyncpg_db_url

        settings = get_settings()
        doc_id = uuid.uuid4()
        storage_path = f"{self.user_id}/{doc_id}/{filename}"

        # Attempt Supabase Storage upload — non-fatal if it fails
        try:
            from supabase import create_client
            sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            sb.storage.from_("user-documents").upload(storage_path, file_bytes)
        except Exception:  # noqa: BLE001
            storage_path = None

        status = "EXTRACTED" if extracted_text else "PENDING"
        conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
        try:
            await conn.execute(
                """INSERT INTO user_documents
                   (id, user_id, filename, file_type, doc_type, storage_path,
                    extracted_text, target_context, extraction_status)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                doc_id,
                uuid.UUID(self.user_id),
                filename,
                file_type,
                doc_type,
                storage_path,
                extracted_text or None,
                target_context,
                status,
            )
        finally:
            await conn.close()

        return {
            "doc_id": str(doc_id),
            "filename": filename,
            "file_type": file_type,
            "doc_type": doc_type,
            "target_context": target_context,
            "extraction_status": status,
        }

    async def _live_delete(self, doc_id: str) -> dict:
        import asyncpg
        from app.core.config import get_settings
        from app.db.session import get_asyncpg_db_url

        settings = get_settings()
        conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                "SELECT storage_path FROM user_documents WHERE id = $1 AND user_id = $2",
                uuid.UUID(doc_id),
                uuid.UUID(self.user_id),
            )
            if not row:
                return {"deleted": False, "doc_id": doc_id, "reason": "not found"}

            if row["storage_path"]:
                try:
                    from supabase import create_client
                    sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
                    sb.storage.from_("user-documents").remove([row["storage_path"]])
                except Exception:  # noqa: BLE001
                    pass

            await conn.execute(
                "DELETE FROM user_documents WHERE id = $1 AND user_id = $2",
                uuid.UUID(doc_id),
                uuid.UUID(self.user_id),
            )
        finally:
            await conn.close()

        return {"deleted": True, "doc_id": doc_id}
