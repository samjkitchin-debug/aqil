-- Cycle record privileges. The disposable database is cloned from schema, then this
-- file is applied by supabase test db only when the migration is already in that schema.
begin;

select plan(4);

select has_table('research', 'research_cycles', 'research cycles exist');
select has_table('research', 'research_cycle_events', 'cycle events exist');

select ok(
  not has_table_privilege('anon', 'research.research_cycles', 'SELECT'),
  'anon cannot select research cycles'
);

select ok(
  has_table_privilege('research_writer', 'research.research_cycles', 'INSERT'),
  'research_writer can insert a cycle'
);

select * from finish();
rollback;
