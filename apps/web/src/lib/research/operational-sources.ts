/** Predicates that keep fixture and synthetic rows out of Today and Intelligence. */

export const LIVE_PUBLICATION_FILTER = "r.collection_mode = 'live'";

export const OPERATIONAL_CALENDAR_FILTER = [
  "source_id = 'bls_ics_schedule'",
  "source_locator like 'https://www.bls.gov/%'",
  "event_id not like 'event:fixture:%'",
  "evidence_class = 'verified_schedule'",
].join(" and ");
