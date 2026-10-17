"""Pre-event macro assessment payload."""

from aqil_research.forward.intelligence.pre_event import build_macro_pre_event_scenario


def test_macro_pre_event_includes_expected_information() -> None:
    payload = build_macro_pre_event_scenario(
        event_payload={
            "event_id": "event:verified:fed:fomc:2026-10-28",
            "title": "FOMC meeting",
            "category": "central_bank_meeting",
            "source_id": "federal_reserve_fomc_calendar",
            "source_locator": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
            "date_precision": "confirmed",
        },
        macro_rationale="Qualitative only.",
        transmission="Rates and financial conditions.",
        geographic_exposure="Global ETFs include US exposure.",
    )
    assert payload["evidence_class"] == "research_assessment"
    assert "Federal funds rate" in str(payload["expected_information"])
    assert payload["no_action_conclusion"]
