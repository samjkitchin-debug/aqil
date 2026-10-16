# Sync JSON Schemas from docs/schemas to packages/contracts/schemas
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $root "docs\schemas"
$dest = Join-Path $root "packages\contracts\schemas"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item (Join-Path $source "*.json") $dest -Force
Write-Host "Synced contracts to $dest"
