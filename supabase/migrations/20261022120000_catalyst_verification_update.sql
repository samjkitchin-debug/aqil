-- Let the research worker refresh a verified schedule after a later retrieval.
-- Insert alone cannot record a new verification time or a changed official start.
-- Local only. Do not apply this file to the hosted project.

grant update (
  last_verified_at,
  scheduled_at,
  status,
  timezone,
  date_precision,
  payload
) on forward.catalyst_events to research_writer;
