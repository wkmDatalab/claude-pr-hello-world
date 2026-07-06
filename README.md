# Claude Review Co-worker

A bare-bones example: drop in **one script + one workflow**, and every pull
request gets a Claude code review posted as a comment.

```
claude_review.py                     the agent — this is the file you copy into other repos
.github/workflows/claude-review.yml  runs it on every PR and posts the comment
src/hello_world.py                   the example file being reviewed (has a bug on purpose)
```

## See it work on GitHub

1. Add a repo secret `ANTHROPIC_API_KEY` (Settings → Secrets → Actions).
2. Push a branch and open a pull request.
3. The `Claude Review` workflow runs and posts a review comment. Each new push
   to the PR **updates that same comment** in place.

`src/hello_world.py` ships with two defects (`"H world"` and `printf`), so the
review comes back **FIX NEEDED** with a suggested diff.

## Run it locally

```bash
pip install claude-agent-sdk python-dotenv
export ANTHROPIC_API_KEY=sk-ant-...        # or put it in a .env file
python claude_review.py                     # writes reports/AGENT_REVIEW.md
```

(No PR context locally, so it just saves the report instead of commenting.)

## Make it yours

Open `claude_review.py` and edit the two constants near the top:

- `REVIEW_TARGETS` — what the agent looks at.
- `ROLE` — who the agent is and how it should respond.

That's the whole extension point. A comment in the file shows the next step:
review only the **PR diff** instead of whole files, for cheaper, more precise
feedback.
