"""October 2025 invalidates only the windows that include it."""

from datetime import date

from aqil_research.methods.evaluation import (
    classify_sahm_window,
    required_sahm_months,
)


def _months(start: date, count: int) -> set[date]:
    present: set[date] = set()
    cursor = start
    for _ in range(count):
        present.add(cursor)
        year = cursor.year + (cursor.month // 12)
        month = cursor.month % 12 + 1
        cursor = date(year, month, 1)
    return present


def test_september_2025_window_excludes_the_permanent_absence() -> None:
    present = _months(date(2024, 7, 1), 15)
    finding = classify_sahm_window(present, date(2025, 9, 1))
    assert date(2025, 10, 1) not in required_sahm_months(date(2025, 9, 1))
    assert finding.status == "eligible"


def test_september_2026_window_is_permanently_invalid() -> None:
    present = _months(date(2023, 1, 1), 48)
    present.discard(date(2025, 10, 1))
    finding = classify_sahm_window(present, date(2026, 9, 1))
    assert finding.status == "permanently_invalid"
    assert finding.permanent_months == (date(2025, 10, 1),)
    assert finding.next_possible_evaluation == date(2027, 1, 1)
    assert date(2025, 10, 1) not in required_sahm_months(date(2027, 1, 1))


def test_january_2027_waits_for_real_later_months() -> None:
    present = _months(date(2023, 1, 1), 45)
    present.discard(date(2025, 10, 1))
    finding = classify_sahm_window(present, date(2027, 1, 1))
    assert finding.status == "awaiting_observations"
    assert date(2025, 10, 1) not in finding.missing_months


def test_december_2026_still_includes_the_absence() -> None:
    finding = classify_sahm_window(set(), date(2026, 12, 1))
    assert finding.status == "permanently_invalid"
    assert finding.next_possible_evaluation == date(2027, 1, 1)
