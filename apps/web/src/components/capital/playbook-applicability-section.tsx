import { loadInvestmentPlaybooks } from "@/lib/playbook/load-investment-playbooks";
import {
  PLAYBOOK_APPLICABILITY_INTRO,
  assessPlaybookApplicability,
  type PlaybookInputCheck,
} from "@/lib/playbook/playbook-applicability";
import { playbookApprovalLabel, playbookKindLabel } from "@/lib/playbook/investment-playbooks";
import type { Target } from "@/lib/wealth/allocation";

function presenceSentence(input: PlaybookInputCheck): string {
  const detail = input.note ? `${input.label}. ${input.note}` : input.label;
  if (input.presence === "present") return `Present. ${detail}`;
  if (input.presence === "not_required") return `Not required. ${input.label}`;
  return `Missing. ${detail}`;
}

function kindLine(kind: "structural" | "disputed_market_timing"): string {
  if (kind === "structural") return playbookKindLabel(kind);
  return `${playbookKindLabel(kind)}. Not a structural principle`;
}

export function PlaybookApplicabilitySection({ targets }: { targets: readonly Target[] | null }) {
  const rows = assessPlaybookApplicability(loadInvestmentPlaybooks(), { targets });
  return (
    <section
      className="grid gap-[var(--space-3)]"
      data-testid="deploy-playbook-inputs"
      aria-labelledby="deploy-playbook-inputs-heading"
    >
      <h2 id="deploy-playbook-inputs-heading" className="text-foreground">
        Playbook inputs
      </h2>
      <p className="text-muted">{PLAYBOOK_APPLICABILITY_INTRO}</p>
      {rows.map((row) => (
        <article
          key={row.id}
          className="grid gap-[var(--space-2)] border border-border p-[var(--space-3)]"
          data-testid={`playbook-inputs-${row.id}`}
          data-inputs={row.requiredInputsPresent ? "present" : "missing"}
          data-approval={row.approvalStatus}
        >
          <h3 className="text-foreground">{row.title}</h3>
          <p className="text-muted">
            {kindLine(row.kind)}. {playbookApprovalLabel(row.approvalStatus)}.
          </p>
          <p>{row.summary}</p>
          <ul className="grid gap-[var(--space-2)]">
            {row.inputs.map((item) => (
              <li key={item.label}>{presenceSentence(item)}</li>
            ))}
          </ul>
          <p className="text-muted">Policy constraints stay in force.</p>
          <ul className="grid gap-[var(--space-2)]">
            {row.constraints.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      ))}
    </section>
  );
}
