"""
Unit tests for DocumentService (mock mode only).
Tests: list_documents, create_document, delete_document, detect_file_type.
"""
from __future__ import annotations
import pytest

_MODULE = "app.services.document_service"


class TestDocumentServiceMock:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_list_documents_returns_list(self):
        from app.services.document_service import DocumentService
        svc = DocumentService(user_id="00000000-0000-0000-0000-000000000001", use_mock=True)
        result = await svc.list_documents()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_create_document_returns_dict_with_doc_id(self):
        from app.services.document_service import DocumentService
        svc = DocumentService(user_id="00000000-0000-0000-0000-000000000001", use_mock=True)
        result = await svc.create_document(
            filename="resume.pdf",
            file_bytes=b"PDF_CONTENT",
            doc_type="RESUME",
            target_context=None,
        )
        assert isinstance(result, dict)
        assert "doc_id" in result
        assert result["extraction_status"] == "EXTRACTED"

    @pytest.mark.asyncio
    async def test_create_cover_letter_with_context(self):
        from app.services.document_service import DocumentService
        svc = DocumentService(user_id="00000000-0000-0000-0000-000000000001", use_mock=True)
        result = await svc.create_document(
            filename="cover_pe.docx",
            file_bytes=b"DOCX_CONTENT",
            doc_type="COVER_LETTER",
            target_context="PE firms",
        )
        assert result["doc_type"] == "COVER_LETTER"
        assert result["target_context"] == "PE firms"

    @pytest.mark.asyncio
    async def test_delete_document_returns_success(self):
        from app.services.document_service import DocumentService
        svc = DocumentService(user_id="00000000-0000-0000-0000-000000000001", use_mock=True)
        result = await svc.delete_document("some-doc-id")
        assert result["deleted"] is True

    def test_detect_file_type_pdf(self):
        from app.services.document_service import DocumentService
        assert DocumentService.detect_file_type("my_resume.pdf") == "PDF"

    def test_detect_file_type_docx(self):
        from app.services.document_service import DocumentService
        assert DocumentService.detect_file_type("resume.DOCX") == "DOCX"

    def test_detect_file_type_invalid_raises_value_error(self):
        from app.services.document_service import DocumentService
        with pytest.raises(ValueError, match="Unsupported"):
            DocumentService.detect_file_type("resume.txt")

    def test_detect_file_type_empty_filename_raises(self):
        from app.services.document_service import DocumentService
        with pytest.raises(ValueError, match="Filename is required"):
            DocumentService.detect_file_type("")

    def test_detect_file_type_no_extension_raises(self):
        from app.services.document_service import DocumentService
        with pytest.raises(ValueError):
            DocumentService.detect_file_type("resume")
