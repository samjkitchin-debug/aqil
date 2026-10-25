# Local monthly refresh configuration. Does not register a task unless -Activate is passed.
param([switch]$Activate)
$ErrorActionPreference = "Stop"
$command = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-research-refresh.ps1`""
Write-Output "Manual command: npm run research:refresh"
Write-Output "Proposed monthly task command: $command"
Write-Output "Proposed schedule: once a month, after the BEA and BLS release window."
if (-not $Activate) {
  Write-Output "Not registered. Pass -Activate only when this machine should run an unattended local refresh."
  exit 0
}
schtasks /Create /TN AqilMacroRefresh /SC MONTHLY /D 1 /ST 07:00 /TR $command /F
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "Registered AqilMacroRefresh."