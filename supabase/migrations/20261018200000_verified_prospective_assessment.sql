-- Allow one verified real-event scenario and its later outcome.
-- Synthetic rows stay labelled synthetic. Hosted apply still needs founder approval.

alter table forward.forward_scenarios
  drop constraint scenario_evidence_class,
  drop constraint scenario_payload_labelled;

alter table forward.forward_scenarios
  add constraint scenario_evidence_class check (
    evidence_class in ('synthetic_demonstration', 'verified_real_event')
  ),
  add constraint scenario_payload_labelled check (
    (
      evidence_class = 'synthetic_demonstration'
      and coalesce(payload->>'evidence_class', '') = 'synthetic_demonstration'
    )
    or (
      evidence_class = 'verified_real_event'
      and coalesce(payload->>'evidence_class', '') = 'verified_real_event'
      and coalesce(payload->>'no_directional_forecast', '') in ('true', 'True')
    )
  );

alter table forward.event_outcomes
  drop constraint outcome_evidence_class,
  drop constraint outcome_payload_labelled;

alter table forward.event_outcomes
  add constraint outcome_evidence_class check (
    evidence_class in ('synthetic_demonstration', 'verified_release_outcome')
  ),
  add constraint outcome_payload_labelled check (
    (
      evidence_class = 'synthetic_demonstration'
      and coalesce(payload->>'evidence_class', '') = 'synthetic_demonstration'
    )
    or (
      evidence_class = 'verified_release_outcome'
      and coalesce(payload->>'evidence_class', '') = 'verified_release_outcome'
      and payload->>'forecasting_skill' is null
    )
  );
