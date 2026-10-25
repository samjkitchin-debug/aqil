import Link from "next/link";

import { SeriesChart } from "@/components/research/series-chart";
import { loadMacroConditions } from "@/lib/research/load-macro-conditions";
import {
  CONDITION_REGIONS,
  conditionRegion,
  presentMacroConditions,
  type MacroSeriesPanel,
} from "@/lib/research/present-macro-conditions";
import {
  presentIntelligenceDashboard,
  type DashboardMetric,
  type IntelligenceDashboard,
} from "@/lib/research/present-intelligence-dashboard";
import type { SeriesChartModel } from "@/lib/research/series-chart-model";

type Props = {
  view: IntelligenceDashboard;
  seriesLines?: Readonly<Record<string, string>>;
};

export function IntelligenceDashboardView({ view, seriesLines }: Props) {
  return (
    <div data-testid="intelligence-dashboard">
      <div className="intel-scope">
        <h2 className="intel-region-title">{view.regionLabel}</h2>
        {view.scopeLine ? <p className="research-meta">{view.scopeLine}</p> : null}
        <nav className="intel-regions" aria-label="Region">
          {CONDITION_REGIONS.map((item) => (
            <Link
              key={item.id}
              href={item.id === "global" ? "/conditions" : `/conditions?region=${item.id}`}
              prefetch={false}
              aria-current={view.regionId === item.id ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
      <p className="research-meta" data-testid="macro-completeness">
        {view.completenessLine}
      </p>
      <p className="research-meta" data-testid="macro-revision-limit">
        {view.revisionLimit}
      </p>
      <details className="macro-details">
        <summary>How to read these figures</summary>
        <p className="research-meta">{view.intro}</p>
        <p className="research-meta">{view.freshnessRule}</p>
      </details>
      {view.categories.length === 0 ? (
        <p className="research-body">No live series is stored for this region.</p>
      ) : (
        view.categories.map((category) => (
          <details key={category.id} className="intel-category">
            <summary className="intel-summary">
              <span className="intel-category-name">{category.label}</span>
              <span className="intel-summary-metrics">
                {category.summary.map((metric) => (
                  <MetricSummary key={metric.sourceId} metric={metric} showRegion={view.regionId === "global"} />
                ))}
              </span>
            </summary>
            <div className="intel-category-body">
              {category.panels.map((panel) => (
                <IndicatorDetail
                  key={panel.sourceId}
                  panel={panel}
                  readingLine={seriesLines?.[panel.sourceId]}
                />
              ))}
            </div>
          </details>
        ))
      )}
      {view.absentLine ? <p className="research-meta">{view.absentLine}</p> : null}
    </div>
  );
}

function MetricSummary({ metric, showRegion }: { metric: DashboardMetric; showRegion: boolean }) {
  return (
    <span className="intel-metric">
      <span className="intel-metric-name">
        {metric.name}
        {showRegion && metric.region ? <span className="intel-metric-region"> {metric.region}</span> : null}
      </span>
      {metric.valueLabel ? (
        <span className="intel-metric-value aq-num">
          {metric.valueLabel}
          {metric.valueUnit ? <span className="intel-metric-unit"> {metric.valueUnit}</span> : null}
        </span>
      ) : (
        <span className="intel-metric-value">No observation</span>
      )}
      {metric.changeLabel ? <span className="intel-metric-change">{metric.changeLabel}</span> : null}
      {metric.periodLabel ? (
        <span className="intel-metric-when">
          {metric.periodLabel}
          {metric.state === "stale" ? " · Stale" : null}
        </span>
      ) : null}
      {metric.chart ? <TrendMark chart={metric.chart} /> : null}
    </span>
  );
}

function TrendMark({ chart }: { chart: SeriesChartModel }) {
  const { plot } = chart;
  return (
    <svg
      className="intel-trend"
      viewBox={`${plot.x} ${plot.y} ${plot.width} ${plot.height}`}
      aria-hidden="true"
    >
      {chart.segments.map((segment) => (
        <path key={segment.periods.join("|")} d={segment.d} />
      ))}
    </svg>
  );
}

function IndicatorDetail({
  panel,
  readingLine,
}: {
  panel: MacroSeriesPanel;
  readingLine?: string;
}) {
  return (
    <article
      className="intel-indicator"
      id={`macro-panel-${panel.sourceId}`}
      data-testid={`macro-panel-${panel.sourceId}`}
      data-state={panel.state}
    >
      <div className="intel-indicator-copy">
        <h3 className="intel-indicator-name">{panel.name}</h3>
        {panel.region ? <p className="research-meta">{panel.region}</p> : null}
        {panel.warning ? <p className="macro-warning">{panel.warning}</p> : null}
        {panel.valueLabel ? (
          <p className="macro-value" data-testid={`macro-value-${panel.sourceId}`}>
            <span className="macro-value-figure aq-num">{panel.valueLabel}</span>
            {panel.valueUnit ? <span className="macro-value-unit">{panel.valueUnit}</span> : null}
            {panel.periodLabel ? (
              <span className={panel.state === "stale" ? "macro-value-when macro-value-when--stale" : "macro-value-when"}>
                {panel.periodLabel}
                {panel.state === "stale" ? " · Stale" : ""}
              </span>
            ) : null}
          </p>
        ) : null}
        {panel.changeLabel ? <p className="macro-change">{panel.changeLabel}</p> : null}
        {readingLine ? (
          <p className="research-meta" data-testid={`macro-reading-line-${panel.sourceId}`}>
            {readingLine}
          </p>
        ) : null}
        {panel.gapLine ? <p className="research-meta">{panel.gapLine}</p> : null}
        {panel.chartNote ? <p className="research-meta">{panel.chartNote}</p> : null}
        <p className="research-meta">{panel.freshnessLabel}</p>
        {panel.measures || panel.matters ? (
          <details className="macro-details">
            <summary>What this measures</summary>
            {panel.measures ? <p className="research-body">{panel.measures}</p> : null}
            {panel.matters ? <p className="research-body">{panel.matters}</p> : null}
          </details>
        ) : null}
        <details className="macro-details">
          <summary>Source and technical details</summary>
          {panel.sourceLabel ? <p className="research-meta">Source: {panel.sourceLabel}</p> : null}
          {panel.sourceHref ? (
            <p className="research-meta">
              <a href={panel.sourceHref} rel="noopener noreferrer" target="_blank">
                {panel.sourceLinkLabel}
              </a>
            </p>
          ) : null}
          {panel.sourceLinkNote ? <p className="research-meta">{panel.sourceLinkNote}</p> : null}
          {panel.details.length > 0 ? (
            <ul className="macro-detail-list">
              {panel.details.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
          {panel.evidenceHref ? (
            <p className="research-meta">
              <Link href={panel.evidenceHref} prefetch={false}>
                Evidence
              </Link>
            </p>
          ) : null}
        </details>
      </div>
      {panel.chart ? (
        <SeriesChart chart={panel.chart} testId={`macro-sparkline-${panel.sourceId}`} />
      ) : null}
    </article>
  );
}

export async function IntelligenceDashboardSection({
  region,
  seriesLines,
}: {
  region?: string;
  seriesLines?: Readonly<Record<string, string>>;
}) {
  const loaded = await loadMacroConditions();
  if (loaded.status === "unavailable") {
    return (
      <p className="research-body" data-testid="macro-conditions-unavailable">
        {loaded.reason}
      </p>
    );
  }
  const view = presentIntelligenceDashboard(
    presentMacroConditions({
      series: loaded.series,
      asOf: new Date(),
      region: conditionRegion(region),
    }),
  );
  return <IntelligenceDashboardView view={view} seriesLines={seriesLines} />;
}
