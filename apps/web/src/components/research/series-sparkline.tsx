export type SparklineMark =
  | { kind: "line"; points: string }
  | { kind: "point"; cx: number; cy: number };

type Props = {
  marks: SparklineMark[];
  label: string;
  caption: string;
  width: number;
  height: number;
  testId?: string;
};

export function SeriesSparkline({ marks, label, caption, width, height, testId }: Props) {
  if (marks.length === 0) {
    return (
      <p className="research-body" data-testid="research-chart-empty">
        Chart unavailable — insufficient observation points.
      </p>
    );
  }

  return (
    <figure>
      <svg
        className="research-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${label}. ${caption}`}
        data-testid={testId}
      >
        {marks.map((mark, index) =>
          mark.kind === "line" ? (
            <polyline key={index} className="research-chart-line" points={mark.points} />
          ) : (
            <circle key={index} className="research-chart-point" cx={mark.cx} cy={mark.cy} r="2.5" />
          ),
        )}
      </svg>
      <figcaption className="research-chart-caption">{caption}</figcaption>
    </figure>
  );
}
