import { ReadingContainer } from "@/components/ui/reading-container";

type PlaceholderPanelProps = {
  body: string;
};

export function PlaceholderPanel({ body }: PlaceholderPanelProps) {
  return (
    <ReadingContainer>
      <section className="max-w-prose" aria-labelledby="page-title">
        <p className="text-muted">{body}</p>
        <p className="aq-panel-note mt-[var(--space-6)] text-muted">
          This is scaffolding only. No investment research or financial data is shown here yet.
        </p>
      </section>
    </ReadingContainer>
  );
}
