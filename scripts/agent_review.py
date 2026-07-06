"""Tiny Claude Agent SDK PR-style review.

Kept deliberately small. It:
1. loads ANTHROPIC_API_KEY from .env (if present),
2. reads the three example files under src/,
3. asks Claude to review them and classify each as
   FIX NEEDED / NO CHANGE NEEDED / NEEDS HUMAN JUDGMENT,
4. writes one report to reports/AGENT_REVIEW.md.

Run locally:
    Copy .env.example to .env, paste your ANTHROPIC_API_KEY, then run:
    uv run python scripts/agent_review.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
REPORTS_DIR = ROOT / "reports"
REPORT_FILE = REPORTS_DIR / "AGENT_REVIEW.md"

# The three cases the agent reviews.
REVIEW_FILES = ["hello_world.py", "adder.py", "average.py"]


def load_environment() -> None:
    """Load ANTHROPIC_API_KEY from .env locally; CI env vars still win."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_file, override=False)


def build_prompt() -> str:
    """Combine the review prompt with the source of the three files."""
    prompt = (ROOT / "prompts" / "pr_review_prompt.md").read_text(encoding="utf-8")
    blocks = []
    for name in REVIEW_FILES:
        code = (SRC_DIR / name).read_text(encoding="utf-8")
        blocks.append(f"### src/{name}\n\n```python\n{code}\n```")
    return prompt + "\n\n## Files to review\n\n" + "\n\n".join(blocks)


async def run_review() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Add it to .env locally (copy "
            ".env.example to .env) or set it as a GitHub Actions repository "
            "secret, then re-run."
        )

    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        TextBlock,
    )

    options = ClaudeAgentOptions(
        cwd=ROOT,
        max_turns=8,
        allowed_tools=["Read", "Glob", "Grep", "Write"],
    )

    REPORTS_DIR.mkdir(exist_ok=True)
    assistant_text: list[str] = []

    async with ClaudeSDKClient(options=options) as client:
        await client.query(build_prompt())
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        assistant_text.append(block.text)
                        print(block.text, end="")

    # Safety net: if the agent answered but did not write the report itself,
    # save its final text so the artifact always exists.
    if not REPORT_FILE.exists():
        REPORT_FILE.write_text("".join(assistant_text), encoding="utf-8")


if __name__ == "__main__":
    load_environment()
    asyncio.run(run_review())
