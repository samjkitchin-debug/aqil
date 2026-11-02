import { displayLevel } from "@/lib/research/format-indicator";
import type { PrivateMethodologyResult } from "@/lib/research/private-methodology-result";
import { buildSeriesChart } from "@/lib/research/series-chart-model";

const DAY = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export function MethodologyPrivateResult({ result }: { result: PrivateMethodologyResult }) {
  const chart = result.series ? chartFor(result.series) : null;
  return (
    <div className="intel-method-result" data-testid="methodology-private-result">
      <p className="research-body">{result.headline}</p>
      <p className="research-body">{result.standing}</p>
      <dl className="intel-method-facts">
        {result.facts.map((item) => (
          <div key={item.label}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
      {chart ? (
        <figure className="macro-chart" data-testid="methodology-private-chart">
          <p className="macro-chart-unit">{chart.unitLabel}</p>
          <div className="macro-chart-plot">
            <svg
              className="research-chart"
              viewBox={`0 0 ${chart.width} ${chart.height}`}
              role="img"
              aria-label={`${chart.label}. ${chart.caption}`}
            >
              {chart.yTicks.map((tick) => (
                <g key={`y-${tick.label}`}>
                  <line
                    className="research-chart-grid"
                    x1={chart.plot.x}
                    x2={chart.plot.x + chart.plot.width}
                    y1={tick.y}
                    y2={tick.y}
                  />
                  <text className="research-chart-axis" x={chart.plot.x - 6} y={tick.y + 4} textAnchor="end">
                    {tick.label}
                  </text>
                </g>
              ))}
              {chart.segments.map((segment) => (
                <path key={segment.periods[0]} className="research-chart-line" d={segment.d} />
              ))}
              {chart.xTicks.map((tick) => (
                <text
                  key={`x-${tick.label}-${tick.x}`}
                  className="research-chart-axis"
                  x={tick.x}
                  y={chart.height - 8}
                  textAnchor={tick.anchor}
                >
                  {tick.label}
                </text>
              ))}
            </svg>
          </div>
          <p className="research-chart-caption">{result.series?.caption}</p>
        </figure>
      ) : null}
      {result.dates.length > 0 ? <DateChart dates={result.dates} /> : null}
      {result.dates.length > 0 ? (
        <ul className="intel-method-dates">
          {result.dates.map((mark) => (
            <li key={`${mark.series ?? ""}-${mark.kind}-${mark.period}`}>
              {mark.series ? `${mark.series}, ` : ""}
              {mark.kind} {formatDay(mark.period)}
            </li>
          ))}
        </ul>
      ) : null}
      {result.diagnostic ? <p className="research-body">{result.diagnostic}</p> : null}
      {result.limitations.length > 0 ? (
        <ul className="intel-method-limits">
          {result.limitations.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function chartFor(series: NonNullable<PrivateMethodologyResult["series"]>) {
  const points = series.points.flatMap((point) => {
    const display = displayLevel(String(point.value), series.unit);
    if (!display) return [];
    return [
      {
        period: point.period,
        display,
        dateLabel: formatDay(point.period),
        valueLabel: display.precise,
      },
    ];
  });
  return buildSeriesChart({
    label: series.label,
    caption: series.caption,
    frequency: series.frequency,
    points,
  });
}

function DateChart({ dates }: { dates: readonly PrivateMethodologyResult["dates"][number][] }) {
  const parsed = dates.flatMap((mark) => {
    const time = Date.parse(`${mark.period.slice(0, 10)}T00:00:00Z`);
    if (Number.isNaN(time)) return [];
    return [{ ...mark, time }];
  });
  if (parsed.length < 2) return null;
  const min = Math.min(...parsed.map((mark) => mark.time));
  const max = Math.max(...parsed.map((mark) => mark.time));
  const span = max - min || 1;
  const width = 360;
  const height = 96;
  const pad = 16;
  return (
    <figure className="macro-chart" data-testid="methodology-date-chart">
      <svg
        className="research-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Stored peaks and troughs. Peaks are the upper marks and troughs the lower marks."
      >
        {parsed.map((mark) => {
          const x = pad + ((mark.time - min) / span) * (width - pad * 2);
          const y = mark.kind === "Peak" ? 28 : 68;
          return (
            <circle
              key={`${mark.series ?? ""}-${mark.kind}-${mark.period}`}
              className="research-chart-point"
              cx={x}
              cy={y}
              r="3"
            >
              <title>{`${mark.kind} ${formatDay(mark.period)}`}</title>
            </circle>
          );
        })}
      </svg>
      <p className="research-chart-caption">
        Peaks are the upper marks and troughs the lower marks. Retrospective latest-revised dates. Not a real-time call.
      </p>
    </figure>
  );
}

function formatDay(iso: string): string {
  const when = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(when.getTime())) return iso;
  return DAY.format(when);
}
