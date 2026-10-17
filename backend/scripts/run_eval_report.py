#!/usr/bin/env python3
"""Run B7 eval suite and write tests/golden/EVAL_REPORT.md"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tests" / "golden" / "EVAL_REPORT.md"


def main():
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_eval_suite.py",
        "tests/test_main_query.py",
        "tests/test_api_auth.py",
        "tests/test_drafts.py",
        "-v", "--tb=line",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = proc.stdout + "\n" + proc.stderr
    passed = proc.returncode == 0

    lines = [
        "# Evaluation report (B7)",
        "",
        f"- Generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Result: **{'PASS' if passed else 'FAIL'}** (exit code {proc.returncode})",
        "",
        "## Scope",
        "",
        "- Golden main-query IDs",
        "- API auth (401 / 404 cross-workspace)",
        "- Viewer read access",
        "- Search does not return notes/email",
        "- Draft lifecycle + idempotent send",
        "- Agent main query + empty-search anti-hallucination (if GROQ_API_KEY set)",
        "",
        "## Pytest output",
        "",
        "```",
        out.strip()[-12000:],  # tail if huge
        "```",
        "",
    ]
    REPORT.write_text("\n".join(lines))
    print(out)
    print(f"\nReport written to {REPORT}")
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
