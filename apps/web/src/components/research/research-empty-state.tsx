type Props = {
  reason: "missing" | "invalid" | "unauthorized";
};

export function ResearchEmptyState({ reason }: Props) {
  const message =
    reason === "unauthorized"
      ? "Founder research is not available in this session."
      : reason === "invalid"
        ? "The research insight file could not be validated. Run the local research preview pipeline to regenerate it."
        : "No founder research insight is available yet. Run npm run research:preview after starting local Supabase.";

  return (
    <div className="research-banner" data-testid="research-empty-state">
      <h2 className="research-headline">Macro intelligence pending</h2>
      <p className="research-body">{message}</p>
      <p className="research-meta">
        Public publication remains blocked until evidence requirements are met.
      </p>
    </div>
  );
}
