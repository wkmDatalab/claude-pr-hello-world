"""Claude review co-worker — push-based artifact reviewer.

This script is deliberately simple:

1. Read the git diff from the pushed commit range.
2. Ask Claude to review the diff.
3. Ask Claude to propose a smallest-fix patch if needed.
4. Save:
   - reports/AGENT_REVIEW.md
   - reports/SUGGESTED_FIX.patch
   - traceability/run.json

No PR comments.
No GitHub CLI.
No MCP.
No automatic file modification.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
TRACE_DIR = ROOT / "traceability"

REPORT_FILE = REPORTS_DIR / "AGENT_REVIEW.md"
PATCH_FILE = REPORTS_DIR / "SUGGESTED_FIX.patch"
TRACE_FILE = TRACE_DIR / "run.json"

ROLE = """\
You are a careful code-review co-worker for a Python project.

You are reviewing a unified git diff from a push.

Your job:
1. Explain what changed.
2. Decide whether the change is correct.
3. If the code is broken, propose the smallest safe fix.
4. If you propose a fix, include one fenced ```diff block containing a valid unified diff.
5. Do not modify files yourself.
6. Do not invent unrelated improvements.

Use this exact structure:

# Verdict
FIX NEEDED / NO CHANGE NEEDED / NEEDS HUMAN JUDGMENT

# What changed
Brief explanation.

# Problem
Explain the issue, if any.

# Proposed fix
Include a valid unified diff in a fenced ```diff block if a fix is needed.

# Human instructions
Tell the human how to review/apply the patch.
"""


def run_command(args: list[str], allow_failure: bool = True) -> tuple[int, str, str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(
            f"Command failed: {' '.join(args)}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )

    return result.returncode, result.stdout, result.stderr


def git(args: list[str]) -> str:
    code, stdout, stderr = run_command(["git", *args])
    if code != 0:
        return ""
    return stdout


def get_diff() -> str:
    """Get the pushed diff.

    In GitHub Actions on push:
      BEFORE_SHA = commit before the push
      AFTER_SHA  = commit after the push

    Locally:
      first inspect uncommitted changes
      otherwise inspect the latest commit
    """

    before = os.getenv("BEFORE_SHA", "").strip()
    after = os.getenv("AFTER_SHA", "").strip()

    # GitHub gives all-zero BEFORE_SHA for some first-push/new-branch cases.
    all_zero = "0000000000000000000000000000000000000000"

    if before and after and before != all_zero:
        diff = git(["diff", f"{before}..{after}"])
        if diff.strip():
            return diff

    if after:
        diff = git(["show", "--format=", "--no-ext-diff", after])
        if diff.strip():
            return diff

    working = git(["diff", "HEAD"])
    if working.strip():
        return working

    latest_commit = git(["diff", "HEAD~1..HEAD"])
    return latest_commit


def build_prompt(diff: str) -> str:
    return f"{ROLE}\n\n## Unified git diff\n\n```diff\n{diff}\n```"


def extract_first_diff_block(markdown: str) -> str:
    """Extract the first fenced diff block from Claude's report."""
    match = re.search(r"```diff\s*(.*?)```", markdown, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return ""

    patch = match.group(1).strip()

    # Remove accidental leading/trailing prose.
    if not patch.startswith("diff --git") and not patch.startswith("--- "):
        return ""

    return patch + "\n"


async def run_claude_review(diff: str) -> str:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY is missing. Add it as a GitHub Actions secret "
            "or put it in a local .env file."
        )

    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        TextBlock,
    )

    options = ClaudeAgentOptions(
        cwd=ROOT,
        model="haiku",  # cost-effective; alias resolves to current Haiku (avoids pinning a retired ID)
        max_turns=6,
        allowed_tools=["Read", "Grep", "Glob"],
    )

    chunks: list[str] = []

    async with ClaudeSDKClient(options=options) as client:
        await client.query(build_prompt(diff))

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
                        print(block.text, end="")

    return "".join(chunks).strip()


def write_trace(diff: str, report: str, patch: str) -> None:
    TRACE_DIR.mkdir(exist_ok=True)

    trace = {
        "run_started_at_utc": datetime.now(timezone.utc).isoformat(),
        "branch": os.getenv("GITHUB_REF_NAME") or git(["branch", "--show-current"]).strip(),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "before_sha": os.getenv("BEFORE_SHA"),
        "after_sha": os.getenv("AFTER_SHA"),
        "diff_characters": len(diff),
        "report_file": str(REPORT_FILE),
        "patch_file": str(PATCH_FILE),
        "patch_generated": bool(patch.strip()),
        "agent": "claude-agent-sdk",
        "mode": "push-artifact-review",
        "tools_allowed": ["Read", "Grep", "Glob"],
        "files_changed": git(["diff", "--name-only", "HEAD~1..HEAD"]).splitlines(),
    }

    TRACE_FILE.write_text(json.dumps(trace, indent=2), encoding="utf-8")


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        pass

    REPORTS_DIR.mkdir(exist_ok=True)
    TRACE_DIR.mkdir(exist_ok=True)

    diff = get_diff()

    if not diff.strip():
        report = """# Verdict
NO CHANGE NEEDED

# What changed
No git diff was found.

# Problem
Nothing to review.

# Proposed fix
No patch generated.

# Human instructions
No action required.
"""
        patch = ""
    else:
        report = asyncio.run(run_claude_review(diff))
        patch = extract_first_diff_block(report)

    REPORT_FILE.write_text(report + "\n", encoding="utf-8")
    PATCH_FILE.write_text(patch, encoding="utf-8")
    write_trace(diff, report, patch)

    print(f"\n\nWrote {REPORT_FILE}")
    print(f"Wrote {PATCH_FILE}")
    print(f"Wrote {TRACE_FILE}")

    # Do not fail the workflow yet.
    # Baby step: generate evidence, let the human decide.
    sys.exit(0)


if __name__ == "__main__":
    main()