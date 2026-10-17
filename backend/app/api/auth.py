from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models import User, WorkspaceMembership, Workspace
from app.core.security import verify_password, create_access_token
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services.audit import log_audit
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == body.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        await log_audit(
            db,
            action="login_failed",
            details=f"email={body.email}",
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    stmt = (
        select(WorkspaceMembership, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .where(WorkspaceMembership.user_id == user.id)
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no workspace")

    membership, workspace = row

    token = create_access_token({
        "sub": str(user.id),
        "workspace_id": str(workspace.id),
        "role": membership.role,
    })

    await log_audit(
        db,
        action="login_success",
        user_id=user.id,
        workspace_id=workspace.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: UserOut = Depends(get_current_user)):
    return current_user
