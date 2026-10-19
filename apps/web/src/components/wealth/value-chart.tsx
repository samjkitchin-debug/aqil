export function ValueChart({
  points,
  from,
  to,
  currency,
}: {
  points: { date: string; value: string }[];
  from: string;
  to: string;
  currency: string | null;
}) {
  const values = points.map((point) => Number(point.value)).filter((value) => Number.isFinite(value));
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 640;
  const height = 220;
  const coords = values.map((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - ((value - min) / span) * (height - 24) - 12;
    return [x, y] as const;
  });
  const line = coords.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
  const area = `0,${height} ${line} ${width},${height}`;
  const label = `Account value, including contributions, ${from} to ${to}${currency ? `, ${currency}` : ""}`;

  return (
    <figure className="aq-chart">
      <figcaption className="aq-chart-caption">
        <span className="aq-kicker">Account value</span>
        <span className="aq-chart-note">Includes contributions. {from} to {to}.{currency ? ` ${currency}.` : ""}</span>
      </figcaption>
      <svg className="aq-chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
        <polygon className="aq-chart-area" points={area} />
        <polyline className="aq-chart-line" fill="none" points={line} />
      </svg>
    </figure>
  );
}
