param(
  [ValidateSet("Full", "TestOnly", "ResetOnly", "GuardOnly")]
  [string]$Mode = "Full",
  [string]$DatabaseUrl = ""
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

. "$PSScriptRoot\pgtap-guard.ps1"
if ($Mode -eq "GuardOnly") {
  Assert-PgtapProbesRejected
  Assert-PgtapUrl $DatabaseUrl
  Write-Host "pgTAP target accepted."
  exit 0
}

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

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
  $DatabaseUrl = $env:AQIL_PGTAP_DATABASE_URL
}
Assert-PgtapProbesRejected
Assert-PgtapUrl $DatabaseUrl
$env:AQIL_PGTAP_DATABASE_URL = $DatabaseUrl

if ($Mode -eq "Full" -or $Mode -eq "ResetOnly" -or $Mode -eq "TestOnly") {
  Write-Host "Starting local Supabase stack ..."
  Invoke-Supabase start -x storage-api,imgproxy
}

if ($Mode -eq "Full" -or $Mode -eq "ResetOnly") {
  Write-Host "Preparing disposable pgTAP database aqil_pgtap_test ..."
  & "$PSScriptRoot\prepare-pgtap-test-db.ps1"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Get-DisposablePgtapUrl {
  $previousErrorAction = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $status = & npx --yes supabase status -o env 2>&1 | Out-String
  $ErrorActionPreference = $previousErrorAction
  if ($status -notmatch 'DB_URL="([^"]+)"') {
    throw "Refusing database tests: local Supabase status did not provide a database URL."
  }
  $localUrl = $Matches[1]
  if ($localUrl -notmatch '127\.0\.0\.1:55432/postgres$') {
    throw "Refusing database tests: local Supabase is not the loopback database on port 55432."
  }
  $disposable = $localUrl -replace '/postgres$','/aqil_pgtap_test'
  Assert-PgtapUrl $disposable
  return $disposable
}

if ($Mode -eq "Full" -or $Mode -eq "TestOnly") {
  $target = Get-DisposablePgtapUrl
  $marker = docker exec supabase_db_ojvswermsbbaltjohqph psql -U postgres -d aqil_pgtap_test -tA -c "select marker from research.pgtap_isolation_marker;"
  if ($marker.Trim() -ne "disposable-pgtap-test") {
    throw "Refusing pgTAP: disposable database identity was not verified."
  }
  Write-Host "Running pgTAP on aqil_pgtap_test ..."
  Invoke-Supabase test db --db-url $target
}
