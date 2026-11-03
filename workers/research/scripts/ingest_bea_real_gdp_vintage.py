"""Import the BEA real GDP growth vintage into local postgres. No other database."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import psycopg

from aqil_research.adapters.bea_gdp_vintage.ingest import (
    LOCAL_DATABASE_URL,
    assert_local_research_database,
    download_workbook,
    store_real_gdp_vintage,
)


def main() -> None:
    assert_local_research_database(LOCAL_DATABASE_URL)
    payload, status = download_workbook()
    retrieved_at = datetime.now(UTC)
    with psycopg.connect(LOCAL_DATABASE_URL) as connection:
        result, parsed, file_hash, checksum = store_real_gdp_vintage(
            connection,
            payload,
            retrieved_at=retrieved_at,
            http_status=status,
        )
        connection.commit()
    print(f"inserted {result.inserted}")
    print(f"unchanged {result.unchanged}")
    print(f"points {len(parsed.points)}")
    print(f"quarters {parsed.distinct_quarters}")
    print(f"release_dates {parsed.distinct_release_dates}")
    print(f"skipped_unpublished {parsed.skipped_unpublished}")
    print(f"earliest_period {parsed.points[-1].period_start.isoformat()}")
    print(f"latest_period {parsed.points[0].period_start.isoformat()}")
    print(f"updated_on {parsed.updated_on.isoformat() if parsed.updated_on else ''}")
    print(f"file_sha256 {file_hash}")
    print(f"series_sha256 {checksum}")


if __name__ == "__main__":
    main()
