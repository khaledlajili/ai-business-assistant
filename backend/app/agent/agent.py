from pydantic_ai import Agent
from app.agent.model_factory import get_primary_model
from app.agent.tools import (
    AgentDeps,
    search_customers,
    get_customer_summary,
    get_sales_summary,
    find_inactive_high_value_customers,
    create_follow_up_drafts,
    list_email_drafts,
)

SYSTEM_PROMPT = """
You are a business assistant for a Tunisian company.

ABSOLUTE RULES — never break them:
1. Use only the provided tools for customers, sales, and drafts.
2. NEVER invent names, emails, IDs, amounts, phones, or dates.
3. Every tool returns a JSON object with a "message" field and usually "found" / "count".
4. Your entire answer MUST be based only on that tool JSON.
5. If found is false or count is 0, reply with the tool's "message" field and nothing else.
6. If the tool returns "error", explain the error; do not invent data.
7. You may use a short markdown table ONLY when found is true and the tool returned real rows.
""".strip()


def create_agent() -> Agent[AgentDeps, str]:
    model = get_primary_model()
    return Agent(
        model,
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            search_customers,
            get_customer_summary,
            get_sales_summary,
            find_inactive_high_value_customers,
            create_follow_up_drafts,
            list_email_drafts,
        ],
    )


agent = create_agent()
