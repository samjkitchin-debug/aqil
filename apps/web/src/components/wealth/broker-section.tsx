import { BrokerPanel } from "@/components/wealth/broker-panel";
import type { SaxoLinkState } from "@/lib/saxo/link-state";
import type { BrokerPortfolioView } from "@/lib/saxo/portfolio";
import { buildWealthPanel } from "@/lib/wealth/panel";

const SAXO_ERRORS: Record<string, string> = {
  saxo_unavailable: "Saxo is not available from this address.",
  saxo_denied: "Saxo authorisation was cancelled.",
  saxo_state: "That Saxo return did not match this sign-in. Connect again.",
  saxo_user: "This Saxo connection belongs to a different Aqil sign-in.",
  saxo_exchange: "Saxo did not complete the connection.",
  no_session: "Connect Saxo before refreshing.",
  refresh_failed: "The Saxo connection needs to be renewed.",
  source_error: "Saxo did not return a complete portfolio. The last good snapshot is unchanged.",
  incomplete_kept: "This refresh did not replace the stored snapshot.",
};

export function saxoErrorMessage(error: string | null): string | null {
  if (!error) return null;
  return SAXO_ERRORS[error] ?? null;
}

export function BrokerSection({
  broker,
  error,
  connectEnabled,
  heading,
  link = "unknown",
}: {
  broker: BrokerPortfolioView | null;
  error: string | null;
  connectEnabled: boolean;
  heading: "h1" | "h2";
  link?: SaxoLinkState;
}) {
  const message = saxoErrorMessage(error);
  const Title = heading;
  if (!broker) {
    return (
      <section className="aq-wealth">
        {heading === "h1" ? <Title className="aq-wealth-title">My wealth</Title> : null}
        {message ? <p>{message}</p> : null}
        <p>
          <a className="aq-quiet-link" href="/my-wealth/deploy">
            Deploy capital
          </a>
        </p>
        {connectEnabled ? (
          <p>
            <a className="aq-button" href="/auth/saxo?environment=live">
              Connect Saxo
            </a>
          </p>
        ) : (
          <p className="aq-status aq-status--meta">A Saxo connection is not available on this site yet.</p>
        )}
      </section>
    );
  }

  const panel = buildWealthPanel({ broker, link, error });
  return <BrokerPanel panel={panel} notice={message} connectEnabled={connectEnabled} heading={heading} />;
}
