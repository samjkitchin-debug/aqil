# Recreate the disposable pgTAP database from the current schema only.
# This script never runs supabase db reset and never drops the database named postgres.
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\pgtap-guard.ps1"

Assert-PgtapProbesRejected
if (-not $env:AQIL_PGTAP_DATABASE_URL) {
  throw "AQIL_PGTAP_DATABASE_URL is required before preparing the pgTAP database."
}
Assert-PgtapUrl $env:AQIL_PGTAP_DATABASE_URL

$container = "supabase_db_ojvswermsbbaltjohqph"
$testDatabase = "aqil_pgtap_test"

function Invoke-Psql {
  param([string]$Database, [string]$Sql)
  docker exec $container psql -U postgres -d $Database -v ON_ERROR_STOP=1 -tA -c $Sql
  if ($LASTEXITCODE -ne 0) {
    throw "psql failed on database $Database."
  }
}

$liveCountSql = "select count(*) from research.economic_observations o join research.source_retrievals r using (retrieval_id) where r.collection_mode = 'live'"
$before = (Invoke-Psql "postgres" $liveCountSql).Trim()

docker exec $container psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c @"
select pg_terminate_backend(pid)
from pg_stat_activity
where datname = '$testDatabase' and pid <> pg_backend_pid();
"@ | Out-Null
docker exec $container psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "drop database if exists $testDatabase;"
if ($LASTEXITCODE -ne 0) { throw "Could not drop $testDatabase." }
docker exec $container psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "create database $testDatabase;"
if ($LASTEXITCODE -ne 0) { throw "Could not create $testDatabase." }

docker exec $container pg_dump -U postgres -d postgres --schema-only --no-owner --format=custom --file=/tmp/aqil_pgtap_schema.dump
if ($LASTEXITCODE -ne 0) { throw "Schema dump from the development database failed." }
docker exec $container pg_restore -U postgres -d $testDatabase --no-owner --schema-only /tmp/aqil_pgtap_schema.dump
if ($LASTEXITCODE -gt 1) { throw "Schema restore into $testDatabase failed." }

Invoke-Psql $testDatabase @"
create table if not exists research.pgtap_isolation_marker (marker text primary key);
insert into research.pgtap_isolation_marker (marker) values ('disposable-pgtap-test')
on conflict (marker) do nothing;
"@ | Out-Null

$identity = (Invoke-Psql $testDatabase "select current_database()").Trim()
$marker = (Invoke-Psql $testDatabase "select marker from research.pgtap_isolation_marker").Trim()
if ($identity -ne $testDatabase -or $marker -ne "disposable-pgtap-test") {
  throw "pgTAP database identity was not verified."
}
$markerOnDevelopment = docker exec $container psql -U postgres -d postgres -tA -c "select to_regclass('research.pgtap_isolation_marker');"
if ($markerOnDevelopment.Trim() -ne "") {
  throw "The pgTAP marker must not exist on the development database."
}

# instruments is intentionally absent from preserved database postgres.
# Apply that migration only on this disposable database so etf_instruments.test.sql can run.
$instrumentsOnTest = (Invoke-Psql $testDatabase "select exists(select 1 from information_schema.schemata where schema_name = 'instruments')").Trim()
if ($instrumentsOnTest -ne "t") {
  $migration = Join-Path (Split-Path -Parent $PSScriptRoot) "supabase\migrations\20261024120000_etf_instruments.sql"
  docker cp $migration "${container}:/tmp/aqil_pgtap_etf_instruments.sql"
  if ($LASTEXITCODE -ne 0) { throw "Could not copy the instruments migration." }
  docker exec $container psql -U postgres -d $testDatabase -v ON_ERROR_STOP=1 -f /tmp/aqil_pgtap_etf_instruments.sql
  if ($LASTEXITCODE -ne 0) { throw "Could not apply the instruments migration on $testDatabase." }
}
$marketOnTest = (Invoke-Psql $testDatabase "select to_regclass('instruments.market_price_observations')").Trim()
if ($marketOnTest -eq "") {
  $marketMigration = Join-Path (Split-Path -Parent $PSScriptRoot) "supabase\migrations\20261102160000_etf_market_data.sql"
  docker cp $marketMigration "${container}:/tmp/aqil_pgtap_etf_market_data.sql"
  if ($LASTEXITCODE -ne 0) { throw "Could not copy the ETF market-data migration." }
  docker exec $container psql -U postgres -d $testDatabase -v ON_ERROR_STOP=1 -f /tmp/aqil_pgtap_etf_market_data.sql
  if ($LASTEXITCODE -ne 0) { throw "Could not apply the ETF market-data migration on $testDatabase." }
}
$instrumentsOnDevelopment = (Invoke-Psql "postgres" "select exists(select 1 from information_schema.schemata where schema_name = 'instruments')").Trim()
if ($instrumentsOnDevelopment -eq "t") {
  throw "The instruments schema must stay off preserved database postgres."
}

$cyclesOnTest = (Invoke-Psql $testDatabase "select to_regclass('research.research_cycles')").Trim()
if ($cyclesOnTest -eq "") {
  $cycleMigration = Join-Path (Split-Path -Parent $PSScriptRoot) "supabase\migrations\20261101120000_research_cycles.sql"
  docker cp $cycleMigration "${container}:/tmp/aqil_research_cycles.sql"
  if ($LASTEXITCODE -ne 0) { throw "Could not copy the research cycle migration." }
  docker exec $container psql -U postgres -d $testDatabase -v ON_ERROR_STOP=1 -f /tmp/aqil_research_cycles.sql
  if ($LASTEXITCODE -ne 0) { throw "Could not apply the research cycle migration on $testDatabase." }
}

$atlasOnTest = (Invoke-Psql $testDatabase "select to_regclass('research.decision_anchors')").Trim()
if ($atlasOnTest -eq "") {
  $atlasMigration = Join-Path (Split-Path -Parent $PSScriptRoot) "supabase\migrations\20261104120000_historical_state_atlas.sql"
  docker cp $atlasMigration "${container}:/tmp/aqil_state_atlas.sql"
  if ($LASTEXITCODE -ne 0) { throw "Could not copy the historical-state atlas migration." }
  docker exec $container psql -U postgres -d $testDatabase -v ON_ERROR_STOP=1 -1 -f /tmp/aqil_state_atlas.sql
  if ($LASTEXITCODE -ne 0) { throw "Could not apply the historical-state atlas migration on $testDatabase." }
}
$protocolOnTest = (Invoke-Psql $testDatabase "select to_regclass('research.etf_protocol_trials')").Trim()
if ($protocolOnTest -eq "") {
  $protocolMigration = Join-Path (Split-Path -Parent $PSScriptRoot) "supabase\migrations\20261104183000_etf_research_protocol.sql"
  docker cp $protocolMigration "${container}:/tmp/aqil_etf_protocol.sql"
  if ($LASTEXITCODE -ne 0) { throw "Could not copy the ETF protocol migration." }
  docker exec $container psql -U postgres -d $testDatabase -v ON_ERROR_STOP=1 -1 -f /tmp/aqil_etf_protocol.sql
  if ($LASTEXITCODE -ne 0) { throw "Could not apply the ETF protocol migration on $testDatabase." }
}
$discoveryOnTest = (Invoke-Psql $testDatabase "select to_regclass('research.discovery_v2_trials')").Trim()
if ($discoveryOnTest -eq "") {
  $discoveryMigration = Join-Path (Split-Path -Parent $PSScriptRoot) "supabase\migrations\20261104210000_vwra_discovery_v2.sql"
  docker cp $discoveryMigration "${container}:/tmp/aqil_vwra_discovery.sql"
  if ($LASTEXITCODE -ne 0) { throw "Could not copy the VWRA discovery migration." }
  docker exec $container psql -U postgres -d $testDatabase -v ON_ERROR_STOP=1 -1 -f /tmp/aqil_vwra_discovery.sql
  if ($LASTEXITCODE -ne 0) { throw "Could not apply the VWRA discovery migration on $testDatabase." }
}
$symbolCheck = (Invoke-Psql $testDatabase "select pg_get_constraintdef(oid) from pg_constraint where conname = 'discovery_v2_trials_symbol'").Trim()
if ($symbolCheck -notmatch "EIMI") {
  $comparisonMigration = Join-Path (Split-Path -Parent $PSScriptRoot) "supabase\migrations\20261105120000_eimi_vwra_comparison.sql"
  docker cp $comparisonMigration "${container}:/tmp/aqil_eimi_vwra_comparison.sql"
  if ($LASTEXITCODE -ne 0) { throw "Could not copy the EIMI comparison migration." }
  docker exec $container psql -U postgres -d $testDatabase -v ON_ERROR_STOP=1 -1 -f /tmp/aqil_eimi_vwra_comparison.sql
  if ($LASTEXITCODE -ne 0) { throw "Could not apply the EIMI comparison migration on $testDatabase." }
}
$after = (Invoke-Psql "postgres" $liveCountSql).Trim()
if ($before -ne $after) {
  throw "Development live observation count changed from $before to $after."
}
Write-Host "Prepared disposable database $testDatabase. Development live observations remained $after."
