from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import decode_access_token
from app.models import User, WorkspaceMembership, Workspace
from app.schemas.auth import UserOut

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    workspace_id = payload.get("workspace_id")
    role = payload.get("role")

    if not user_id or not workspace_id or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Load user + membership to make sure they still exist
    stmt = (
        select(User, WorkspaceMembership, Workspace)
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.id)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .where(User.id == UUID(user_id))
        .where(WorkspaceMembership.workspace_id == UUID(workspace_id))
        .where(User.is_active.is_(True))
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User or membership not found")

    user, membership, workspace = row
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        workspace_id=workspace.id,
        workspace_name=workspace.name,
    )
