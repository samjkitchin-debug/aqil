import { loadInvestmentPlaybooks } from "@/lib/playbook/load-investment-playbooks";
import {
  PLAYBOOK_REGISTER_NOTE,
  PLAYBOOK_TRADE_NOTICE,
  playbookApprovalLabel,
  playbookKindLabel,
  type InvestmentPlaybook,
  type PlaybookCitation,
  type PlaybookKind,
} from "@/lib/playbook/investment-playbooks";

export function InvestmentPlaybooks() {
  const playbooks = loadInvestmentPlaybooks();
  const structural = playbooks.filter((playbook) => playbook.kind === "structural");
  const disputed = playbooks.filter((playbook) => playbook.kind === "disputed_market_timing");

  return (
    <div data-testid="learn-playbooks">
      <section className="research-banner research-banner--preview" aria-labelledby="learn-playbooks-intro">
        <p className="research-meta">Research register</p>
        <h2 className="research-headline" id="learn-playbooks-intro">
          Investment playbooks
        </h2>
        <p className="research-body">{PLAYBOOK_TRADE_NOTICE}</p>
        <p className="research-body mt-[var(--space-4)]">{PLAYBOOK_REGISTER_NOTE}</p>
      </section>

      <PlaybookGroup
        headingId="learn-playbooks-structural"
        title="Structural principles"
        intro="These entries are structural principles. Proposed means proposed for later review."
        playbooks={structural}
        empty="No structural principle is in this version of the register."
      />
      <PlaybookGroup
        headingId="learn-playbooks-timing"
        title="Disputed market-timing"
        intro="These entries are disputed market-timing. They are not structural principles, and they are not approved."
        playbooks={disputed}
        empty="No disputed market-timing entry is in this version of the register."
      />
    </div>
  );
}

function PlaybookGroup({
  headingId,
  title,
  intro,
  playbooks,
  empty,
}: {
  headingId: string;
  title: string;
  intro: string;
  playbooks: readonly InvestmentPlaybook[];
  empty: string;
}) {
  return (
    <section aria-labelledby={headingId}>
      <h2 className="research-section-title" id={headingId}>
        {title}
      </h2>
      <p className="research-body">{intro}</p>
      {playbooks.length === 0 ? (
        <p className="research-body mt-[var(--space-4)]">{empty}</p>
      ) : (
        playbooks.map((playbook) => <PlaybookCard key={playbook.id} playbook={playbook} />)
      )}
    </section>
  );
}

function PlaybookCard({ playbook }: { playbook: InvestmentPlaybook }) {
  const titleId = `learn-playbook-${playbook.id}-title`;
  return (
    <section
      className="research-banner"
      data-testid={`learn-playbook-${playbook.id}`}
      data-kind={playbook.kind}
      data-approval={playbook.approvalStatus}
      aria-labelledby={titleId}
    >
      <p className="research-meta">{kindLine(playbook.kind)}</p>
      <h3 className="research-headline" id={titleId}>
        {playbook.title}
      </h3>
      <p className="research-body">{PLAYBOOK_TRADE_NOTICE}</p>
      <dl className="research-body mt-[var(--space-4)] grid gap-[var(--space-2)]">
        <TextDetail title="Decision question" value={playbook.decisionQuestion} />
        <ListDetail title="Portfolio data required" items={playbook.requiredPortfolioData} />
        <ListDetail title="Market or economic data" items={playbook.requiredMarketOrEconomicData} />
        <ListDetail title="Policy constraints" items={playbook.investorPolicyConstraints} />
        <CitationDetail citations={playbook.evidence} />
        <ListDetail title="Limits of the evidence" items={playbook.evidenceLimitations} />
        <ListDetail title="Applicable conditions" items={playbook.applicableConditions} />
        <ListDetail title="Contradictory conditions" items={playbook.contradictoryConditions} />
        <ListDetail title="Implementation alternatives" items={playbook.implementationAlternatives} />
        <ListDetail title="Expected trade-offs" items={playbook.expectedTradeOffs} />
        <ListDetail title="How an outcome would be judged" items={playbook.outcomeEvaluationCriteria} />
      </dl>
      <p className="research-meta">
        Approval status: {playbookApprovalLabel(playbook.approvalStatus)}. Version {playbook.version}.
        Register id: {playbook.id}.
      </p>
    </section>
  );
}

function kindLine(kind: PlaybookKind): string {
  if (kind === "structural") return playbookKindLabel(kind);
  return `${playbookKindLabel(kind)}. Not a structural principle.`;
}

function TextDetail({ title, value }: { title: string; value: string }) {
  return (
    <div>
      <dt>{title}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function ListDetail({ title, items }: { title: string; items: readonly string[] }) {
  return (
    <div>
      <dt>{title}</dt>
      <dd>
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </dd>
    </div>
  );
}

function CitationDetail({ citations }: { citations: readonly PlaybookCitation[] }) {
  return (
    <div>
      <dt>Evidence</dt>
      <dd>
        <ul>
          {citations.map((citation) => (
            <li key={`${citation.locator}:${citation.year}`}>
              {citation.authors} ({citation.year}). {citation.title}.{" "}
              <CitationLocator locator={citation.locator} />
            </li>
          ))}
        </ul>
      </dd>
    </div>
  );
}

function CitationLocator({ locator }: { locator: string }) {
  if (!locator.startsWith("https://")) return locator;
  return (
    <a href={locator} rel="noopener noreferrer">
      {locator}
    </a>
  );
}
