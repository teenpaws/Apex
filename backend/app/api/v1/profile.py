"""
Profile API — career profile + document upload/management routes.

All routes require a valid Bearer token (or mock-user in USE_MOCK_DATA mode).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.services.profile_service import ProfileService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/profile", tags=["profile"])

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


# ── Request schemas ─────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    current_role: str | None = None
    target_roles: list[str] | None = None
    industries: list[str] | None = None
    aspirations_text: str | None = None


# ── Profile routes ──────────────────────────────────────────────────────────

@router.get("", response_model=dict, summary="Get career profile")
async def get_profile(current_user: dict = Depends(get_current_user)) -> dict:
    settings = get_settings()
    return await ProfileService(
        user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA
    ).get_profile()


@router.put("", response_model=dict, summary="Update career profile")
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    return await ProfileService(
        user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA
    ).update_profile(body.model_dump())


@router.post(
    "/analyze",
    response_model=dict,
    summary="Trigger profile extraction from all uploaded documents",
)
async def analyze_profile(current_user: dict = Depends(get_current_user)) -> dict:
    """Enqueue ProfileExtractor Celery task. Returns {run_id, status}."""
    settings = get_settings()
    if settings.USE_MOCK_DATA:
        return {"run_id": "mock-run-profile-001", "status": "queued"}

    from app.workers.extract_profile import extract_profile_from_documents
    task = extract_profile_from_documents.delay(user_id=current_user["id"])
    return {"run_id": str(task.id), "status": "queued"}


# ── Document routes ─────────────────────────────────────────────────────────

@router.get("/documents", response_model=list, summary="List uploaded documents")
async def list_documents(current_user: dict = Depends(get_current_user)) -> list:
    settings = get_settings()
    return await DocumentService(
        user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA
    ).list_documents()


@router.post("/documents", response_model=dict, summary="Upload resume or cover letter")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    target_context: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Accept PDF or DOCX, max 10 MB. doc_type must be RESUME, COVER_LETTER, or OTHER.
    Text extraction runs synchronously on upload. Returns doc metadata + extraction_status.
    """
    if doc_type not in ("RESUME", "COVER_LETTER", "OTHER"):
        raise HTTPException(
            status_code=422,
            detail="doc_type must be RESUME, COVER_LETTER, or OTHER",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")

    try:
        DocumentService.detect_file_type(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    settings = get_settings()
    svc = DocumentService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    return await svc.create_document(
        filename=file.filename or "upload",
        file_bytes=file_bytes,
        doc_type=doc_type,
        target_context=target_context,
    )


@router.delete("/documents/{doc_id}", response_model=dict, summary="Delete a document")
async def delete_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    return await DocumentService(
        user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA
    ).delete_document(doc_id)


@router.get(
    "/documents/pending-review",
    response_model=dict,
    summary="Get staged extraction output awaiting user approval",
)
async def get_pending_review(current_user: dict = Depends(get_current_user)) -> dict:
    settings = get_settings()
    return await ProfileService(
        user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA
    ).get_pending_review()


@router.post(
    "/documents/approve",
    response_model=dict,
    summary="Apply staged extraction fields to career profile",
)
async def approve_extraction(current_user: dict = Depends(get_current_user)) -> dict:
    settings = get_settings()
    return await ProfileService(
        user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA
    ).approve_extraction()
