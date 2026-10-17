from decimal import Decimal
from uuid import UUID
from typing import Annotated
from pydantic import Field
from pydantic_ai import RunContext

from app.services.customer_service import CustomerService, PermissionDenied


class AgentDeps:
    def __init__(self, session, user, clock=None):
        self.session = session
        self.user = user
        self.clock = clock
        self.tool_results: list[dict] = []
        self.request_count = 0


def _record(ctx: RunContext[AgentDeps], tool: str, args: dict, result):
    ctx.deps.tool_results.append({"tool": tool, "args": args, "result": result})
    return result


async def search_customers(
    ctx: RunContext[AgentDeps],
    query: Annotated[str, Field(description="Search text (name or email)")],
    limit: Annotated[int, Field(description="Max results", ge=1, le=50)] = 10,
) -> dict:
    """Search customers by name or email. Returns only id and name."""
    svc = CustomerService(ctx.deps.session, clock=ctx.deps.clock)
    try:
        results = await svc.search(
            ctx.deps.user.workspace_id,
            ctx.deps.user.role,
            query,
            limit,
        )
    except PermissionDenied as e:
        return _record(ctx, "search_customers", {"query": query, "limit": limit}, {"error": str(e)})

    payload = {
        "found": len(results) > 0,
        "count": len(results),
        "customers": results,
        "message": (
            f"Found {len(results)} customer(s)."
            if results
            else f"No customers found matching '{query}'."
        ),
    }
    return _record(ctx, "search_customers", {"query": query, "limit": limit}, payload)


async def get_customer_summary(
    ctx: RunContext[AgentDeps],
    customer_id: Annotated[str, Field(description="Customer UUID")],
) -> dict:
    """Get totals and last 5 orders for one customer."""
    svc = CustomerService(ctx.deps.session, clock=ctx.deps.clock)
    try:
        result = await svc.get_summary(
            ctx.deps.user.workspace_id,
            ctx.deps.user.role,
            UUID(customer_id),
        )
    except PermissionDenied as e:
        return _record(ctx, "get_customer_summary", {"customer_id": customer_id}, {"error": str(e)})

    if result is None:
        payload = {"found": False, "message": "Customer not found."}
    else:
        payload = {"found": True, **result}
    return _record(ctx, "get_customer_summary", {"customer_id": customer_id}, payload)


async def get_sales_summary(
    ctx: RunContext[AgentDeps],
    period: Annotated[str, Field(description="One of: previous_month, current_month, last_30_days")],
) -> dict:
    """Get sales totals for a period. The server resolves the dates."""
    svc = CustomerService(ctx.deps.session, clock=ctx.deps.clock)
    try:
        result = await svc.sales_summary(
            ctx.deps.user.workspace_id,
            ctx.deps.user.role,
            period,
            timezone="Africa/Tunis",
        )
    except PermissionDenied as e:
        return _record(ctx, "get_sales_summary", {"period": period}, {"error": str(e)})
    return _record(ctx, "get_sales_summary", {"period": period}, result)


async def find_inactive_high_value_customers(
    ctx: RunContext[AgentDeps],
    minimum_spend: Annotated[float, Field(description="Minimum spend in DT in the previous month")],
) -> dict:
    """
    Find active customers who spent more than minimum_spend in the previous month
    but have no paid/completed order in the current month.
    """
    svc = CustomerService(ctx.deps.session, clock=ctx.deps.clock)
    try:
        results = await svc.find_inactive_high_value(
            ctx.deps.user.workspace_id,
            ctx.deps.user.role,
            Decimal(str(minimum_spend)),
            timezone="Africa/Tunis",
        )
    except PermissionDenied as e:
        return _record(
            ctx,
            "find_inactive_high_value_customers",
            {"minimum_spend": minimum_spend},
            {"error": str(e)},
        )

    compact = [
        {
            "customer_id": r["customer_id"],
            "name": r["name"],
            "previous_month_spend": str(r["previous_month_spend"]),
        }
        for r in results
    ]
    payload = {
        "found": len(compact) > 0,
        "count": len(compact),
        "customers": compact,
        "message": (
            f"Found {len(compact)} customer(s)."
            if compact
            else f"No inactive high-value customers above {minimum_spend} DT."
        ),
    }
    return _record(
        ctx,
        "find_inactive_high_value_customers",
        {"minimum_spend": minimum_spend},
        payload,
    )


async def create_follow_up_drafts(
    ctx: RunContext[AgentDeps],
    items: Annotated[
        list[dict],
        Field(description="List of {customer_id, subject, body}. Max 10 items."),
    ],
) -> dict:
    """Create up to 10 email drafts. Recipient is taken from the database."""
    from app.services.draft_service import DraftService, PermissionDenied as DraftPermDenied

    svc = DraftService(ctx.deps.session)
    try:
        results = await svc.create_drafts(
            ctx.deps.user.workspace_id,
            ctx.deps.user.id,
            ctx.deps.user.role,
            items,
        )
    except DraftPermDenied as e:
        return _record(ctx, "create_follow_up_drafts", {"items_count": len(items)}, {"error": str(e)})
    except Exception as e:
        return _record(ctx, "create_follow_up_drafts", {"items_count": len(items)}, {"error": str(e)})

    payload = {
        "found": len(results) > 0,
        "count": len(results),
        "drafts": results,
        "message": f"Created {len(results)} draft(s)." if results else "No drafts created.",
    }
    return _record(ctx, "create_follow_up_drafts", {"items_count": len(items)}, payload)


async def list_email_drafts(
    ctx: RunContext[AgentDeps],
    status: Annotated[
        str,
        Field(description="Filter by status: pending_review, approved, sent, failed, rejected"),
    ] = "pending_review",
) -> dict:
    """List email drafts filtered by status."""
    from app.services.draft_service import DraftService, PermissionDenied as DraftPermDenied

    svc = DraftService(ctx.deps.session)
    try:
        results = await svc.list_drafts(
            ctx.deps.user.workspace_id,
            ctx.deps.user.role,
            status=status,
            limit=50,
        )
    except DraftPermDenied as e:
        return _record(ctx, "list_email_drafts", {"status": status}, {"error": str(e)})

    compact = [
        {
            "draft_id": r["draft_id"],
            "customer_name": r["customer_name"],
            "subject": r["subject"],
            "status": r["status"],
        }
        for r in results
    ]
    payload = {
        "found": len(compact) > 0,
        "count": len(compact),
        "drafts": compact,
        "message": (
            f"Found {len(compact)} draft(s) with status '{status}'."
            if compact
            else f"There are currently no email drafts with status '{status}'."
        ),
    }
    return _record(ctx, "list_email_drafts", {"status": status}, payload)
