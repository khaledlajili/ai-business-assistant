import time
import logging
from uuid import uuid4
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.auth import UserOut
from app.agent.agent import agent
from app.agent.tools import AgentDeps
from app.models import LlmCall
from app.core.config import settings
from app.core.clock import Clock

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    tool_results: list[dict]


def _reply_from_tools(tool_results: list[dict]) -> str | None:
    """Truthful markdown reply derived only from tool data."""
    if not tool_results:
        return None

    last = tool_results[-1]
    result = last.get("result")
    tool = last.get("tool", "")

    if not isinstance(result, dict):
        return None

    if "error" in result:
        return f"**Error:** {result['error']}"

    if result.get("found") is False or result.get("count") == 0:
        return result.get("message") or "No matching records found."

    if tool == "search_customers" and result.get("customers"):
        lines = [result.get("message", "Results:"), "", "| Name | ID |", "| --- | --- |"]
        for c in result["customers"]:
            lines.append(f"| {c.get('name', '')} | `{c.get('id', '')}` |")
        return "\n".join(lines)

    if tool == "find_inactive_high_value_customers" and result.get("customers"):
        lines = [
            result.get("message", "Results:"),
            "",
            "| Customer | Previous-month spend (DT) | ID |",
            "| --- | ---: | --- |",
        ]
        for c in result["customers"]:
            lines.append(
                f"| {c.get('name', '')} | {c.get('previous_month_spend', '')} | `{c.get('customer_id', '')}` |"
            )
        return "\n".join(lines)

    if tool == "list_email_drafts" and result.get("drafts"):
        lines = [
            result.get("message", "Results:"),
            "",
            "| Status | Customer | Subject | Draft ID |",
            "| --- | --- | --- | --- |",
        ]
        for d in result["drafts"]:
            lines.append(
                f"| {d.get('status', '')} | {d.get('customer_name', '')} | {d.get('subject', '')} | `{d.get('draft_id', '')}` |"
            )
        return "\n".join(lines)

    if tool == "create_follow_up_drafts" and result.get("drafts"):
        lines = [result.get("message", "Drafts created:"), ""]
        for d in result["drafts"]:
            lines.append(
                f"- **{d.get('customer_name')}** — {d.get('subject')} "
                f"(status: `{d.get('status')}`, id: `{d.get('draft_id')}`)"
            )
        return "\n".join(lines)

    if tool == "get_sales_summary":
        return (
            f"**Sales summary**\n\n"
            f"- Total: **{result.get('total_amount')}** DT\n"
            f"- Orders: **{result.get('order_count')}**\n"
            f"- Period: `{result.get('period_start')}` → `{result.get('period_end')}`"
        )

    if tool == "get_customer_summary" and result.get("found"):
        lines = [
            f"**{result.get('name')}**",
            "",
            f"- Total spent: **{result.get('total_spent')}** DT",
            f"- Orders: **{result.get('order_count')}**",
        ]
        return "\n".join(lines)

    return None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deps = AgentDeps(session=db, user=current_user, clock=Clock())
    start = time.perf_counter()
    success = True
    error_message = None
    model_reply = ""

    try:
        result = await agent.run(body.message, deps=deps)
        if hasattr(result, "output") and result.output is not None:
            model_reply = str(result.output)
        elif hasattr(result, "data") and result.data is not None:
            model_reply = str(result.data)
        else:
            model_reply = str(result)
    except Exception as e:
        success = False
        error_message = f"{type(e).__name__}: {e}"
        logger.exception("Agent run failed: %s", error_message)
        model_reply = ""

    safe = _reply_from_tools(deps.tool_results)
    if safe is not None:
        reply = safe
    elif model_reply:
        reply = model_reply
    else:
        reply = "Sorry, I could not complete the request. Please try again."

    latency_ms = int((time.perf_counter() - start) * 1000)

    call = LlmCall(
        id=uuid4(),
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        latency_ms=latency_ms,
        success=success,
        error_message=error_message,
    )
    db.add(call)
    try:
        await db.commit()
    except Exception:
        await db.rollback()

    return ChatResponse(reply=reply, tool_results=deps.tool_results)
