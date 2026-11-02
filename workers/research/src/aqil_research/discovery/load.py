"""Read-only local extracts. Hosted databases and writes are refused."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

from aqil_research.contracts.observation import AnalysisMode, EconomicObservation
from aqil_research.discovery.calendar import add_months
from aqil_research.persistence.config import DEFAULT_LOCAL_URL
from aqil_research.vintages.asof import monthly_decimal_series, select_as_of_series

READ_AT = datetime(2026, 11, 3, tzinfo=UTC)
NEEDED_DATASETS = (
    "bls.ln.LNS14000000",
    "bls.cu.CUSR0000SA0",
    "fed.g17.IP.B50001.S",
    "fed.h15.RIFSPFF_N.M",
    "fed.h15.RIFLGFCY10_N.M",
    "fed.h15.RIFLGFCM03_N.M",
    "bea.nipa.T20600.W875RX",
    "bea.nipa.U002BU.KPMT",
    "bls.ce.CES0000000001",
)


class LoadError(Exception):
    """Raised when the local databases cannot be read under the programme rules."""


@dataclass
class ListingHistory:
    ticker: str
    isin: str
    mic: str
    currency: str
    quote_unit: str
    distribution_policy: str
    inception_date: date | None
    sessions: tuple[date, ...]
    prices: dict[date, Decimal]
    weekday_gaps: int


@dataclass
class StudyData:
    live_latest_revised: int
    fixture_rows: int
    provider_vintage_rows: int
    publication_allowed_true: int
    research_runs: int
    adjusted_close: int
    raw_close: int
    fx_observations: int
    share_classes: int
    listings_stored: int
    series_inventory: list[dict[str, object]]
    series: dict[str, dict[date, Decimal]]
    observations: dict[str, dict[date, EconomicObservation]]
    listings: dict[str, ListingHistory]
    input_hash: str
    gaps: dict[str, list[str]] = field(default_factory=dict)


def local_database_url(database: str) -> str:
    parsed = urlparse(DEFAULT_LOCAL_URL)
    if parsed.hostname != "127.0.0.1" or parsed.port != 55432:
        raise LoadError("the local research database must be loopback port 55432")
    if database not in {"postgres", "aqil_etf"}:
        raise LoadError("this programme reads only postgres and aqil_etf")
    return DEFAULT_LOCAL_URL.rsplit("/", 1)[0] + "/" + database


def _connect(database: str) -> psycopg.Connection:
    try:
        connection = psycopg.connect(local_database_url(database), connect_timeout=8)
    except psycopg.Error as exc:
        raise LoadError(f"{database} is not available") from exc
    connection.execute("set transaction read only")
    return connection


def _observation(row: dict[str, object]) -> EconomicObservation:
    return EconomicObservation.model_validate(row)


def missing_months(periods: list[date]) -> list[str]:
    if not periods:
        return []
    present = set(periods)
    missing: list[str] = []
    cursor = periods[0]
    while cursor <= periods[-1]:
        if cursor not in present:
            missing.append(cursor.isoformat())
        cursor = add_months(cursor, 1)
    return missing


def weekday_gaps(sessions: tuple[date, ...]) -> int:
    if not sessions:
        return 0
    present = set(sessions)
    count = 0
    cursor = sessions[0]
    last = sessions[-1]
    while cursor <= last:
        if cursor.weekday() < 5 and cursor not in present:
            count += 1
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return count


def _input_hash(
    observations: dict[str, dict[date, EconomicObservation]],
    listings: dict[str, ListingHistory],
) -> str:
    lines: list[str] = []
    for dataset_id, by_period in sorted(observations.items()):
        for period, row in sorted(by_period.items()):
            lines.append(f"{dataset_id}|{period.isoformat()}|{row.observation_id}|{row.raw_value}")
    for ticker, listing in sorted(listings.items()):
        for session in listing.sessions:
            lines.append(f"{ticker}|{session.isoformat()}|{listing.prices[session]}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def load_study() -> StudyData:
    """Read the local macro panel and the stored ETF closes. The transaction is read only."""
    with _connect("postgres") as connection:
        counts = _one(
            connection,
            """
            select
              count(*) filter (
                where r.collection_mode = 'live'
                  and o.series_provenance = 'latest_revised'
              )::int
                as live_latest_revised,
              count(*) filter (where r.collection_mode = 'fixture')::int as fixture_rows,
              count(*) filter (where o.series_provenance = 'provider_vintage')::int
                as provider_vintage_rows
            from research.economic_observations o
            join research.source_retrievals r on r.retrieval_id = o.retrieval_id
            """,
        )
        runs = _one(
            connection,
            """
            select
              count(*)::int as research_runs,
              count(*) filter (where publication_allowed)::int as publication_allowed_true
            from research.research_runs
            """,
        )
        inventory = _rows(
            connection,
            """
            select dataset_id, min(geography) as geography, min(frequency) as frequency,
                   min(source_id) as source_id, count(*)::int as rows,
                   count(distinct period_start)::int as distinct_periods,
                   min(period_start)::text as period_min, max(period_start)::text as period_max,
                   count(*) filter (where source_release_at is not null)::int as release_timestamps,
                   count(*) filter (where series_provenance = 'provider_vintage')::int
                     as provider_vintage_rows,
                   count(distinct provider_vintage_date)::int as distinct_vintage_dates
            from research.economic_observations
            group by dataset_id
            order by dataset_id
            """,
        )
        raw_rows = _rows(
            connection,
            """
            select o.observation_id, o.dataset_id, o.provider_id, o.source_id, o.rights_record_id,
                   o.period_start, o.period_end, o.frequency, o.geography, o.unit,
                   o.seasonal_adjustment, o.raw_value, o.quality_status, o.series_provenance,
                   o.provider_vintage_date, o.source_release_at, o.earliest_model_available_at,
                   o.availability_precision, o.retrieved_at, o.first_seen_at, o.source_locator,
                   o.adapter_version, o.supersedes_observation_id
            from research.economic_observations o
            join research.source_retrievals r on r.retrieval_id = o.retrieval_id
            where r.collection_mode = 'live'
              and o.quality_status = 'observed'
              and o.dataset_id = any(%s)
            """,
            (list(NEEDED_DATASETS),),
        )
    if runs["publication_allowed_true"] != 0:
        raise LoadError(
            "publication_allowed is true on a stored run; this programme will not continue"
        )

    grouped: dict[str, list[EconomicObservation]] = {dataset: [] for dataset in NEEDED_DATASETS}
    for row in raw_rows:
        grouped[str(row["dataset_id"])].append(_observation(row))
    series: dict[str, dict[date, Decimal]] = {}
    observations: dict[str, dict[date, EconomicObservation]] = {}
    gaps: dict[str, list[str]] = {}
    for dataset_id, rows in grouped.items():
        if not rows:
            series[dataset_id] = {}
            observations[dataset_id] = {}
            gaps[dataset_id] = []
            continue
        selected = select_as_of_series(
            tuple(rows),
            dataset_id,
            READ_AT,
            AnalysisMode.LATEST_REVISED,
        )
        if rows[0].frequency == "monthly":
            series[dataset_id] = monthly_decimal_series(selected)
        else:
            series[dataset_id] = {period: row.decimal_value() for period, row in selected.items()}
        observations[dataset_id] = selected
        gaps[dataset_id] = missing_months(sorted(selected))

    with _connect("aqil_etf") as connection:
        etf_counts = _one(
            connection,
            """
            select
              (select count(*)::int from instruments.market_price_observations)
                as adjusted_candidate,
              (select count(*)::int from instruments.market_price_observations
                where price_type = 'close') as raw_close,
              (select count(*)::int from instruments.market_price_observations
                where price_type = 'adjusted_close') as adjusted_close,
              (select count(*)::int from instruments.fx_observations) as fx_observations,
              (select count(*)::int from instruments.share_classes) as share_classes,
              (select count(*)::int from instruments.listings) as listings_stored
            """,
        )
        price_rows = _rows(
            connection,
            """
            select l.ticker, l.mic, l.trading_currency, sc.isin, sc.distribution_policy,
                   sc.inception_date, p.session_date, p.value, p.currency,
                   p.quote_unit, p.price_type
            from instruments.listings l
            join instruments.share_classes sc on sc.share_class_id = l.share_class_id
            join instruments.market_price_observations p on p.listing_id = l.listing_id
            where p.price_type = 'adjusted_close'
            order by l.ticker, p.session_date
            """,
        )
    listings: dict[str, ListingHistory] = {}
    for row in price_rows:
        ticker = str(row["ticker"])
        listing = listings.get(ticker)
        if listing is None:
            listing = ListingHistory(
                ticker=ticker,
                isin=str(row["isin"]),
                mic=str(row["mic"]),
                currency=str(row["currency"]),
                quote_unit=str(row["quote_unit"]),
                distribution_policy=str(row["distribution_policy"]),
                inception_date=row["inception_date"],
                sessions=(),
                prices={},
                weekday_gaps=0,
            )
            listings[ticker] = listing
        session = row["session_date"]
        listing.prices[session] = Decimal(row["value"])
    for ticker, listing in listings.items():
        sessions = tuple(sorted(listing.prices))
        listings[ticker] = ListingHistory(
            ticker=listing.ticker,
            isin=listing.isin,
            mic=listing.mic,
            currency=listing.currency,
            quote_unit=listing.quote_unit,
            distribution_policy=listing.distribution_policy,
            inception_date=listing.inception_date,
            sessions=sessions,
            prices=listing.prices,
            weekday_gaps=weekday_gaps(sessions),
        )
    return StudyData(
        live_latest_revised=int(counts["live_latest_revised"]),
        fixture_rows=int(counts["fixture_rows"]),
        provider_vintage_rows=int(counts["provider_vintage_rows"]),
        publication_allowed_true=int(runs["publication_allowed_true"]),
        research_runs=int(runs["research_runs"]),
        adjusted_close=int(etf_counts["adjusted_close"]),
        raw_close=int(etf_counts["raw_close"]),
        fx_observations=int(etf_counts["fx_observations"]),
        share_classes=int(etf_counts["share_classes"]),
        listings_stored=int(etf_counts["listings_stored"]),
        series_inventory=inventory,
        series=series,
        observations=observations,
        listings=listings,
        input_hash=_input_hash(observations, listings),
        gaps=gaps,
    )


def _rows(
    connection: psycopg.Connection, sql: str, params: tuple[object, ...] = ()
) -> list[dict[str, object]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, params)
        return list(cursor.fetchall())


def _one(connection: psycopg.Connection, sql: str) -> dict[str, object]:
    found = _rows(connection, sql)
    if not found:
        raise LoadError("a required count query returned no row")
    return found[0]
