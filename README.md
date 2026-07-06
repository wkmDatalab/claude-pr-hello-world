# Claude Review Co-worker

An AI teammate that reviews your code on every pull request and leaves a comment
— like a colleague who never sleeps.

The whole thing is **two files you drop into any repo**. This README explains
exactly how they work so you can change them with confidence.

---

## The one idea

> **A GitHub event runs a script. The script asks Claude a question and posts
> the answer back as a PR comment.**

Everything below is just plumbing for those two sentences. If you remember only
this, you understand the project.

---

## The two files

```
claude_review.py                     THE SCRIPT — asks Claude, posts the comment
.github/workflows/claude-review.yml  THE TRIGGER — runs the script on every PR
```

(`src/hello_world.py` is just an example file with a deliberate bug, so you have
something for the reviewer to catch.)

---

## What happens on every pull request

```
1. You open or push to a PR
          │
          ▼
2. GitHub sees the "pull_request" event  ──►  starts the workflow
          │                                    (.github/workflows/claude-review.yml)
          ▼
3. A fresh Ubuntu machine: checkout code, install Python + the SDK
          │
          ▼
4. It runs  python claude_review.py  and hands it 3 values:
     • ANTHROPIC_API_KEY  → so Claude will answer
     • GITHUB_TOKEN       → permission to comment (auto-created by GitHub)
     • PR_NUMBER          → which PR to comment on
          │
          ▼
5. The script reads your target file(s) and builds a prompt   ── build_prompt()
          │
          ▼
6. It sends that prompt to Claude and collects the reply      ── run_review()
          │
          ▼
7. It posts the reply to the PR. If a review comment already  ── post_or_update_pr_comment()
   exists it EDITS it; otherwise it CREATES one.
          │
          ▼
   You see the review as a comment. Push again → step 1 repeats,
   and the SAME comment updates in place.
```

That is the entire loop. Nothing hidden.

---

## The two things *you* change

You almost never touch the plumbing. You adapt the co-worker by editing **two
constants at the top of `claude_review.py`:**

| Constant | Meaning | Example change |
| --- | --- | --- |
| `REVIEW_TARGETS` | **What** it reads | Point it at your real source files |
| `ROLE` | **Who** it is and how it answers | Make it a security reviewer, a style checker, a docs checker… |

Change `ROLE`, and you've hired a different specialist. Change `REVIEW_TARGETS`,
and you've pointed it at different work. Everything else keeps working.

---

## Why the comment updates instead of piling up

The script writes a hidden marker (`<!-- claude-review -->`) at the top of its
comment. On each run it looks for that marker: found → edit that comment, not
found → create a new one. So a PR always has exactly **one** living review
comment, no matter how many times you push.

---

## Run it on your own machine

Locally there is no PR, so step 7 simply saves the report to a file instead of
commenting:

```bash
pip install claude-agent-sdk python-dotenv
export ANTHROPIC_API_KEY=sk-ant-...        # or put it in a .env file
python claude_review.py                     # prints the review, saves reports/AGENT_REVIEW.md
```

This is the fastest way to experiment with `ROLE` and `REVIEW_TARGETS` before
pushing anything.

---

## Put it in CI (what makes the PR comments happen)

1. In your GitHub repo: **Settings → Secrets and variables → Actions → New
   repository secret**, named `ANTHROPIC_API_KEY`.
2. Open a pull request. The `Claude Review` workflow runs and comments.

Note: PRs opened **from a fork** get a read-only token, so the comment step is
skipped there. Same-repo branches (the normal team workflow) work fine.

---

## Where to take it next

**Review the diff instead of whole files.** Today the script sends entire files
to Claude. The natural upgrade is to send only what changed in the PR
(`git diff`). This costs fewer tokens and gives more precise, line-level
feedback. Only `build_prompt()` (step 5) needs to change — the rest of the loop
is untouched.

After that: give the agent tools to run the tests, split it into multiple
specialist roles, or have it suggest commits rather than comments.
