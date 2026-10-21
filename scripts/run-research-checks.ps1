# Refresh PATH so winget-installed uv is available in fresh shells.
$ErrorActionPreference = "Stop"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
  [System.Environment]::GetEnvironmentVariable("Path", "User")

$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "prepare-research-test-db.ps1")
$env:AQIL_RESEARCH_TEST_DATABASE_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/aqil_research_test"
Remove-Item Env:RESEARCH_DATABASE_URL -ErrorAction SilentlyContinue
Set-Location (Join-Path $root "workers\research")

uv run pytest
uv run ruff check .
uv run ruff format --check .
