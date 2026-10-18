import { StatusLine } from "@/components/ui/status-line";

type Props = {
  reason: "missing" | "invalid" | "unauthorized";
};

export function ResearchEmptyState({ reason }: Props) {
  const message =
    reason === "unauthorized"
      ? "Private research is available only to an explicitly authorised account."
      : reason === "invalid"
        ? "The research insight file could not be validated. Run the local research preview pipeline to regenerate it."
        : "No founder research insight is available yet. Run npm run research:preview after starting local Supabase.";

  return (
    <div className="research-banner" data-testid="research-empty-state">
      <h2 className="research-headline">Macro intelligence pending</h2>
      <p className="research-body">{message}</p>
      <StatusLine tone="limitation">
        Public publication remains blocked until evidence requirements are met.
      </StatusLine>
    </div>
  );
}
