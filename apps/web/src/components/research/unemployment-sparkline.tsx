import type { ChartPoint } from "@/lib/research/types";

type Props = {
  points: ChartPoint[];
  label: string;
};

export function UnemploymentSparkline({ points, label }: Props) {
  if (points.length < 2) {
    return (
      <p className="research-body" data-testid="research-chart-empty">
        Chart unavailable — insufficient observation points.
      </p>
    );
  }

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 320;
  const height = 120;
  const padding = 8;

  const coords = points.map((p, i) => {
    const x =
      padding + (i / (points.length - 1)) * (width - padding * 2);
    const y =
      height -
      padding -
      ((p.value - min) / span) * (height - padding * 2);
    return `${x},${y}`;
  });

  return (
    <figure>
      <svg
        className="research-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={label}
        data-testid="research-unemployment-chart"
      >
        <polyline
          fill="none"
          stroke="var(--colour-brand-navy)"
          strokeWidth="2"
          points={coords.join(" ")}
        />
      </svg>
      <figcaption className="research-chart-caption">
        {label} (latest {points.length} months, percent)
      </figcaption>
    </figure>
  );
}
