"""
Simulated email provider.
Results are stored in the database; nothing is actually sent.
"""
import asyncio


class EmailProviderError(Exception):
    pass


async def send_email(
    to: str,
    subject: str,
    body: str,
    force_fail: bool = False,
) -> str:
    # Simulate network latency
    await asyncio.sleep(0.05)
    if force_fail:
        raise EmailProviderError("Simulated provider failure")
    return f"OK: delivered to {to} subject={subject[:40]}"
