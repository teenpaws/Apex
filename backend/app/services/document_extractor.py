"""
DocumentExtractor — local text extraction from PDF and DOCX files.

No API calls. Runs in-process. Called synchronously on file upload.
Both pdfplumber (PDF) and python-docx (DOCX) are installed in requirements.txt.
"""
from __future__ import annotations

import io
import re


class DocumentExtractor:
    """Static helper for extracting plain text from PDF or DOCX bytes."""

    @staticmethod
    def extract(file_bytes: bytes, file_type: str) -> str:
        """
        Extract plain text from file bytes.

        Args:
            file_bytes: Raw file content.
            file_type:  'PDF' or 'DOCX' (case-insensitive).

        Returns:
            Extracted text, whitespace-normalised. Empty string on parse failure.

        Raises:
            ValueError: If file_type is not 'PDF' or 'DOCX'.
        """
        ft = file_type.upper()
        if ft == "PDF":
            return DocumentExtractor._extract_pdf(file_bytes)
        if ft == "DOCX":
            return DocumentExtractor._extract_docx(file_bytes)
        raise ValueError(
            f"Unsupported file type: {file_type!r}. Expected 'PDF' or 'DOCX'."
        )

    @staticmethod
    def _extract_pdf(file_bytes: bytes) -> str:
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError(
                "pdfplumber is not installed. Run: pip install pdfplumber==0.11.4"
            )
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            raw = "\n".join(pages)
            return DocumentExtractor._normalise(raw)
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _extract_docx(file_bytes: bytes) -> str:
        try:
            from docx import Document
        except ImportError:
            raise RuntimeError(
                "python-docx is not installed. Run: pip install python-docx==1.1.2"
            )
        try:
            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            raw = "\n".join(paragraphs)
            return DocumentExtractor._normalise(raw)
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _normalise(text: str) -> str:
        """Collapse runs of whitespace (spaces, tabs) to single space per line."""
        lines = text.splitlines()
        cleaned = [re.sub(r"[ \t]{2,}", " ", line).strip() for line in lines]
        return "\n".join(line for line in cleaned if line)
