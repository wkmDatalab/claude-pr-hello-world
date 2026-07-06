# Run from repo root after unzipping the project.
# This creates a local Git demo with a clean main branch and one feature branch.


if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Paste your real ANTHROPIC_API_KEY into .env before running Claude."
}

if (-not (Test-Path ".git")) {
    git init
}

git add .
git commit -m "Initial broken hello-world demo"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Commit may already exist; continuing."
}

git branch -M main
git checkout -B feature/broken-hello-world

Write-Host "Demo branch ready: feature/broken-hello-world"
Write-Host "Next: run python scripts/agent_review.py or push this repo to GitHub."
