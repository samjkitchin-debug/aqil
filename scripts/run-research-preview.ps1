# Local founder preview: Supabase + collect-and-run + web insight export.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-db-tests.ps1 -Mode Full

$env:RESEARCH_DATABASE_URL = "postgresql://research_worker:research_worker@127.0.0.1:55432/postgres"
$runId = "founder-preview-" + (Get-Date -Format "yyyyMMdd-HHmm")

Set-Location (Join-Path $root "workers\research")
uv run aqil-research collect-and-run `
  --source bls --method sahm `
  --fixture tests/fixtures/bls/api_lns14000000_success.json `
  --start-year 2022 --end-year 2025 `
  --run-id $runId `
  --allow-evaluation-fallback `
  --export-insight

Write-Host "Insight written for Next.js (.local). Start web: npm run dev"
Write-Host "run_id=$runId"
