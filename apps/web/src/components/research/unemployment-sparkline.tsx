import type { ChartPoint } from "@/lib/research/types";

import { SeriesSparkline, type SparklineMark } from "@/components/research/series-sparkline";

type Props = {
  points: ChartPoint[];
  label: string;
};

const WIDTH = 320;
const HEIGHT = 120;
const PADDING = 8;

function sequenceMarks(points: ChartPoint[]): SparklineMark[] {
  if (points.length < 2) return [];
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const coords = points.map((point, index) => {
    const x = PADDING + (index / (points.length - 1)) * (WIDTH - PADDING * 2);
    const y = HEIGHT - PADDING - ((point.value - min) / span) * (HEIGHT - PADDING * 2);
    return `${x},${y}`;
  });
  return [{ kind: "line", points: coords.join(" ") }];
}

export function UnemploymentSparkline({ points, label }: Props) {
  return (
    <SeriesSparkline
      marks={sequenceMarks(points)}
      label={label}
      caption={`${label} (latest ${points.length} months, percent)`}
      width={WIDTH}
      height={HEIGHT}
      testId="research-unemployment-chart"
    />
  );
}
