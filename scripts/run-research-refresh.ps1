# One local refresh of the registered live sources.
# Does not install a Windows scheduled task or change production.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $env:RESEARCH_DATABASE_URL) {
  $env:RESEARCH_DATABASE_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres"
}

Set-Location (Join-Path $root "workers\research")
uv run aqil-research refresh @args
