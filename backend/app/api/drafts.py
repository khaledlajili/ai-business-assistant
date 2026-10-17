from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.auth import UserOut
from app.services.draft_service import (
    DraftService, PermissionDenied, DraftNotFound, InvalidState
)

router = APIRouter(prefix="/drafts", tags=["drafts"])


class EditDraftRequest(BaseModel):
    subject: str | None = None
    body: str | None = None


class SendRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=8, max_length=64)
    force_fail: bool = False


@router.get("")
async def list_drafts(
    status: str | None = Query(None),
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = DraftService(db)
    try:
        return await svc.list_drafts(current_user.workspace_id, current_user.role, status)
    except PermissionDenied as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{draft_id}")
async def edit_draft(
    draft_id: UUID,
    body: EditDraftRequest,
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = DraftService(db)
    try:
        return await svc.edit_draft(
            current_user.workspace_id, current_user.role, draft_id,
            subject=body.subject, body=body.body,
        )
    except PermissionDenied as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except DraftNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")


@router.post("/{draft_id}/approve")
async def approve_draft(
    draft_id: UUID,
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = DraftService(db)
    try:
        return await svc.approve(current_user.workspace_id, current_user.role, draft_id)
    except PermissionDenied as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except DraftNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    except InvalidState as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{draft_id}/reject")
async def reject_draft(
    draft_id: UUID,
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = DraftService(db)
    try:
        return await svc.reject(current_user.workspace_id, current_user.role, draft_id)
    except PermissionDenied as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except DraftNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    except InvalidState as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{draft_id}/send")
async def send_draft(
    draft_id: UUID,
    body: SendRequest,
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = DraftService(db)
    try:
        return await svc.send(
            current_user.workspace_id,
            current_user.role,
            draft_id,
            idempotency_key=body.idempotency_key,
            force_fail=body.force_fail,
        )
    except PermissionDenied as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except DraftNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    except InvalidState as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
