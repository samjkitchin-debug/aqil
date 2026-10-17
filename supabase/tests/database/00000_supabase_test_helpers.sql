-- Test helpers for pgTAP RLS tests (usebasejump/supabase-test-helpers v0.0.6).
-- Local test files only. Not a migration. Never run `supabase test db --linked`
-- or `supabase db diff`/`db pull` from a database that has executed this file:
-- these SECURITY DEFINER functions can insert into auth.users and are granted
-- to anon and authenticated. Hosted deploy is `supabase db push` of
-- supabase/migrations/ only.
-- DDL runs outside the pgTAP transaction so helpers persist for later test files.

CREATE SCHEMA IF NOT EXISTS tests;
CREATE SCHEMA IF NOT EXISTS test_overrides;

GRANT USAGE ON SCHEMA tests TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA tests REVOKE EXECUTE ON FUNCTIONS FROM public;
ALTER DEFAULT PRIVILEGES IN SCHEMA tests GRANT EXECUTE ON FUNCTIONS TO anon, authenticated, service_role;

GRANT USAGE ON SCHEMA test_overrides TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA test_overrides REVOKE EXECUTE ON FUNCTIONS FROM public;
ALTER DEFAULT PRIVILEGES IN SCHEMA test_overrides GRANT EXECUTE ON FUNCTIONS TO anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION tests.create_supabase_user(identifier text, email text default null, phone text default null, metadata jsonb default null)
RETURNS uuid
 SECURITY DEFINER
 SET search_path = auth, pg_temp
AS $$
DECLARE
 user_id uuid;
BEGIN
 user_id := extensions.uuid_generate_v4();
 INSERT INTO auth.users (id, email, phone, raw_user_meta_data, raw_app_meta_data, created_at, updated_at)
 VALUES (user_id, coalesce(email, concat(user_id, '@test.com')), phone, jsonb_build_object('test_identifier', identifier) || coalesce(metadata, '{}'::jsonb), '{}'::jsonb, now(), now())
 RETURNING id INTO user_id;
 RETURN user_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tests.get_supabase_user(identifier text)
RETURNS json
SECURITY DEFINER
SET search_path = auth, pg_temp
AS $$
 DECLARE
 supabase_user json;
 BEGIN
 SELECT json_build_object(
 'id', id,
 'email', email,
 'phone', phone,
 'raw_user_meta_data', raw_user_meta_data,
 'raw_app_meta_data', raw_app_meta_data
 ) into supabase_user
 FROM auth.users
 WHERE raw_user_meta_data ->> 'test_identifier' = identifier limit 1;
 if supabase_user is null OR supabase_user -> 'id' IS NULL then
 RAISE EXCEPTION 'User with identifier % not found', identifier;
 end if;
 RETURN supabase_user;
 END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tests.get_supabase_uid(identifier text)
 RETURNS uuid
 SECURITY DEFINER
 SET search_path = auth, pg_temp
AS $$
DECLARE
 supabase_user uuid;
BEGIN
 SELECT id into supabase_user FROM auth.users WHERE raw_user_meta_data ->> 'test_identifier' = identifier limit 1;
 if supabase_user is null then
 RAISE EXCEPTION 'User with identifier % not found', identifier;
 end if;
 RETURN supabase_user;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tests.authenticate_as (identifier text)
 RETURNS void
 AS $$
 DECLARE
 user_data json;
 original_auth_data text;
 BEGIN
 original_auth_data := current_setting('request.jwt.claims', true);
 user_data := tests.get_supabase_user(identifier);
 if user_data is null OR user_data ->> 'id' IS NULL then
 RAISE EXCEPTION 'User with identifier % not found', identifier;
 end if;
 perform set_config('role', 'authenticated', true);
 perform set_config('request.jwt.claims', json_build_object(
 'sub', user_data ->> 'id',
 'email', user_data ->> 'email',
 'phone', user_data ->> 'phone',
 'user_metadata', user_data -> 'raw_user_meta_data',
 'app_metadata', user_data -> 'raw_app_meta_data'
 )::text, true);
 EXCEPTION
 WHEN OTHERS THEN
 set local role authenticated;
 set local "request.jwt.claims" to original_auth_data;
 RAISE;
 END
 $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tests.clear_authentication()
 RETURNS void AS $$
BEGIN
 perform set_config('role', 'anon', true);
 perform set_config('request.jwt.claims', null, true);
END
$$ LANGUAGE plpgsql;

begin;
select plan(4);
select function_returns('tests', 'create_supabase_user', array['text', 'text', 'text', 'jsonb'], 'uuid');
select function_returns('tests', 'get_supabase_uid', array['text'], 'uuid');
select function_returns('tests', 'authenticate_as', array['text'], 'void');
select function_returns('tests', 'clear_authentication', array[]::text[], 'void');
select * from finish();
rollback;
