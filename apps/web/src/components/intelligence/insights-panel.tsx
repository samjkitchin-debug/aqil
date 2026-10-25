import Link from "next/link";

const FUTURE_PARTS = [
  ["Finding", "A concise statement that cites a stored model output."],
  ["Evidence", "The observations and methodologies the finding uses."],
  ["Change", "What differs from an earlier stored evaluation."],
  ["Agreement and disagreement", "Which independent methods support or conflict with the finding."],
  ["Uncertainty", "What the evidence does not establish."],
  ["What to watch", "Later observations that the stored analysis says would change the conclusion."],
] as const;

export function InsightsPanel() {
  return (
    <article className="intel-insight" data-testid="insights-limited">
      <h2 className="intel-region-title">Strategic synthesis</h2>
      <p className="research-body">
        No cross-method finding is published. Dashboard shows stored observations. Methodologies shows each model and whether its calculated output may be displayed. A finding on this page would have to be written from publication-eligible model results. Those results are not available, so this page does not state a view on growth, inflation, recession risk or markets.
      </p>
      <h3 className="intel-section-title">What a finding will contain</h3>
      <p className="research-meta">These headings are the structure for a later finding. They are not findings.</p>
      <ol className="intel-insight-parts">
        {FUTURE_PARTS.map(([title, detail]) => (
          <li key={title}>
            <span className="intel-insight-part">{title}.</span> {detail}
          </li>
        ))}
      </ol>
      <p className="research-meta">
        <Link href="/conditions" prefetch={false}>
          Dashboard
        </Link>
        {" · "}
        <Link href="/intelligence/methodologies" prefetch={false}>
          Methodologies
        </Link>
      </p>
    </article>
  );
}
