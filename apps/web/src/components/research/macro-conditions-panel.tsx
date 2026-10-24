import Link from "next/link";

import { SeriesChart } from "@/components/research/series-chart";
import { loadMacroConditions } from "@/lib/research/load-macro-conditions";
import {
  CONDITION_REGIONS,
  conditionRegion,
  presentMacroConditions,
  type MacroConditionsView,
  type MacroSeriesPanel,
} from "@/lib/research/present-macro-conditions";

type Props = {
  view: MacroConditionsView;
  variant: "compact" | "dashboard";
  seriesLines?: Readonly<Record<string, string>>;
};

export function MacroConditionsPanel({ view, variant, seriesLines }: Props) {
  const compact = variant === "compact";
  return (
    <div data-testid="macro-conditions" data-variant={variant}>
      <p className="research-body">{view.intro}</p>
      <p className="research-meta" data-testid="macro-completeness">
        {view.completenessLine}
      </p>
      <p className="research-meta" data-testid="macro-revision-limit">
        {view.revisionLimit}
      </p>
      <details className="macro-details" data-testid="macro-freshness">
        <summary>How freshness is judged</summary>
        <p className="research-meta">{view.freshnessRule}</p>
      </details>
      {compact ? null : (
        <nav className="research-meta" aria-label="Region" data-testid="macro-region-filter">
          {CONDITION_REGIONS.map((item) => (
            <Link
              key={item.id}
              href={item.id === "global" ? "/conditions" : `/conditions?region=${item.id}`}
              prefetch={false}
              data-testid={`macro-region-${item.id}`}
              aria-current={view.regionId === item.id ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
      {compact ? (
        <p className="research-meta">
          <Link href="/conditions" prefetch={false} data-testid="macro-full-view">
            Full indicator view
          </Link>
        </p>
      ) : null}
      {view.groups.map((group) => (
        <section key={group.id} aria-labelledby={`macro-group-${group.id}`}>
          <h3 id={`macro-group-${group.id}`} className="research-section-title">
            {group.label}
          </h3>
          {group.panels.map((panel) => (
            <IndicatorPanel
              key={panel.sourceId}
              panel={panel}
              compact={compact}
              readingLine={compact ? undefined : seriesLines?.[panel.sourceId]}
            />
          ))}
        </section>
      ))}
      <section aria-labelledby="macro-unavailable-heading">
        <h3 id="macro-unavailable-heading" className="research-section-title">
          Unavailable
        </h3>
        {view.unavailable.map((item) => (
          <article
            key={item.id}
            className={compact ? "macro-panel macro-panel--compact" : "macro-panel"}
            data-testid={`macro-unavailable-${item.id}`}
          >
            <h4 className="macro-panel-title">{item.name}</h4>
            <p className="research-body">{item.detail}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function IndicatorPanel({
  panel,
  compact,
  readingLine,
}: {
  panel: MacroSeriesPanel;
  compact: boolean;
  readingLine?: string;
}) {
  return (
    <article
      className={compact ? "macro-panel macro-panel--compact" : "macro-panel"}
      id={`macro-panel-${panel.sourceId}`}
      data-testid={`macro-panel-${panel.sourceId}`}
      data-state={panel.state}
    >
      <h4 className="macro-panel-title">{panel.name}</h4>
      {panel.region ? <p className="macro-region">{panel.region}</p> : null}
      {panel.warning ? <p className="macro-warning">{panel.warning}</p> : null}
      {panel.valueLabel ? (
        <p className="macro-value" data-testid={`macro-value-${panel.sourceId}`}>
          <span className="macro-value-figure">{panel.valueLabel}</span>
          {panel.valueUnit ? <span className="macro-value-unit">{panel.valueUnit}</span> : null}
          {panel.periodLabel ? (
            <span className={panel.state === "stale" ? "macro-value-when macro-value-when--stale" : "macro-value-when"}>
              {panel.periodLabel}
            </span>
          ) : null}
        </p>
      ) : null}
      {panel.changeLabel ? <p className="macro-change">{panel.changeLabel}</p> : null}
      {readingLine ? (
        <p className="macro-reading-line" data-testid={`macro-reading-line-${panel.sourceId}`}>
          {readingLine}
        </p>
      ) : null}
      {panel.chart ? <SeriesChart chart={panel.chart} testId={`macro-sparkline-${panel.sourceId}`} /> : null}
      {panel.gapLine ? <p className="research-meta">{panel.gapLine}</p> : null}
      {panel.chartNote ? <p className="research-body">{panel.chartNote}</p> : null}
      {!compact && panel.measures ? (
        <>
          <h5 className="macro-heading">What it measures</h5>
          <p className="research-body">{panel.measures}</p>
        </>
      ) : null}
      {!compact && panel.matters ? (
        <>
          <h5 className="macro-heading">Why it matters</h5>
          <p className="research-body">{panel.matters}</p>
        </>
      ) : null}
      {panel.sourceLabel ? <p className="research-meta">Source: {panel.sourceLabel}</p> : null}
      {panel.sourceHref ? (
        <p className="research-meta">
          <a
            href={panel.sourceHref}
            rel="noopener noreferrer"
            target="_blank"
            data-testid={`macro-source-${panel.sourceId}`}
          >
            {panel.sourceLinkLabel}
          </a>
        </p>
      ) : null}
      {panel.sourceLinkNote ? <p className="research-meta">{panel.sourceLinkNote}</p> : null}
      <p className="research-meta">{panel.freshnessLabel}</p>
      {panel.details.length > 0 ? (
        <details className="macro-details">
          <summary>Technical details</summary>
          <ul className="macro-detail-list">
            {panel.details.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          {panel.evidenceHref ? (
            <p className="research-meta">
              <Link href={panel.evidenceHref} prefetch={false}>
                Evidence
              </Link>
            </p>
          ) : null}
        </details>
      ) : null}
    </article>
  );
}

export async function MacroConditionsSection({
  variant,
  seriesLines,
  region,
}: {
  variant: "compact" | "dashboard";
  seriesLines?: Readonly<Record<string, string>>;
  region?: string;
}) {
  const loaded = await loadMacroConditions();
  if (loaded.status === "unavailable") {
    return (
      <p className="research-body" data-testid="macro-conditions-unavailable">
        {loaded.reason}
      </p>
    );
  }
  const view = presentMacroConditions({
    series: loaded.series,
    asOf: new Date(),
    region: variant === "dashboard" ? conditionRegion(region) : "global",
  });
  return <MacroConditionsPanel view={view} variant={variant} seriesLines={seriesLines} />;
}
