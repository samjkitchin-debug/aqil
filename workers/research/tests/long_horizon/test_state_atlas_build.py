"""Row assembly without a database write."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from aqil_research.long_horizon.events.identify import ListingSeries
from aqil_research.long_horizon.state_atlas.build import (
    AtlasBatch,
    VintageRow,
    as_of_gdp,
    checksum_lines,
    compile_listing,
    content_checksum,
)
from aqil_research.long_horizon.state_atlas.specification import atlas_specification_hash


def _listing(symbol: str, currency: str, count: int) -> ListingSeries:
    start = date(2020, 1, 1)
    dates = tuple(start + timedelta(days=offset) for offset in range(count))
    closes = tuple(Decimal("100") + Decimal(offset) for offset in range(count))
    return ListingSeries(symbol, currency, dates, closes)


def test_later_gdp_vintage_is_not_visible() -> None:
    rows = (
        VintageRow(date(2020, 1, 1), date(2020, 3, 31), date(2020, 4, 26), Decimal("1.2")),
        VintageRow(date(2020, 1, 1), date(2020, 3, 31), date(2020, 5, 28), Decimal("3.4")),
    )
    early = as_of_gdp(rows, date(2020, 4, 26))
    later = as_of_gdp(rows, date(2020, 5, 28))
    assert as_of_gdp(rows, date(2020, 4, 25)) == []
    assert early[0].value == Decimal("1.2")
    assert later[0].value == Decimal("3.4")


def test_euna_relative_performance_is_blocked_and_repeatable() -> None:
    euna = _listing("EUNA", "EUR", 40)
    vwra = _listing("VWRA", "USD", 40)
    frozen = datetime(2026, 11, 4, tzinfo=UTC)
    specification_hash = atlas_specification_hash()
    first = compile_listing(
        euna,
        specification_hash=specification_hash,
        series=(),
        pit_by_release=(),
        vwra=vwra,
        recorded_at=frozen,
    )
    second = compile_listing(
        euna,
        specification_hash=specification_hash,
        series=(),
        pit_by_release=(),
        vwra=vwra,
        recorded_at=frozen,
    )
    assert first[3] == second[3]
    relative = [row for row in first[1] if str(row[2]).startswith("relative_performance")]
    assert relative
    assert {row[4] for row in relative} == {"blocked_no_foreign_exchange"}
    assert {row[7] for row in relative} == {None}
    assert all("surprise" not in str(row[2]) for row in first[1])
    long_horizon = [row for row in first[2] if row[3] == 756]
    assert long_horizon
    assert {row[4] for row in long_horizon} == {"censored"}
    assert {row[5] for row in long_horizon} == {None}
    batch = AtlasBatch()
    batch.anchors.extend(first[0])
    batch.states.extend(first[1])
    batch.outcomes.extend(first[2])
    again = AtlasBatch()
    again.anchors.extend(second[0])
    again.states.extend(second[1])
    again.outcomes.extend(second[2])
    assert content_checksum(checksum_lines(batch, specification_hash)) == content_checksum(
        checksum_lines(again, specification_hash)
    )
