"""
Run once to generate expected_main_query.json
"""
import asyncio
import json
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import UUID

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.clock import Clock
from app.services.customer_service import CustomerService

WS1_ID = UUID("11111111-1111-1111-1111-111111111111")

# Freeze time to 15 Oct 2026 12:00 Africa/Tunis (same as seed)
FIXED_NOW = datetime(2026, 10, 15, 12, 0, tzinfo=ZoneInfo("Africa/Tunis"))


async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        clock = Clock(fixed_now=FIXED_NOW)
        svc = CustomerService(session, clock=clock)
        results = await svc.find_inactive_high_value(
            workspace_id=WS1_ID,
            role="manager",
            minimum_spend=Decimal("500.000"),
            timezone="Africa/Tunis",
        )

    print(json.dumps(results, indent=2, default=str))
    with open("tests/expected_main_query.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nSaved to tests/expected_main_query.json")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
