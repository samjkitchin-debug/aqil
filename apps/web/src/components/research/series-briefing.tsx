import { presentSeriesBriefing, type LiveSeriesRetrieval } from "@/lib/research/present-series-briefing";

type Props = {
  series: LiveSeriesRetrieval;
};

export function SeriesBriefing({ series }: Props) {
  const copy = presentSeriesBriefing(series);
  return (
    <section aria-labelledby="series-briefing-heading" data-testid="series-briefing">
      <h2 id="series-briefing-heading" className="research-section-title">
        {copy.heading}
      </h2>
      <p className="research-body">{copy.notice}</p>
      <p className="research-meta">{copy.sourceLine}</p>
      <p className="research-meta">{copy.spanLine}</p>
      <p className="research-meta">{copy.latestLine}</p>
      {copy.gapLine ? <p className="research-meta">{copy.gapLine}</p> : null}
      <p className="research-meta" data-testid="series-briefing-freshness">
        {copy.freshnessLine}
      </p>
    </section>
  );
}
