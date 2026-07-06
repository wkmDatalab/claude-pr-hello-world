"""Claude review co-worker — a drop-in PR reviewer.

Copy this one file plus .github/workflows/claude-review.yml into any repo,
add an ANTHROPIC_API_KEY secret, and every pull request gets a Claude review
posted as a comment that updates in place on each push.

Run locally:   ANTHROPIC_API_KEY=sk-ant-...  python claude_review.py
Run in CI:     the workflow provides ANTHROPIC_API_KEY, GITHUB_TOKEN, and
               the PR number; the review is posted back to the PR.

------------------------------------------------------------------------------
To make this your own, you usually only edit the two constants below:
  REVIEW_TARGETS  — what the agent looks at
  ROLE            — who the agent is and how it should respond
Everything under "machinery" rarely needs to change.
------------------------------------------------------------------------------
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ── The agent's job — EDIT THESE to change the co-worker's role ──────────────
# REVIEW_TARGETS is now an optional whole-file FALLBACK (see build_prompt).
# The primary input is the PR diff, produced by get_pr_diff() below.
REVIEW_TARGETS = ["src/hello_world.py"]

ROLE = """\
You are a careful code-review co-worker for a Python project.

You are reviewing a unified diff — the changes made in a pull request — not
whole files. Focus on the changed lines (those beginning with + or -) and their
surrounding context; you may read the rest of a file for context if needed.

For the change as a whole:
- Give a verdict: FIX NEEDED / NO CHANGE NEEDED / NEEDS HUMAN JUDGMENT.
- Briefly say what you observed, pointing at the specific changed lines.
- If FIX NEEDED, propose the smallest fix as a unified diff.

Do not modify any files. Reply with a single Markdown report, nothing else.
"""
# ─────────────────────────────────────────────────────────────────────────────

# ── machinery ────────────────────────────────────────────────────────────────

COMMENT_MARKER = "<!-- claude-review -->"
REPORT_FILE = ROOT / "reports" / "AGENT_REVIEW.md"
NO_CHANGES_REPORT = (
    "**NO CHANGE NEEDED** — no changes to review (the PR diff is empty)."
)


def _git(args: list[str]) -> str:
    """Run `git <args>` in the repo; return stdout, or "" on any git error."""
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else ""


def get_pr_diff() -> str:
    """Return the PR's changes as a unified-diff string (may be empty).

    In CI the workflow provides BASE_SHA (the PR's base commit), so we diff
    `<base>...HEAD` — the three-dot form compares HEAD against the merge-base,
    i.e. exactly what the PR adds.

    Locally there is no BASE_SHA, so we fall back so a developer can still try
    the script: any uncommitted changes first (`git diff HEAD`), otherwise the
    most recent commit (`git diff HEAD~1...HEAD`).
    """
    base = os.getenv("BASE_SHA")
    if base:
        return _git(["diff", f"{base}...HEAD"])

    working = _git(["diff", "HEAD"])  # staged + unstaged changes vs. HEAD
    if working.strip():
        return working
    return _git(["diff", "HEAD~1...HEAD"])  # the last commit (empty if none)


def build_prompt(diff: str | None = None) -> str:
    """Build the review prompt.

    Primary mode: review the unified ``diff`` of the PR's changes.
    Fallback mode (``diff`` is None): review the whole REVIEW_TARGETS files —
    the original behavior, kept so the script still works without a diff.
    """
    if diff is not None:
        return f"{ROLE}\n\n## Unified diff to review\n\n```diff\n{diff}\n```"

    blocks = []
    for rel in REVIEW_TARGETS:
        code = (ROOT / rel).read_text(encoding="utf-8")
        blocks.append(f"### {rel}\n\n```python\n{code}\n```")
    return f"{ROLE}\n\n## Files to review (whole-file fallback)\n\n" + "\n\n".join(blocks)


async def run_review(diff: str | None = None) -> str:
    """Ask Claude to review the diff (or targets) and return the Markdown report."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Set it locally (e.g. in .env) or as "
            "the repository secret used by the workflow, then re-run."
        )

    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        TextBlock,
    )

    options = ClaudeAgentOptions(
        cwd=ROOT,
        max_turns=6,
        allowed_tools=["Read", "Grep", "Glob"],
    )

    parts: list[str] = []
    async with ClaudeSDKClient(options=options) as client:
        await client.query(build_prompt(diff))
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
                        print(block.text, end="")
    return "".join(parts).strip()


def _github_request(method: str, url: str, token: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "claude-review")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read() or "null")


def post_or_update_pr_comment(report: str) -> None:
    """Upsert a single PR comment. No-op when not running against a PR."""
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")  # "owner/name", set by Actions
    pr = os.getenv("PR_NUMBER")
    if not (token and repo and pr):
        print("\n(No PR context — skipping comment; report saved locally.)")
        return

    body = f"{COMMENT_MARKER}\n{report}\n\n---\n<sub>🤖 Claude review · updates in place on each push.</sub>"
    base = f"https://api.github.com/repos/{repo}"
    try:
        comments = _github_request("GET", f"{base}/issues/{pr}/comments?per_page=100", token)
        existing = next((c for c in comments if COMMENT_MARKER in (c.get("body") or "")), None)
        if existing:
            _github_request("PATCH", f"{base}/issues/comments/{existing['id']}", token, {"body": body})
            print(f"\nUpdated PR comment #{existing['id']}.")
        else:
            _github_request("POST", f"{base}/issues/{pr}/comments", token, {"body": body})
            print("\nCreated PR comment.")
    except urllib.error.HTTPError as err:
        print(f"\nCould not post PR comment ({err.code}): {err.read().decode(errors='replace')}")


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        pass

    diff = get_pr_diff()
    if diff.strip():
        report = asyncio.run(run_review(diff))
    else:
        # No changes to review — skip the Claude call entirely.
        report = NO_CHANGES_REPORT
        print(report)

    REPORT_FILE.parent.mkdir(exist_ok=True)
    REPORT_FILE.write_text(report, encoding="utf-8")
    post_or_update_pr_comment(report)


if __name__ == "__main__":
    main()
