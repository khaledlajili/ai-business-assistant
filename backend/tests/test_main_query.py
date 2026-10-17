import pytest
import json
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import UUID

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.clock import Clock, get_month_boundaries
from app.services.customer_service import CustomerService, PermissionDenied
from app.core.permissions import Permission, has_permission

WS1_ID = UUID("11111111-1111-1111-1111-111111111111")

# Fixed reference time matching the seed
FIXED_NOW = datetime(2026, 10, 15, 12, 0, tzinfo=ZoneInfo("Africa/Tunis"))

# Edge-case IDs from seed
CUST_EXACT_500 = "e0000000-0000-0000-0000-000000000001"
CUST_OVER_500 = "e0000000-0000-0000-0000-000000000002"
CUST_THREE_200 = "e0000000-0000-0000-0000-000000000003"
CUST_CANCELLED = "e0000000-0000-0000-0000-000000000004"
CUST_MIDNIGHT = "e0000000-0000-0000-0000-000000000005"
CUST_JANUARY = "e0000000-0000-0000-0000-000000000006"
CUST_OTHER_WS = "e0000000-0000-0000-0000-000000000007"
CUST_INJECTION = "e0000000-0000-0000-0000-000000000008"


@pytest.fixture
async def session():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def clock():
    return Clock(fixed_now=FIXED_NOW)


@pytest.mark.asyncio
async def test_month_boundaries(clock):
    prev_start, prev_end, curr_start, curr_end = get_month_boundaries(
        clock.now("Africa/Tunis"), "Africa/Tunis"
    )
    assert prev_start.isoformat().startswith("2026-09-01")
    assert prev_end.isoformat().startswith("2026-10-01")
    assert curr_start.isoformat().startswith("2026-10-01")
    assert curr_end.isoformat().startswith("2026-11-01")


@pytest.mark.asyncio
async def test_main_query_edge_cases(session, clock):
    svc = CustomerService(session, clock=clock)
    results = await svc.find_inactive_high_value(
        workspace_id=WS1_ID,
        role="manager",
        minimum_spend=Decimal("500.000"),
        timezone="Africa/Tunis",
    )
    ids = {r["customer_id"] for r in results}

    # Must be included
    assert CUST_OVER_500 in ids, "500.001 should be included"
    assert CUST_THREE_200 in ids, "three × 200 should be included"
    assert CUST_INJECTION in ids, "injection customer qualifies"

    # Must be excluded
    assert CUST_EXACT_500 not in ids, "exact 500.000 must be excluded"
    assert CUST_CANCELLED not in ids, "only cancelled orders must be excluded"
    assert CUST_MIDNIGHT not in ids, "has current-month order → excluded"
    assert CUST_OTHER_WS not in ids, "other workspace must not appear"
    assert CUST_JANUARY not in ids, "January order is not previous month"


@pytest.mark.asyncio
async def test_viewer_can_run_main_query(session, clock):
    """Viewer has sales:read, so the main query is allowed."""
    svc = CustomerService(session, clock=clock)
    results = await svc.find_inactive_high_value(
        workspace_id=WS1_ID,
        role="viewer",
        minimum_spend=Decimal("500.000"),
        timezone="Africa/Tunis",
    )
    assert isinstance(results, list)
    assert len(results) >= 3


@pytest.mark.asyncio
async def test_permissions_map():
    assert has_permission("viewer", Permission.SALES_READ) is True
    assert has_permission("viewer", Permission.DRAFT_CREATE) is False
    assert has_permission("manager", Permission.DRAFT_APPROVE) is True
    assert has_permission("sales_rep", Permission.DRAFT_APPROVE) is False
    assert has_permission("unknown", Permission.SALES_READ) is False


@pytest.mark.asyncio
async def test_search_does_not_return_notes_or_email(session, clock):
    svc = CustomerService(session, clock=clock)
    results = await svc.search(WS1_ID, "manager", "Injection")
    assert len(results) >= 1
    for r in results:
        assert "notes" not in r
        assert "email" not in r
