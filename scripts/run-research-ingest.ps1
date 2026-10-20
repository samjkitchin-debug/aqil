# Local research ingest: live BLS series (and optional publications hook) into PostgreSQL.
# Does not run Sahm or export web insight — use research:preview for the founder preview path.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $env:RESEARCH_DATABASE_URL) {
  $env:RESEARCH_DATABASE_URL = "postgresql://research_worker:research_worker@127.0.0.1:54322/postgres"
}

Set-Location (Join-Path $root "workers\research")
uv run aqil-research ingest @args
