# G0 local verification (run from repo root after Docker Desktop is healthy).
# Requires: Node 24, Docker Desktop + WSL2, ~15+ GiB free on C:

$ErrorActionPreference = "Stop"
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;C:\nvm4w\nodejs;" + $env:Path

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Preflight ===" -ForegroundColor Cyan
$freeGiB = [math]::Round((Get-PSDrive C).Free / 1GB, 2)
Write-Host "C: free space: $freeGiB GiB"
if ((Get-PSDrive C).Free -lt 8GB) {
  throw "Need at least 8 GiB free on C: before Supabase/Docker will work reliably."
}

docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Docker engine not ready. Open Docker Desktop and wait until running."
}

Write-Host "`n=== Database (migrations + pgTAP) ===" -ForegroundColor Cyan
# run-db-tests.ps1 starts Supabase with storage/imgproxy excluded (G0 db-only).
npm run test:db

Write-Host "`n=== Regenerate DB types ===" -ForegroundColor Cyan
npm run db:types
git diff --exit-code apps/web/src/types/database.generated.ts
if ($LASTEXITCODE -ne 0) {
  Write-Host "database.generated.ts differs from local schema — review diff and commit if correct." -ForegroundColor Yellow
}

Write-Host "`n=== Web ===" -ForegroundColor Cyan
npm run check:tokens
npm run typecheck
npm run lint
npm run build
Push-Location apps/web
npx playwright install chromium
Pop-Location
$env:CI = "true"
npm run test:e2e

Write-Host "`n=== Research worker ===" -ForegroundColor Cyan
npm run test:research

Write-Host "`n=== apps/web lockfile (CI parity) ===" -ForegroundColor Cyan
Push-Location apps/web
npm ci
Pop-Location

Write-Host "`nG0 local verification finished." -ForegroundColor Green
