# Refresh PATH so winget-installed uv is available in fresh shells.
$ErrorActionPreference = "Stop"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
  [System.Environment]::GetEnvironmentVariable("Path", "User")

$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "workers\research")

uv run pytest
uv run ruff check .
uv run ruff format --check .
