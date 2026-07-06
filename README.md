# Claude Review Co-worker

[![Claude Review On Push](https://github.com/wkmDatalab/claude-pr-hello-world/actions/workflows/claude-review.yml/badge.svg)](https://github.com/wkmDatalab/claude-pr-hello-world/actions/workflows/claude-review.yml)

An AI teammate that reviews your code on every push and hands you a written
report plus a ready-to-apply patch — like a colleague who reads your diff,
writes up what they think, and leaves the fix on your desk for you to check.

The whole thing is **two files you drop into any repo**. This README explains
exactly how they work so you can change them with confidence.

---

## The one idea

> **On every push, GitHub Actions runs a script. The script hands Claude the
> git diff, and Claude writes back review artifacts — a report, a suggested
> patch, and a trace. A human downloads them, reads the report, and applies the
> patch by hand.**

Nothing gets committed automatically. Nothing gets posted as a PR comment. The
co-worker produces evidence; **you** stay the decision-maker. If you remember
only that, you understand the project.

---

## The two files

```
claude_review.py                     THE SCRIPT — reads the diff, asks Claude, writes the artifacts
.github/workflows/claude-review.yml  THE TRIGGER — runs the script on every push, uploads the artifacts
```

**`claude_review.py`** reads the pushed diff (the commit range
`BEFORE_SHA..AFTER_SHA`), asks Claude to review it, and writes three files:

- `reports/AGENT_REVIEW.md` — the review: a verdict, what changed, the problem
  (if any), a proposed fix, and instructions for you.
- `reports/SUGGESTED_FIX.patch` — a unified diff, extracted from the fenced
  ` ```diff ` block in Claude's report. Empty if no fix was proposed.
- `traceability/run.json` — a trace of the run: branch, run id, the SHAs, how
  big the diff was, which files changed, whether a patch was generated.

It does **not** post PR comments, use the GitHub CLI, use MCP, or modify any of
your source files. It only writes those three artifact files.

**`.github/workflows/claude-review.yml`** runs on push to `main` and
`feature/**` branches (and can be triggered manually via `workflow_dispatch`).
It checks out the repo, installs the SDK, runs the script, writes the report
into the Actions run **Summary**, and uploads all the artifacts.

(`src/hello_world.py` is just an example file with a deliberate bug, so you have
something for the reviewer to catch.)

---

## What happens on every push

```
1. You push commits to main or a feature/** branch
          │
          ▼
2. GitHub sees the "push" event  ──►  starts the workflow
          │                            (.github/workflows/claude-review.yml)
          ▼
3. A fresh Ubuntu machine: checkout code (full history), install Python + the SDK
          │
          ▼
4. It runs  python claude_review.py  with these values in the environment:
     • ANTHROPIC_API_KEY  → so Claude will answer (from repo secrets)
     • BEFORE_SHA         → the commit before the push  (github.event.before)
     • AFTER_SHA          → the commit after the push   (github.sha)
     • GITHUB_REF_NAME    → the branch name
     • GITHUB_RUN_ID      → this run's id (used to name the artifact)
          │
          ▼
5. The script computes the diff for BEFORE_SHA..AFTER_SHA          ── get_diff()
   and builds a prompt around it                                   ── build_prompt()
          │
          ▼
6. It sends the diff to Claude and collects the review             ── run_claude_review()
          │
          ▼
7. It extracts the first fenced ```diff block into a patch         ── extract_first_diff_block()
   and writes the three artifact files                             ── reports/ + traceability/
          │
          ▼
8. The workflow writes AGENT_REVIEW.md into the run Summary
   and uploads reports/** and traceability/** as an artifact
   named  claude-review-<run_id>
          │
          ▼
   You open the run, read the Summary, download the artifact,
   read the report, and apply the patch yourself if you agree.
```

That is the entire loop. Nothing hidden, nothing automatic past step 8.

---

## Where to see the results

On GitHub:

1. Go to the **Actions** tab.
2. Open the **Claude Review On Push** workflow.
3. Click the **latest run**.
4. Read the review inline in the **Summary** (Claude's report is written there
   via `GITHUB_STEP_SUMMARY`).
5. Scroll to **Artifacts** and download **`claude-review-<run_id>`**. Unzip it
   to get `reports/AGENT_REVIEW.md`, `reports/SUGGESTED_FIX.patch`, and
   `traceability/run.json`.

---

## How to apply the suggested patch

Once you've downloaded and unzipped the artifact (so `SUGGESTED_FIX.patch` sits
under `reports/` in your repo), review it, then apply it. You're on Windows, so
these are PowerShell-friendly — but `git apply` itself is cross-platform:

```powershell
# 1. Read the patch first — never apply blind
Get-Content reports/SUGGESTED_FIX.patch

# 2. Dry-run: does it apply cleanly?
git apply --check reports/SUGGESTED_FIX.patch

# 3. Apply it to your working tree
git apply reports/SUGGESTED_FIX.patch

# 4. Run your tests / the code to confirm the fix
python -m pytest        # or however you test this project

# 5. If you're happy, commit it
git add -A
git commit -m "Apply Claude's suggested fix"
```

If `git apply --check` complains, the diff may be stale or based on slightly
different context — read the report, fix by hand, and move on. The patch is a
suggestion, not a command.

---

## Run it on your own machine

You can run the script locally to experiment before pushing anything. With no
`BEFORE_SHA`/`AFTER_SHA` set, `get_diff()` falls back gracefully: it first looks
at your **uncommitted changes** (`git diff HEAD`), and if there are none it
reviews the **latest commit** (`git diff HEAD~1..HEAD`).

```powershell
pip install claude-agent-sdk python-dotenv
$env:ANTHROPIC_API_KEY = "sk-ant-..."     # or put it in a .env file
python claude_review.py                     # prints the review, writes the 3 artifact files
```

This is the fastest way to experiment with `ROLE` before pushing anything.

---

## Put it in CI

1. In your GitHub repo: **Settings → Secrets and variables → Actions → New
   repository secret**, named `ANTHROPIC_API_KEY`.
2. Push to `main` or a `feature/**` branch. The **Claude Review On Push**
   workflow runs and produces the artifacts.

The workflow only needs `contents: read` — it never writes to your repo.

---

## Monitoring the reviews

- **Status badge** — the badge at the top of this README shows whether the
  latest **Claude Review On Push** run passed or failed. It links straight to
  the Actions history.
- **Per-run view** — each run's **Summary** shows the verdict and the proposed
  patch inline; the full report + patch + trace are in the downloadable
  **`claude-review-<run_id>`** artifact at the bottom of the run page.
- **Email (optional)** — the workflow can email the report, patch, and trace on
  every run; the subject carries the run status, so it doubles as a failure
  alert. It's skipped automatically unless you add these repo secrets
  (**Settings → Secrets and variables → Actions**):

  | Secret | Example |
  | --- | --- |
  | `MAIL_SERVER` | `smtp.gmail.com` |
  | `MAIL_PORT` | `465` |
  | `MAIL_USERNAME` | `you@gmail.com` |
  | `MAIL_PASSWORD` | a mail **app password** (never your login password) |
  | `MAIL_TO` | where to send it |

  Email uses the third-party `dawidd6/action-send-mail` action, pinned to a
  major version; for stricter supply-chain safety, pin it to a commit SHA.
  GitHub also emails the run's author on failure by default, independent of
  this step.

---

## The one thing *you* change

You almost never touch the plumbing. You adapt the co-worker by editing a single
constant at the top of `claude_review.py`:

| Constant | Meaning | Example change |
| --- | --- | --- |
| `ROLE` | **Who** Claude is and how it reviews | Make it a security reviewer, a style checker, a docs checker… |

`ROLE` also defines the exact report structure (Verdict, What changed, Problem,
Proposed fix, Human instructions) and the rule that any fix must arrive as a
single fenced ` ```diff ` block — which is what `extract_first_diff_block()`
pulls out into `SUGGESTED_FIX.patch`. Change `ROLE` and you've hired a different
specialist; keep the ` ```diff ` convention and the patch extraction keeps
working.

---

## What comes next — but not yet

The obvious next step is to have the co-worker **auto-commit the suggested patch
to a branch** so you can review it as a normal diff instead of applying it by
hand. That is deliberately **not** done yet. Baby steps: for now the script only
generates evidence and lets the human decide — the workflow even exits `0` on
purpose so a review never blocks your push. Trust the loop first, then automate
more.