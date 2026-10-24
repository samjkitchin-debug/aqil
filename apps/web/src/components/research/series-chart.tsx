"use client";

import { useId, useState, type KeyboardEvent, type PointerEvent } from "react";

import type { SeriesChartModel } from "@/lib/research/series-chart-model";

type Props = {
  chart: SeriesChartModel;
  testId?: string;
};

export function SeriesChart({ chart, testId }: Props) {
  const [active, setActive] = useState<number | null>(null);
  const titleId = useId();
  const selected = active === null ? null : (chart.points[active] ?? null);
  const tooltip = selected ? tooltipStyle(selected.x, selected.y, chart.width, chart.height) : null;

  function selectFromPointer(event: PointerEvent<SVGRectElement>) {
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) return;
    const bounds = svg.getBoundingClientRect();
    if (bounds.width <= 0) return;
    const x = ((event.clientX - bounds.left) / bounds.width) * chart.width;
    let best = 0;
    let bestDistance = Number.POSITIVE_INFINITY;
    chart.points.forEach((point, index) => {
      const distance = Math.abs(point.x - x);
      if (distance < bestDistance) {
        best = index;
        bestDistance = distance;
      }
    });
    setActive(best);
  }

  return (
    <figure
      className="macro-chart"
      data-testid={testId}
      aria-label={`${chart.label}. ${chart.unitLabel}. ${chart.caption}.`}
    >
      <p id={titleId} className="macro-chart-unit">
        {chart.unitLabel}
      </p>
      <div className="macro-chart-plot">
        <svg
          className="research-chart"
          viewBox={`0 0 ${chart.width} ${chart.height}`}
          role="group"
          aria-labelledby={titleId}
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
            <polyline key={segment.periods.join("|")} className="research-chart-line" points={segment.points} />
          ))}
          {chart.points.map((point, index) => (
            <circle
              key={point.period}
              className={
                index === active ? "research-chart-point research-chart-point--active" : "research-chart-point"
              }
              cx={point.x}
              cy={point.y}
              r="3"
              tabIndex={0}
              role="img"
              aria-label={`${point.dateLabel}, ${point.valueLabel}`}
              onFocus={() => setActive(index)}
              onBlur={() => setActive((current) => (current === index ? null : current))}
              onKeyDown={(event: KeyboardEvent<SVGCircleElement>) => {
                if (event.key === "Escape") setActive(null);
              }}
            />
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
          <rect
            aria-hidden="true"
            className="research-chart-hit"
            x={chart.plot.x}
            y={chart.plot.y}
            width={chart.plot.width}
            height={chart.plot.height}
            onPointerDown={selectFromPointer}
            onPointerMove={selectFromPointer}
            onPointerLeave={(event) => {
              if (event.pointerType === "mouse") setActive(null);
            }}
          />
        </svg>
        {selected && tooltip ? (
          <div className="macro-chart-tooltip" style={tooltip} role="status">
            <p>{selected.dateLabel}</p>
            <p>{selected.valueLabel}</p>
          </div>
        ) : null}
      </div>
      <figcaption className="research-chart-caption">{chart.caption}</figcaption>
    </figure>
  );
}

function tooltipStyle(
  x: number,
  y: number,
  width: number,
  height: number,
): { left: string; top: string; transform: string } {
  const left = (x / width) * 100;
  const transform =
    left > 72 ? "translate(-100%, -120%)" : left < 28 ? "translate(0, -120%)" : "translate(-50%, -120%)";
  return { left: `${left}%`, top: `${(y / height) * 100}%`, transform };
}
