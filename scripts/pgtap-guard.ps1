# Fail closed before any pgTAP reset. No fallback to the development database.
$ErrorActionPreference = "Stop"

function Assert-PgtapUrl {
  param([string]$Url)
  if ([string]::IsNullOrWhiteSpace($Url)) {
    throw "AQIL_PGTAP_DATABASE_URL is required. There is no fallback to the development database."
  }
  $lower = $Url.ToLowerInvariant()
  foreach ($hostMark in @("supabase.co", "supabase.com", "amazonaws.com", "azure.com", "neon.tech", "vercel.app")) {
    if ($lower.Contains($hostMark)) {
      throw "Hosted databases are prohibited as pgTAP targets."
    }
  }
  if ($lower -notmatch '@(127\.0\.0\.1|localhost)(:|/)') {
    throw "pgTAP target host must be loopback."
  }
  if ($lower -match ':(5432|6543)(/|$)') {
    throw "Ports 5432 and 6543 are prohibited as pgTAP targets."
  }
  if ($lower -match '/postgres([/?]|$)') {
    throw "The development database named postgres is prohibited as a pgTAP target."
  }
  if ($lower -notmatch '/aqil_pgtap_test([/?]|$)') {
    throw "pgTAP target database must be aqil_pgtap_test."
  }
}

function Assert-PgtapProbesRejected {
  $probes = @(
    "",
    "postgresql://postgres@127.0.0.1:55432/postgres",
    "postgresql://postgres@db.ojvswermsbbaltjohqph.supabase.co:5432/aqil_pgtap_test",
    "postgresql://postgres@127.0.0.1:5432/aqil_pgtap_test",
    "postgresql://postgres@127.0.0.1:55432/aqil_research_test"
  )
  foreach ($probe in $probes) {
    $rejected = $false
    try {
      Assert-PgtapUrl $probe
    } catch {
      $rejected = $true
    }
    if (-not $rejected) {
      throw "pgTAP guard accepted a prohibited target."
    }
  }
}
