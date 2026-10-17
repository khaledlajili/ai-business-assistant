from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Customer


async def search_customers(
    session: AsyncSession,
    workspace_id: UUID,
    query: str,
    limit: int = 10,
) -> list[Customer]:
    stmt = (
        select(Customer)
        .where(Customer.workspace_id == workspace_id)
        .where(Customer.is_active.is_(True))
        .where(
            or_(
                Customer.name.ilike(f"%{query}%"),
                Customer.email.ilike(f"%{query}%"),
            )
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_customer(
    session: AsyncSession,
    workspace_id: UUID,
    customer_id: UUID,
) -> Customer | None:
    stmt = (
        select(Customer)
        .where(Customer.workspace_id == workspace_id)
        .where(Customer.id == customer_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
