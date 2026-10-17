import hashlib
import uuid
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmailDraft, EmailDelivery, Customer
from app.core.permissions import Permission, has_permission


class PermissionDenied(Exception):
    pass


class DraftNotFound(Exception):
    pass


class InvalidState(Exception):
    pass


def _content_hash(subject: str, body: str, recipient: str) -> str:
    raw = f"{subject}|{body}|{recipient}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class DraftService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _check(self, role: str, perm: Permission):
        if not has_permission(role, perm):
            raise PermissionDenied(f"Role '{role}' lacks permission '{perm.value}'")

    async def create_drafts(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: str,
        items: list[dict],
    ) -> list[dict]:
        """items = [{customer_id, subject, body}, ...]  max 10"""
        self._check(role, Permission.DRAFT_CREATE)
        if len(items) > 10:
            raise ValueError("Maximum 10 drafts per call")

        created = []
        for item in items:
            customer_id = UUID(item["customer_id"])
            # Verify customer belongs to workspace
            stmt = select(Customer).where(
                Customer.id == customer_id,
                Customer.workspace_id == workspace_id,
            )
            customer = (await self.session.execute(stmt)).scalar_one_or_none()
            if not customer:
                continue  # skip unknown / foreign customers

            draft = EmailDraft(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                customer_id=customer_id,
                subject=item["subject"],
                body=item["body"],
                status="pending_review",
                content_hash=None,
                created_by=user_id,
            )
            self.session.add(draft)
            created.append({
                "draft_id": str(draft.id),
                "customer_id": str(customer_id),
                "customer_name": customer.name,
                "subject": draft.subject,
                "status": draft.status,
            })

        await self.session.commit()
        return created

    async def list_drafts(
        self,
        workspace_id: UUID,
        role: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        self._check(role, Permission.DRAFT_READ)
        stmt = (
            select(EmailDraft, Customer)
            .join(Customer, Customer.id == EmailDraft.customer_id)
            .where(EmailDraft.workspace_id == workspace_id)
            .order_by(EmailDraft.created_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(EmailDraft.status == status)

        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "draft_id": str(d.id),
                "customer_id": str(d.customer_id),
                "customer_name": c.name,
                "customer_email": c.email,
                "subject": d.subject,
                "body": d.body,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d, c in rows
        ]

    async def get_draft(self, workspace_id: UUID, draft_id: UUID) -> EmailDraft | None:
        stmt = select(EmailDraft).where(
            EmailDraft.id == draft_id,
            EmailDraft.workspace_id == workspace_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def edit_draft(
        self,
        workspace_id: UUID,
        role: str,
        draft_id: UUID,
        subject: str | None = None,
        body: str | None = None,
    ) -> dict:
        self._check(role, Permission.DRAFT_CREATE)  # same permission as create
        draft = await self.get_draft(workspace_id, draft_id)
        if not draft:
            raise DraftNotFound()

        if subject is not None:
            draft.subject = subject
        if body is not None:
            draft.body = body
        # Any edit returns to pending_review
        draft.status = "pending_review"
        draft.content_hash = None
        draft.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return {"draft_id": str(draft.id), "status": draft.status}

    async def approve(
        self,
        workspace_id: UUID,
        role: str,
        draft_id: UUID,
    ) -> dict:
        self._check(role, Permission.DRAFT_APPROVE)
        draft = await self.get_draft(workspace_id, draft_id)
        if not draft:
            raise DraftNotFound()
        if draft.status != "pending_review":
            raise InvalidState(f"Cannot approve draft in status '{draft.status}'")

        # Load recipient
        stmt = select(Customer).where(Customer.id == draft.customer_id)
        customer = (await self.session.execute(stmt)).scalar_one()
        recipient = customer.email

        draft.status = "approved"
        draft.content_hash = _content_hash(draft.subject, draft.body, recipient)
        draft.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return {"draft_id": str(draft.id), "status": draft.status, "content_hash": draft.content_hash}

    async def reject(
        self,
        workspace_id: UUID,
        role: str,
        draft_id: UUID,
    ) -> dict:
        self._check(role, Permission.DRAFT_APPROVE)
        draft = await self.get_draft(workspace_id, draft_id)
        if not draft:
            raise DraftNotFound()
        if draft.status != "pending_review":
            raise InvalidState(f"Cannot reject draft in status '{draft.status}'")

        draft.status = "rejected"
        draft.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return {"draft_id": str(draft.id), "status": draft.status}

    async def send(
        self,
        workspace_id: UUID,
        role: str,
        draft_id: UUID,
        idempotency_key: str,
        force_fail: bool = False,
    ) -> dict:
        self._check(role, Permission.DRAFT_SEND)
        draft = await self.get_draft(workspace_id, draft_id)
        if not draft:
            raise DraftNotFound()
        if draft.status not in ("approved", "sending", "sent", "failed"):
            raise InvalidState(f"Cannot send draft in status '{draft.status}'")

        # Idempotency: if we already have a delivery with this key, return it
        stmt = select(EmailDelivery).where(EmailDelivery.idempotency_key == idempotency_key)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return {
                "draft_id": str(draft.id),
                "delivery_id": str(existing.id),
                "status": existing.status,
                "idempotent": True,
            }

        # Atomic claim
        if draft.status == "approved":
            draft.status = "sending"
            await self.session.commit()

        # Load recipient
        stmt = select(Customer).where(Customer.id == draft.customer_id)
        customer = (await self.session.execute(stmt)).scalar_one()
        recipient = customer.email

        # Verify hash still matches (content not changed after approval)
        current_hash = _content_hash(draft.subject, draft.body, recipient)
        if draft.content_hash and draft.content_hash != current_hash:
            draft.status = "pending_review"
            draft.content_hash = None
            await self.session.commit()
            raise InvalidState("Content changed after approval – returned to pending_review")

        # Simulated provider
        from app.services.email_provider import send_email
        try:
            provider_response = await send_email(
                to=recipient,
                subject=draft.subject,
                body=draft.body,
                force_fail=force_fail,
            )
            delivery_status = "sent"
            draft.status = "sent"
        except Exception as e:
            provider_response = str(e)
            delivery_status = "failed"
            draft.status = "failed"

        delivery = EmailDelivery(
            id=uuid.uuid4(),
            draft_id=draft.id,
            idempotency_key=idempotency_key,
            status=delivery_status,
            provider_response=provider_response,
        )
        self.session.add(delivery)
        await self.session.commit()

        return {
            "draft_id": str(draft.id),
            "delivery_id": str(delivery.id),
            "status": delivery_status,
            "idempotent": False,
        }
