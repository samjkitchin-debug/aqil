import "server-only";

import type { Client } from "pg";
import { connection } from "next/server";

import { resolveEtfDatabaseUrl } from "@/lib/data/private-database-url";
import {
  HOLDINGS_BLOCKED_REASON,
  type CitedExposureView,
  type EtfAssessmentView,
  type EtfBenchmarkView,
  type EtfCostView,
  type EtfHoldingsView,
  type EtfListingView,
  type EtfShareExplore,
} from "@/lib/etf/present-explore";

const SHARE_CLASS_ISIN = /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;

export type LoadEtfExploreResult =
  | { status: "ready"; shares: EtfShareExplore[] }
  | { status: "empty" }
  | { status: "absent" }
  | { status: "unavailable"; reason: string };

type ShareRow = {
  share_class_id: string;
  isin: string;
  evidence_status: EtfShareExplore["evidenceStatus"];
  distribution_policy: EtfShareExplore["distributionPolicy"];
  hedge_status: EtfShareExplore["hedgeStatus"];
  inception_date: string | null;
  recorded_at: string;
};

function etfDatabaseUrl() {
  return resolveEtfDatabaseUrl({
    nodeEnv: process.env.NODE_ENV,
    configuredUrl: process.env.ETF_DATABASE_URL,
  });
}

export async function loadEtfExplore(isin?: string): Promise<LoadEtfExploreResult> {
  await connection();
  const requested = isin?.trim() ?? "";
  if (requested && !SHARE_CLASS_ISIN.test(requested)) return { status: "absent" };
  const databaseUrl = etfDatabaseUrl();
  if (databaseUrl.status === "unavailable") return databaseUrl;

  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: databaseUrl.url });
    await client.connect();
    try {
      const shares = await client.query<ShareRow>(
        `select share_class_id::text,
                isin,
                evidence_status,
                distribution_policy,
                hedge_status,
                to_char(inception_date, 'YYYY-MM-DD') as inception_date,
                to_char(recorded_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as recorded_at
         from instruments.share_classes
         where ($1::text is null or isin = $1)
         order by recorded_at, isin`,
        [requested || null],
      );
      if (shares.rows.length === 0) return requested ? { status: "absent" } : { status: "empty" };

      const views: EtfShareExplore[] = [];
      for (const share of shares.rows) {
        views.push(await loadShare(client, share));
      }
      return { status: "ready", shares: views };
    } finally {
      await client.end();
    }
  } catch {
    return {
      status: "unavailable",
      reason: "The ETF database could not be read.",
    };
  }
}

async function loadShare(client: Client, share: ShareRow): Promise<EtfShareExplore> {
  const listings = await client.query<EtfListingView & { trading_currency: string }>(
    `select mic, trading_currency, ticker
     from instruments.listings
     where share_class_id = $1
     order by mic, trading_currency, ticker`,
    [share.share_class_id],
  );
  const costs = await client.query<{
    characteristic_code: string;
    availability: "cited" | "unavailable";
    value_text: string | null;
    source_id: string | null;
  }>(
    `select characteristic_code, availability, value_text, source_id
     from instruments.dated_characteristics
     where share_class_id = $1
       and characteristic_code in ('ter', 'ongoing_charge', 'tracking_difference', 'aum', 'bid_ask_spread', 'total_cost')
     order by characteristic_code, as_of_date desc`,
    [share.share_class_id],
  );
  const holdings = await client.query<{
    as_of_date: string;
    completeness: string;
    line_count: string;
  }>(
    `select to_char(s.as_of_date, 'YYYY-MM-DD') as as_of_date,
            s.completeness,
            count(l.line_id)::text as line_count
     from instruments.holdings_snapshots s
     left join instruments.holdings_lines l on l.snapshot_id = s.snapshot_id
     where s.share_class_id = $1
       and s.rights_gate = 'permitted'
     group by s.snapshot_id, s.as_of_date, s.completeness
     order by s.as_of_date desc
     limit 1`,
    [share.share_class_id],
  );
  const benchmark = await client.query<{
    benchmark_name: string;
    return_convention: string;
    currency: string;
  }>(
    `select b.benchmark_name, b.return_convention, b.currency
     from instruments.dated_characteristics c
     join instruments.benchmarks b on b.benchmark_id::text = c.value_text
     where c.share_class_id = $1
       and c.characteristic_code = 'benchmark_id'
       and c.availability = 'cited'
     order by c.as_of_date desc
     limit 1`,
    [share.share_class_id],
  );
  const assessment = await client.query<{
    eligibility: EtfAssessmentView["eligibility"];
    evidence_status: string;
    statement: string;
    recorded_at: string;
  }>(
    `select eligibility,
            evidence_status,
            statement,
            to_char(recorded_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as recorded_at
     from instruments.assessments
     where share_class_id = $1
     order by recorded_at desc
     limit 1`,
    [share.share_class_id],
  );
  const fundReturns = await client.query<{ count: string }>(
    `select count(*)::text as count from instruments.fund_returns where share_class_id = $1`,
    [share.share_class_id],
  );
  const exposures = await client.query<{
    exposure_class: string;
    weight_text: string | null;
    as_of_date: string;
    source_id: string;
    source_locator: string;
    recorded_at: string;
  }>(
    `select exposure_class,
            weight::text as weight_text,
            to_char(as_of_date, 'YYYY-MM-DD') as as_of_date,
            source_id,
            source_locator,
            to_char(recorded_at at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as recorded_at
     from instruments.exposure_snapshots
     where share_class_id = $1
       and evidence_status = 'cited'
       and source_id is not null
       and source_locator is not null
     order by as_of_date, exposure_class`,
    [share.share_class_id],
  );
  const benchmarkReturns = await client.query<{ count: string }>(
    `select count(*)::text as count
     from instruments.benchmark_returns br
     join instruments.dated_characteristics c
       on c.value_text = br.benchmark_id::text
      and c.share_class_id = $1
      and c.characteristic_code = 'benchmark_id'
      and c.availability = 'cited'`,
    [share.share_class_id],
  );

  const holdingRow = holdings.rows[0];
  const holdingsView: EtfHoldingsView = holdingRow
    ? {
        shown: true,
        asOf: holdingRow.as_of_date,
        completeness: holdingRow.completeness,
        lineCount: Number(holdingRow.line_count),
      }
    : { shown: false, reason: HOLDINGS_BLOCKED_REASON };

  const benchmarkRow = benchmark.rows[0];
  const benchmarkView: EtfBenchmarkView = benchmarkRow
    ? {
        cited: true,
        label: benchmarkRow.benchmark_name,
        returnConvention: benchmarkRow.return_convention,
        currency: benchmarkRow.currency,
      }
    : { cited: false };

  const assessmentRow = assessment.rows[0];
  const seenCosts = new Set<string>();
  const costViews: EtfCostView[] = [];
  for (const cost of costs.rows) {
    if (seenCosts.has(cost.characteristic_code)) continue;
    seenCosts.add(cost.characteristic_code);
    costViews.push({
      code: cost.characteristic_code,
      availability: cost.availability,
      valueText: cost.availability === "cited" ? cost.value_text : null,
      sourceId: cost.availability === "cited" ? cost.source_id : null,
    });
  }

  return {
    isin: share.isin,
    evidenceStatus: share.evidence_status,
    distributionPolicy: share.distribution_policy,
    hedgeStatus: share.hedge_status,
    inceptionDate: share.inception_date,
    recordedAt: share.recorded_at,
    listings: listings.rows.map((listing) => ({
      mic: listing.mic,
      tradingCurrency: listing.trading_currency,
      ticker: listing.ticker,
    })),
    costs: costViews,
    holdings: holdingsView,
    benchmark: benchmarkView,
    assessment: assessmentRow
      ? {
          eligibility: assessmentRow.eligibility,
          evidenceStatus: assessmentRow.evidence_status,
          statement: assessmentRow.statement,
          recordedAt: assessmentRow.recorded_at,
        }
      : null,
    fundReturnCount: Number(fundReturns.rows[0]?.count ?? 0),
    benchmarkReturnCount: Number(benchmarkReturns.rows[0]?.count ?? 0),
    exposures: exposures.rows.flatMap((row): CitedExposureView[] => {
      if (!row.source_id || !row.source_locator) return [];
      return [
        {
          exposureClass: row.exposure_class,
          weightText: row.weight_text,
          asOf: row.as_of_date,
          sourceId: row.source_id,
          sourceLocator: row.source_locator,
          recordedAt: row.recorded_at,
        },
      ];
    }),
  };
}
