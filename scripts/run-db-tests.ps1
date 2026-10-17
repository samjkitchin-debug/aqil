param(
  [ValidateSet("Full", "TestOnly", "ResetOnly")]
  [string]$Mode = "Full"
)

$ErrorActionPreference = "Stop"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
  [System.Environment]::GetEnvironmentVariable("Path", "User")

$dockerBin = "C:\Program Files\Docker\Docker\resources\bin"
if (Test-Path $dockerBin) {
  $env:Path = "$dockerBin;$env:Path"
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "Docker is required for local Supabase (`supabase start`). Install Docker Desktop and ensure docker is on PATH."
}

$minFreeBytes = 8GB
$freeBytes = (Get-PSDrive -Name C).Free
if ($freeBytes -lt $minFreeBytes) {
  $freeGiB = [math]::Round($freeBytes / 1GB, 2)
  Write-Error @"
C: drive has only $freeGiB GiB free. Supabase local images need several GiB; Docker may hang or report read-only filesystem errors when disk is full.
Free space (Docker Desktop > Settings > Resources, Windows Disk Cleanup, or remove unused images after the engine is healthy), restart Docker Desktop, then retry.
"@
}

$dockerDeadline = (Get-Date).AddMinutes(2)
$dockerReady = $false
while ((Get-Date) -lt $dockerDeadline) {
  docker info *> $null
  if ($LASTEXITCODE -eq 0) {
    $dockerReady = $true
    break
  }
  Start-Sleep -Seconds 3
}
if (-not $dockerReady) {
  Write-Error "Docker engine did not respond within 2 minutes. Open Docker Desktop, wait until it is running, then retry."
}

function Invoke-Supabase {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs)
  if (Get-Command supabase -ErrorAction SilentlyContinue) {
    & supabase @CliArgs
  } else {
    & npx --yes supabase @CliArgs
  }
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}

function Assert-LocalSupabaseDatabase {
  # pgTAP helpers (supabase/tests/database/) are not migrations. Never run tests against hosted.
  $previousErrorAction = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $status = & npx --yes supabase status -o env 2>&1 | Out-String
  $ErrorActionPreference = $previousErrorAction
  if ($status -notmatch '127\.0\.0\.1:54322') {
    Write-Error "Refusing database tests: expected local Supabase at 127.0.0.1:54322. Use npm run test:db or start local stack first. Do not run pgTAP against hosted (`supabase test db --linked`)."
  }
}

if ($Mode -eq "Full" -or $Mode -eq "ResetOnly") {
  Write-Host "Starting local Supabase stack (required before db reset) ..."
  Invoke-Supabase start -x storage-api,imgproxy
}

if ($Mode -eq "Full" -or $Mode -eq "ResetOnly") {
  Write-Host "Resetting database and replaying migrations ..."
  Invoke-Supabase db reset --no-seed
  Write-Host "Provisioning local research_worker login (dev/CI only) ..."
  Invoke-Supabase db query -f scripts/provision-research-worker-local.sql
}

if ($Mode -eq "Full" -or $Mode -eq "TestOnly") {
  Write-Host "Running pgTAP database tests ..."
  Assert-LocalSupabaseDatabase
  Invoke-Supabase test db
}
