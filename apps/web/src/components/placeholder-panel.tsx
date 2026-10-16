import { ReadingContainer } from "@/components/ui/reading-container";

type PlaceholderPanelProps = {
  heading: string;
  body: string;
};

export function PlaceholderPanel({ heading, body }: PlaceholderPanelProps) {
  return (
    <ReadingContainer>
      <section
        className="rounded-lg border border-border bg-surface-subtle p-[var(--space-6)] shadow-card"
        aria-labelledby="placeholder-heading"
      >
        <h1 id="placeholder-heading" className="aq-panel-heading font-semibold text-foreground">
          {heading}
        </h1>
        <p className="mt-[var(--space-3)] max-w-prose text-muted">{body}</p>
        <p className="aq-panel-note mt-[var(--space-6)] text-muted">
          This is scaffolding only. No investment research or financial data is shown here yet.
        </p>
      </section>
    </ReadingContainer>
  );
}
