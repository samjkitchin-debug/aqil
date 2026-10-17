-- Local and CI only: enable LOGIN for research_worker with a known dev password.
-- Do not run this against hosted Supabase. Hosted passwords must come from vault/secrets.

alter role research_worker with login password 'research_worker';
