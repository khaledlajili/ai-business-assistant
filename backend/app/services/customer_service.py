from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import Permission, has_permission
from app.core.clock import Clock, get_month_boundaries
from app.repositories import customers as customer_repo
from app.repositories import orders as order_repo


class PermissionDenied(Exception):
    pass


class CustomerService:
    def __init__(self, session: AsyncSession, clock: Clock | None = None):
        self.session = session
        self.clock = clock or Clock()

    def _check(self, role: str, perm: Permission):
        if not has_permission(role, perm):
            raise PermissionDenied(f"Role '{role}' lacks permission '{perm.value}'")

    async def search(self, workspace_id: UUID, role: str, query: str, limit: int = 10):
        self._check(role, Permission.CUSTOMERS_READ)
        customers = await customer_repo.search_customers(self.session, workspace_id, query, limit)
        # Never return notes or full email in list? Plan says "No emails or notes returned"
        return [
            {
                "id": str(c.id),
                "name": c.name,
                # email intentionally omitted for search results
            }
            for c in customers
        ]

    async def get_summary(self, workspace_id: UUID, role: str, customer_id: UUID):
        self._check(role, Permission.CUSTOMERS_READ)
        customer = await customer_repo.get_customer(self.session, workspace_id, customer_id)
        if not customer:
            return None
        summary = await order_repo.get_customer_order_summary(self.session, workspace_id, customer_id)
        return {
            "customer_id": str(customer.id),
            "name": customer.name,
            "total_spent": summary["total_spent"],
            "order_count": summary["order_count"],
            "recent_orders": summary["recent_orders"],
        }

    async def sales_summary(self, workspace_id: UUID, role: str, period: str, timezone: str = "Africa/Tunis"):
        self._check(role, Permission.SALES_READ)
        now = self.clock.now(timezone)
        prev_start, prev_end, curr_start, curr_end = get_month_boundaries(now, timezone)

        if period == "previous_month":
            start, end = prev_start, prev_end
        elif period == "current_month":
            start, end = curr_start, curr_end
        elif period == "last_30_days":
            end = now
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            from datetime import timedelta
            start = start - timedelta(days=30)
        else:
            raise ValueError(f"Unknown period: {period}")

        return await order_repo.get_sales_summary(self.session, workspace_id, start, end)

    async def find_inactive_high_value(
        self,
        workspace_id: UUID,
        role: str,
        minimum_spend: Decimal,
        timezone: str = "Africa/Tunis",
    ):
        self._check(role, Permission.SALES_READ)
        now = self.clock.now(timezone)
        prev_start, prev_end, curr_start, curr_end = get_month_boundaries(now, timezone)

        return await order_repo.find_inactive_high_value_customers(
            self.session,
            workspace_id,
            minimum_spend,
            prev_start,
            prev_end,
            curr_start,
            curr_end,
        )
