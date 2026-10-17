"""
B1 Tool-calling spike
Tests 4 free models on 20 prompts.
Run:  uv run python scripts/tool_spike.py
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# Models to test
# ---------------------------------------------------------------------------
MODELS = [
    {"provider": "groq", "model": "qwen/qwen3.8-27b", "base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    {"provider": "groq", "model": "openai/gpt-oss-20b", "base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    {"provider": "openrouter", "model": "nvidia/nemotron-3-super-120b-a12b:free", "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},
    {"provider": "openrouter", "model": "google/gemma-4-31b-it:free", "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},
]

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI format)
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_customers",
            "description": "Search customers by name or email. Returns limited public fields only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text"},
                    "limit": {"type": "integer", "description": "Max results", "default": 10}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_summary",
            "description": "Get totals and last 5 orders for one customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer UUID"}
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": "Get sales totals for a period (previous_month, current_month, last_30_days).",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["previous_month", "current_month", "last_30_days"]}
                },
                "required": ["period"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_inactive_high_value_customers",
            "description": "Find active customers who spent more than minimum_spend in previous month but have no paid/completed order in current month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minimum_spend": {"type": "number", "description": "Minimum spend in DT"}
                },
                "required": ["minimum_spend"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_follow_up_drafts",
            "description": "Create up to 10 email drafts. Recipient is taken from the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "maxItems": 10,
                        "items": {
                            "type": "object",
                            "properties": {
                                "customer_id": {"type": "string"},
                                "subject": {"type": "string"},
                                "body": {"type": "string"}
                            },
                            "required": ["customer_id", "subject", "body"]
                        }
                    }
                },
                "required": ["items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_email_drafts",
            "description": "List email drafts filtered by status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending_review", "approved", "sent", "failed"]}
                },
                "required": ["status"]
            }
        }
    },
]

# ---------------------------------------------------------------------------
# 20 evaluation prompts
# ---------------------------------------------------------------------------
PROMPTS = [
    # search_customers (1-4)
    {"id": 1, "expected_tool": "search_customers", "text": "Find customers named Ahmed"},
    {"id": 2, "expected_tool": "search_customers", "text": "Search for customer with email containing demo"},
    {"id": 3, "expected_tool": "search_customers", "text": "List customers matching 'Injection'"},
    {"id": 4, "expected_tool": "search_customers", "text": "Who are the customers with '500' in their name?"},

    # get_customer_summary (5-7)
    {"id": 5, "expected_tool": "get_customer_summary", "text": "Give me a summary of customer e0000000-0000-0000-0000-000000000002"},
    {"id": 6, "expected_tool": "get_customer_summary", "text": "Show totals and recent orders for the Over 500.001 DT customer"},
    {"id": 7, "expected_tool": "get_customer_summary", "text": "What is the order history of customer Exact 500 DT?"},

    # get_sales_summary (8-10)
    {"id": 8, "expected_tool": "get_sales_summary", "text": "What were our total sales last month?"},
    {"id": 9, "expected_tool": "get_sales_summary", "text": "Show me the sales summary for the previous month"},
    {"id": 10, "expected_tool": "get_sales_summary", "text": "How much did we sell in the current month?"},

    # find_inactive_high_value_customers (11-14)  ← main business query
    {"id": 11, "expected_tool": "find_inactive_high_value_customers", "text": "Which high-value customers spent more than 500 DT last month but have not ordered this month?"},
    {"id": 12, "expected_tool": "find_inactive_high_value_customers", "text": "Find inactive high-value customers with minimum spend 500"},
    {"id": 13, "expected_tool": "find_inactive_high_value_customers", "text": "List customers who were active last month above 500 DT and are inactive now"},
    {"id": 14, "expected_tool": "find_inactive_high_value_customers", "text": "Who should we follow up with? High spenders from previous month with no current orders"},

    # create_follow_up_drafts (15-17)
    {"id": 15, "expected_tool": "create_follow_up_drafts", "text": "Create a follow-up email draft for customer e0000000-0000-0000-0000-000000000002 with subject 'We miss you' and a short polite body"},
    {"id": 16, "expected_tool": "create_follow_up_drafts", "text": "Draft follow-up emails for the inactive high-value customers"},
    {"id": 17, "expected_tool": "create_follow_up_drafts", "text": "Prepare two email drafts: one for Over 500 and one for Three 200 customers"},

    # list_email_drafts (18-20)
    {"id": 18, "expected_tool": "list_email_drafts", "text": "Show me all pending review email drafts"},
    {"id": 19, "expected_tool": "list_email_drafts", "text": "List the drafts that are still waiting for approval"},
    {"id": 20, "expected_tool": "list_email_drafts", "text": "What email drafts do we have in pending_review status?"},
]


@dataclass
class Result:
    model: str
    provider: str
    prompt_id: int
    expected_tool: str
    actual_tools: list[str]
    success: bool
    latency_ms: float
    error: str | None = None
    raw_tool_calls: Any = None


async def call_model(client: AsyncOpenAI, model: str, prompt: str) -> tuple[list[str], float, Any, str | None]:
    start = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a business assistant. You MUST use the provided tools to answer. Never invent data."},
                {"role": "user", "content": prompt},
            ],
            tools=TOOLS,
            tool_choice="auto",
            temperature=0,
            max_tokens=512,
        )
        latency = (time.perf_counter() - start) * 1000
        message = response.choices[0].message
        tool_calls = []
        raw = None
        if message.tool_calls:
            raw = [tc.model_dump() for tc in message.tool_calls]
            tool_calls = [tc.function.name for tc in message.tool_calls]
        return tool_calls, latency, raw, None
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return [], latency, None, str(e)


async def run_spike():
    results: list[Result] = []

    for m in MODELS:
        api_key = os.getenv(m["api_key_env"])
        if not api_key:
            print(f"❌ Missing {m['api_key_env']} – skipping {m['model']}")
            continue

        client = AsyncOpenAI(base_url=m["base_url"], api_key=api_key)
        print(f"\n=== Testing {m['provider']} / {m['model']} ===")

        for p in PROMPTS:
            tools, latency, raw, error = await call_model(client, m["model"], p["text"])
            success = p["expected_tool"] in tools and error is None
            r = Result(
                model=m["model"],
                provider=m["provider"],
                prompt_id=p["id"],
                expected_tool=p["expected_tool"],
                actual_tools=tools,
                success=success,
                latency_ms=round(latency, 1),
                error=error,
                raw_tool_calls=raw,
            )
            results.append(r)
            status = "✅" if success else "❌"
            print(f"  {status} #{p['id']:02d} expected={p['expected_tool']:<35} got={tools}  {latency:.0f}ms")
            if error:
                print(f"       error: {error[:120]}")

            # small pause to respect rate limits
            await asyncio.sleep(1.2)

    # ------------------------------------------------------------------
    # Summary table
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    from collections import defaultdict
    stats = defaultdict(lambda: {"ok": 0, "total": 0, "latencies": []})

    for r in results:
        key = f"{r.provider}/{r.model}"
        stats[key]["total"] += 1
        if r.success:
            stats[key]["ok"] += 1
        stats[key]["latencies"].append(r.latency_ms)

    print(f"{'Model':<55} {'Valid':>8} {'Median ms':>10}")
    print("-" * 80)
    for key, s in stats.items():
        median = sorted(s["latencies"])[len(s["latencies"]) // 2] if s["latencies"] else 0
        print(f"{key:<55} {s['ok']:>3}/{s['total']:<3} {median:>10.0f}")

    # Save detailed results
    out_path = "scripts/spike_results.json"
    with open(out_path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2, default=str)
    print(f"\nDetailed results saved to {out_path}")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(run_spike())
