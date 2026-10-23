import Link from "next/link";

import { SeriesSparkline } from "@/components/research/series-sparkline";
import { loadMacroConditions } from "@/lib/research/load-macro-conditions";
import {
  presentMacroConditions,
  type MacroConditionsView,
} from "@/lib/research/present-macro-conditions";

type Props = {
  view: MacroConditionsView;
  variant: "compact" | "dashboard";
};

export function MacroConditionsPanel({ view, variant }: Props) {
  const compact = variant === "compact";
  return (
    <div data-testid="macro-conditions" data-variant={variant}>
      <p className="research-body">{view.intro}</p>
      <p className="research-meta">{view.freshnessRule}</p>
      <p className="research-meta" data-testid="macro-completeness">
        {view.completenessLine}
      </p>
      {view.groups.map((group) => (
        <section key={group.id} aria-labelledby={`macro-group-${group.id}`}>
          <h3 id={`macro-group-${group.id}`} className="research-section-title">
            {group.label}
          </h3>
          {group.panels.map((panel) => (
            <article
              key={panel.sourceId}
              className={compact ? "macro-panel macro-panel--compact" : "macro-panel"}
              data-testid={`macro-panel-${panel.sourceId}`}
              data-state={panel.state}
            >
              <h4 className="macro-panel-title">{panel.name}</h4>
              <p className="research-meta">{panel.stateLine}</p>
              {panel.detailLine ? <p className="research-meta">{panel.detailLine}</p> : null}
              {panel.sourceLine ? <p className="research-meta">{panel.sourceLine}</p> : null}
              <p className="research-body">{panel.description}</p>
              {panel.chart ? (
                <SeriesSparkline
                  marks={panel.chart.marks}
                  label={panel.chart.label}
                  caption={panel.chart.caption}
                  width={panel.chart.width}
                  height={panel.chart.height}
                  testId={`macro-sparkline-${panel.sourceId}`}
                />
              ) : panel.windowLine ? (
                <p className="research-meta">{panel.windowLine}</p>
              ) : null}
              {panel.chartNote ? <p className="research-body">{panel.chartNote}</p> : null}
              {panel.gapLine ? <p className="research-meta">{panel.gapLine}</p> : null}
              <p className="research-meta">{panel.freshnessLine}</p>
              {panel.evidenceHref ? (
                <p className="research-meta">
                  <Link href={panel.evidenceHref} prefetch={false}>
                    Evidence
                  </Link>
                </p>
              ) : null}
            </article>
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

export async function MacroConditionsSection({
  variant,
}: {
  variant: "compact" | "dashboard";
}) {
  const loaded = await loadMacroConditions();
  if (loaded.status === "unavailable") {
    return (
      <p className="research-body" data-testid="macro-conditions-unavailable">
        {loaded.reason}
      </p>
    );
  }
  const view = presentMacroConditions({ series: loaded.series, asOf: new Date() });
  return <MacroConditionsPanel view={view} variant={variant} />;
}
