from aqil_research.forward.macro_relevance import assess_macro_relevance


def test_fomc_is_qualitative_only() -> None:
    result = assess_macro_relevance("central_bank_meeting")
    assert result.confidence == "qualitative_only"


def test_unknown_category_is_insufficient() -> None:
    result = assess_macro_relevance("other")
    assert result.confidence == "insufficient_evidence"
