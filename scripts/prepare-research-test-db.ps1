# Create or replace the disposable research test database.
# This script never resets the development database named postgres.
$ErrorActionPreference = "Stop"
$container = "supabase_db_ojvswermsbbaltjohqph"
$testDatabase = "aqil_research_test"
if ($testDatabase -ne "aqil_research_test") {
  Write-Error "Refusing to prepare a database that is not aqil_research_test."
}

docker exec $container psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c @"
select pg_terminate_backend(pid)
from pg_stat_activity
where datname = '$testDatabase' and pid <> pg_backend_pid();
"@ | Out-Null
docker exec $container psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "drop database if exists $testDatabase;"
docker exec $container psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "create database $testDatabase;"

$dump = docker exec $container pg_dump -U postgres -d postgres --schema-only --no-owner -n research -n forward
if ($LASTEXITCODE -ne 0) {
  Write-Error "Schema dump from the development database failed."
}
$dump | docker exec -i $container psql -U postgres -d $testDatabase -v ON_ERROR_STOP=1 | Out-Null

docker exec $container psql -U postgres -d $testDatabase -v ON_ERROR_STOP=1 -c @"
create table research.test_isolation_marker (
  marker text primary key
);
insert into research.test_isolation_marker (marker) values ('disposable-research-test');
revoke all on table research.test_isolation_marker from public, anon, authenticated;
grant select on table research.test_isolation_marker to research_writer, research_worker;
"@

$identity = docker exec $container psql -U postgres -d $testDatabase -tA -c "select current_database();"
if ($identity.Trim() -ne $testDatabase) {
  Write-Error "Prepared database identity was $($identity.Trim())."
}
Write-Host "Prepared disposable database $testDatabase. The development database was not reset."
