from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditEvent


async def log_audit(
    session: AsyncSession,
    *,
    action: str,
    user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> None:
    event = AuditEvent(
        action=action,
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    session.add(event)
    # Do NOT commit here – the request will commit (or rollback) the session
