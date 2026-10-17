import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_success(client):
    r = await client.post("/auth/login", json={"email": "manager@demo.local", "password": "manager123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_fail(client):
    r = await client.post("/auth/login", json={"email": "manager@demo.local", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client):
    login = await client.post("/auth/login", json={"email": "manager@demo.local", "password": "manager123"})
    token = login.json()["access_token"]
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "manager@demo.local"
    assert data["role"] == "manager"


@pytest.mark.asyncio
async def test_main_query_authenticated(client):
    login = await client.post("/auth/login", json={"email": "manager@demo.local", "password": "manager123"})
    token = login.json()["access_token"]
    r = await client.get(
        "/sales/inactive-high-value",
        params={"minimum_spend": "500"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_foreign_customer_returns_404(client):
    """Customer from another workspace must return 404, not 403."""
    login = await client.post("/auth/login", json={"email": "manager@demo.local", "password": "manager123"})
    token = login.json()["access_token"]
    # This ID belongs to the other workspace
    foreign_id = "e0000000-0000-0000-0000-000000000007"
    r = await client.get(
        f"/customers/{foreign_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
