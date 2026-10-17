import type { CompanyFilingSummary, ForwardHorizonV1 } from "@/lib/forward/types";

type Props = {
  bundle: ForwardHorizonV1;
};

function label(filing: CompanyFilingSummary): string {
  if (filing.is_fixture) {
    return "EDGAR fixture (completed filing)";
  }
  if (filing.evidence_class === "verified_announcement") {
    return "EDGAR completed filing";
  }
  return "Filing record";
}

export function ForwardCompanyFilings({ bundle }: Props) {
  const filings = bundle.company_filings ?? [];
  if (filings.length === 0) {
    return (
      <p className="research-body">
        No completed SEC filing history is loaded. Collect EDGAR submissions to populate issuer
        fundamentals context.
      </p>
    );
  }

  return (
    <section data-testid="forward-company-filings" className="research-banner">
      <h2 className="research-section-title">Completed SEC filings (history)</h2>
      <p className="research-meta">
        Observed filings only — not a forward earnings calendar. Dates are acceptance times from
        EDGAR.
      </p>
      <ul className="forward-horizon-list">
        {filings.map((filing) => (
          <li key={filing.event_id} className="forward-horizon-item">
            <p className="forward-horizon-title">{filing.title}</p>
            <p className="research-meta">
              {label(filing)}
              {filing.form ? ` · ${filing.form}` : ""}
              {filing.reported_period_end
                ? ` · Period end ${filing.reported_period_end}`
                : ""}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
