# Claude Agent PR Review Hello World

This is a deliberately tiny training repo for learning agentic PR-review mechanics without Snowflake, MCP, GitHub CLI, or a real hosted PR.

The agent reviews three small files, each a different kind of case, and writes one report that a human can inspect. The point is to see the agent use judgment — not just "find the bug."

## What this teaches

The important mapping is:

```text
Your script          = orchestrator
Claude Agent SDK     = agent runtime
Claude               = reasoning engine
Read/Grep/Write      = tools
reports/             = PR-style output artifact
GitHub Actions       = CI runner + artifact storage
```

## The three cases

The agent reviews three files under `src/` and should treat each differently:

| File | Case | Expected verdict |
| --- | --- | --- |
| `src/hello_world.py` | Clear defect (its test fails) | **FIX NEEDED** — propose the smallest patch |
| `src/adder.py` | Already correct (its test passes) | **NO CHANGE NEEDED** — don't invent a fix |
| `src/average.py` | Ambiguous, no test | **NEEDS HUMAN JUDGMENT** — raise a question |

`src/hello_world.py` has two bugs — it returns `"H world"` instead of `"Hello world"`, and calls `printf(...)` where Python uses `print(...)`. `src/average.py` returns `0.0` for an empty input, which may be intended or may need to raise; that is the human's call, not the agent's.

## Files

```text
.env.example                         Safe template for local secrets; copy to .env
.github/workflows/agent-review.yml    GitHub Actions workflow that uploads the report artifact
prompts/pr_review_prompt.md           The prompt used by the agent
scripts/agent_review.py               Claude Agent SDK orchestration script
scripts/apply_suggested_fix.py        Optional human-applied fix script (case 1)
scripts/setup_demo.ps1                Windows PowerShell local git setup helper
scripts/setup_demo.sh                 Bash local git setup helper
src/hello_world.py                    Case 1: clear defect (failing test)
src/adder.py                          Case 2: already correct (passing test)
src/average.py                        Case 3: ambiguous, no test
tests/test_hello_world.py             Fails until case 1 is fixed
tests/test_adder.py                   Passes (case 2)
reports/                             Generated PR-style report goes here
```

## Local run on Windows with uv

From PowerShell:

```powershell
cd path\to\claude-pr-review-hello
uv sync

# Create a local git repo/branch for the demo.
# This also creates .env from .env.example if .env does not exist yet.
.\scripts\setup_demo.ps1
```

Now open `.env` and paste your real key:

```dotenv
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
```

Then run:

```powershell
# Run tests manually: they should fail at first
uv run python -m pytest -q

# Run the agent review. The script loads ANTHROPIC_API_KEY from .env.
uv run python scripts\agent_review.py
```

Then inspect:

```text
reports/AGENT_REVIEW.md
```

## Local run without uv

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env       # Windows PowerShell: Copy-Item .env.example .env
# Edit .env and paste your real ANTHROPIC_API_KEY.
python scripts/agent_review.py
```

## Secret handling

Local development uses `.env`:

```text
.env.example   safe template committed to Git
.env           your private local secrets file, ignored by Git
```

The script calls `load_dotenv()` at startup. It does **not** overwrite existing environment variables, so GitHub Actions can still use repository secrets normally.

Do not commit `.env`. The `.gitignore` file ignores `.env` and `.env.*`, while explicitly allowing `.env.example`.

## GitHub Actions setup

1. Create a new GitHub repo.
2. Push this project to it.
3. Add a repository secret named `ANTHROPIC_API_KEY` if you want Claude to run in CI. This is the GitHub Actions equivalent of your local `.env` file.
4. Go to the Actions tab.
5. Run `Agent Review Artifacts` manually, or push to `main` / `feature/**`.

The workflow always uploads an artifact named like:

```text
agent-review-<run_id>
```

Inside it you will find:

```text
reports/AGENT_REVIEW.md
reports/pytest-output.txt
```

If `ANTHROPIC_API_KEY` is missing, `agent_review.py` exits with a clear message; the workflow still uploads the pytest output.

## The local PR simulation

Git by itself handles local version control:

```text
branch
commit
diff
merge
```

A real GitHub Pull Request is a GitHub hosting feature, not a raw Git feature. This repo therefore starts with a local PR-style artifact:

```text
reports/AGENT_REVIEW.md
```

That file is the first learning milestone. Later you can add GitHub CLI or API automation to post the report as a real PR comment.

## Human review flow

After the agent generates `reports/AGENT_REVIEW.md`, the human can apply the proposed fix for case 1 manually.

For this demo, you can simulate accepting the proposed fix:

```bash
python scripts/apply_suggested_fix.py
python -m pytest -q
git diff
```

Then commit it yourself:

```bash
git add src/hello_world.py
git commit -m "Fix hello-world output"
```

## Why no GitHub MCP and no GitHub CLI?

This first repo uses only Git and GitHub Actions artifacts.

- Git gives you branch/diff/commit/merge mechanics.
- GitHub Actions gives you repeatable CI execution and downloadable artifacts.
- Claude Agent SDK gives you the agent loop and tool-calling behavior.

GitHub MCP or GitHub CLI can be added later when you want the agent to read/write hosted PR comments directly.

## Expansion path

Phase 1: Review-only local PR proposal.

Phase 2: Allow agent to edit source files on a feature branch.

Phase 3: Add stricter tool hooks and richer traceability.

Phase 4: Add GitHub CLI or API to create/update real PRs.

Phase 5: Add Snowflake/Cortex Code SDK mapping.
