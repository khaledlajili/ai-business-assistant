"""Draft lifecycle tests – no LLM (avoids event-loop issues under pytest)."""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.services.draft_service import DraftService
from uuid import UUID

WS1 = UUID("11111111-1111-1111-1111-111111111111")
MANAGER_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CUST_OVER = "e0000000-0000-0000-0000-000000000002"
CUST_INJ = "e0000000-0000-0000-0000-000000000008"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _login(client, email, password):
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


async def _create_draft_via_service(customer_id: str, subject: str, body: str) -> str:
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        svc = DraftService(session)
        results = await svc.create_drafts(
            workspace_id=WS1,
            user_id=MANAGER_ID,
            role="manager",
            items=[{
                "customer_id": customer_id,
                "subject": subject,
                "body": body,
            }],
        )
    await engine.dispose()
    assert results, "create_drafts returned empty"
    return results[0]["draft_id"]


@pytest.mark.asyncio
async def test_draft_lifecycle_and_idempotent_send(client):
    token = await _login(client, "manager@demo.local", "manager123")
    headers = {"Authorization": f"Bearer {token}"}

    draft_id = await _create_draft_via_service(
        CUST_OVER, "Test draft", "Hello, we miss you."
    )

    listed = await client.get("/drafts", params={"status": "pending_review"}, headers=headers)
    assert listed.status_code == 200
    assert draft_id in [d["draft_id"] for d in listed.json()]

    approved = await client.post(f"/drafts/{draft_id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["content_hash"]

    key = f"test-{uuid.uuid4()}"
    send1 = await client.post(
        f"/drafts/{draft_id}/send",
        headers=headers,
        json={"idempotency_key": key},
    )
    assert send1.status_code == 200
    body1 = send1.json()
    assert body1["status"] == "sent"
    assert body1["idempotent"] is False
    delivery_id = body1["delivery_id"]

    send2 = await client.post(
        f"/drafts/{draft_id}/send",
        headers=headers,
        json={"idempotency_key": key},
    )
    assert send2.status_code == 200
    body2 = send2.json()
    assert body2["idempotent"] is True
    assert body2["delivery_id"] == delivery_id
    assert body2["status"] == "sent"


@pytest.mark.asyncio
async def test_viewer_cannot_create_draft():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        svc = DraftService(session)
        from app.services.draft_service import PermissionDenied
        with pytest.raises(PermissionDenied):
            await svc.create_drafts(
                workspace_id=WS1,
                user_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                role="viewer",
                items=[{
                    "customer_id": CUST_OVER,
                    "subject": "Should fail",
                    "body": "No",
                }],
            )
    await engine.dispose()


@pytest.mark.asyncio
async def test_forced_failure(client):
    token = await _login(client, "manager@demo.local", "manager123")
    headers = {"Authorization": f"Bearer {token}"}

    draft_id = await _create_draft_via_service(
        CUST_INJ, "Fail test", "This will fail."
    )

    await client.post(f"/drafts/{draft_id}/approve", headers=headers)

    key = f"fail-{uuid.uuid4()}"
    send = await client.post(
        f"/drafts/{draft_id}/send",
        headers=headers,
        json={"idempotency_key": key, "force_fail": True},
    )
    assert send.status_code == 200
    assert send.json()["status"] == "failed"
