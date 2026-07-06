#!/usr/bin/env bash
set -euo pipefail

# Run from repo root after unzipping the project.
# This creates a local Git demo with a clean main branch and one feature branch.

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Paste your real ANTHROPIC_API_KEY into .env before running Claude."
fi

if [ ! -d .git ]; then
  git init
fi

git add .
git commit -m "Initial broken hello-world demo" || true

git branch -M main

git checkout -B feature/broken-hello-world

echo "Demo branch ready: feature/broken-hello-world"
echo "Next: run python scripts/agent_review.py or push this repo to GitHub."
