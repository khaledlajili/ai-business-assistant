from uuid import UUID
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Order, Customer


async def get_customer_order_summary(
    session: AsyncSession,
    workspace_id: UUID,
    customer_id: UUID,
    limit_orders: int = 5,
) -> dict:
    # Totals
    totals_stmt = (
        select(
            func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"),
            func.count(Order.id).label("order_count"),
        )
        .where(Order.workspace_id == workspace_id)
        .where(Order.customer_id == customer_id)
        .where(Order.status.in_(["paid", "completed"]))
    )
    totals = (await session.execute(totals_stmt)).one()

    # Last N orders
    orders_stmt = (
        select(Order)
        .where(Order.workspace_id == workspace_id)
        .where(Order.customer_id == customer_id)
        .order_by(Order.ordered_at.desc())
        .limit(limit_orders)
    )
    orders = (await session.execute(orders_stmt)).scalars().all()

    return {
        "total_spent": Decimal(totals.total_spent),
        "order_count": totals.order_count,
        "recent_orders": [
            {
                "id": str(o.id),
                "status": o.status,
                "total_amount": o.total_amount,
                "ordered_at": o.ordered_at.isoformat(),
            }
            for o in orders
        ],
    }


async def get_sales_summary(
    session: AsyncSession,
    workspace_id: UUID,
    start: datetime,
    end: datetime,
) -> dict:
    stmt = (
        select(
            func.coalesce(func.sum(Order.total_amount), 0).label("total"),
            func.count(Order.id).label("count"),
        )
        .where(Order.workspace_id == workspace_id)
        .where(Order.status.in_(["paid", "completed"]))
        .where(Order.ordered_at >= start)
        .where(Order.ordered_at < end)
    )
    row = (await session.execute(stmt)).one()
    return {
        "total_amount": Decimal(row.total),
        "order_count": row.count,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
    }


async def find_inactive_high_value_customers(
    session: AsyncSession,
    workspace_id: UUID,
    minimum_spend: Decimal,
    prev_start: datetime,
    prev_end: datetime,
    curr_start: datetime,
    curr_end: datetime,
) -> list[dict]:
    """
    Main business query:
    - sum(paid + completed) in previous month > minimum_spend
    - no paid/completed order in current month
    - customer is active
    """
    # Subquery: spend in previous month
    prev_spend = (
        select(
            Order.customer_id,
            func.sum(Order.total_amount).label("spent"),
        )
        .where(Order.workspace_id == workspace_id)
        .where(Order.status.in_(["paid", "completed"]))
        .where(Order.ordered_at >= prev_start)
        .where(Order.ordered_at < prev_end)
        .group_by(Order.customer_id)
        .having(func.sum(Order.total_amount) > minimum_spend)
        .subquery()
    )

    # Customers who have any paid/completed order in current month
    current_active = (
        select(Order.customer_id)
        .where(Order.workspace_id == workspace_id)
        .where(Order.status.in_(["paid", "completed"]))
        .where(Order.ordered_at >= curr_start)
        .where(Order.ordered_at < curr_end)
        .distinct()
        .subquery()
    )

    stmt = (
        select(
            Customer.id,
            Customer.name,
            Customer.email,
            prev_spend.c.spent,
        )
        .join(prev_spend, Customer.id == prev_spend.c.customer_id)
        .where(Customer.workspace_id == workspace_id)
        .where(Customer.is_active.is_(True))
        .where(Customer.id.not_in(select(current_active.c.customer_id)))
        .order_by(prev_spend.c.spent.desc())
    )

    rows = (await session.execute(stmt)).all()
    return [
        {
            "customer_id": str(r.id),
            "name": r.name,
            "email": r.email,
            "previous_month_spend": Decimal(r.spent),
        }
        for r in rows
    ]
