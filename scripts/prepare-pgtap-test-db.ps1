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
$instrumentsOnDevelopment = (Invoke-Psql "postgres" "select exists(select 1 from information_schema.schemata where schema_name = 'instruments')").Trim()
if ($instrumentsOnDevelopment -eq "t") {
  throw "The instruments schema must stay off preserved database postgres."
}

$after = (Invoke-Psql "postgres" $liveCountSql).Trim()
if ($before -ne $after) {
  throw "Development live observation count changed from $before to $after."
}
Write-Host "Prepared disposable database $testDatabase. Development live observations remained $after."
