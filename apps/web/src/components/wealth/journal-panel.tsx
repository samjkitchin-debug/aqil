import {
  applyJournalPreview,
  discardJournalPreview,
  saveJournalEntry,
  saveJournalPreview,
  saveSuppliedPrice,
  saveSuppliedRate,
} from "@/lib/wealth/journal-actions";
import { CSV_MAX_CHARS, JOURNAL_CSV_HEADER } from "@/lib/wealth/journal-csv";
import { MANUAL_EVENT_TYPES, type ManualEventType } from "@/lib/wealth/journal-entry";
import type { SolvedRate } from "@/lib/wealth/journal-returns";
import type { JournalSummary } from "@/lib/wealth/journal-workflow";
import type { MoneyStatus } from "@/lib/wealth/journal";
import { formatMinor } from "@/lib/wealth/money";
import type { SuppliedPrice, SuppliedRate } from "@/lib/wealth/journal-valuation";

const EVENT_LABELS: Record<ManualEventType, string> = {
  deposit: "Deposit",
  withdrawal: "Withdrawal",
  buy: "Buy",
  sell: "Sell",
  fee: "Fee",
  distribution: "Distribution",
  split: "Split",
};

const ERRORS: Record<string, string> = {
  currency: "The currency is invalid or does not match the holding.",
  conflict: "That entry was already saved with different details.",
  missing: "A required field is missing.",
  amount: "The amount or quantity is invalid.",
  rejected: "That entry does not fit the journal.",
  unreadable: "The journal could not be read.",
  price: "The price could not be saved.",
  price_conflict: "A different price is already recorded for that date.",
  rate: "The exchange rate could not be saved.",
  rate_conflict: "A different exchange rate is already recorded for that date.",
  preview: "The preview could not be saved.",
};

const fieldClass = "mt-[var(--space-1)] block w-full border border-border bg-surface p-[var(--space-2)]";

function formatUkDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  if (!year || !month || !day) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

function moneyLabel(value: MoneyStatus): string {
  if (value.status !== "available") return "Unavailable";
  return formatMinor(value.amountMinor, value.currency);
}

function percentLabel(rate: string): string {
  const negative = rate.startsWith("-");
  const unsigned = negative ? rate.slice(1) : rate;
  const [whole, fraction = ""] = unsigned.split(".");
  const frac = fraction.padEnd(8, "0").slice(0, 8);
  const percentWhole = `${whole}${frac.slice(0, 2)}`.replace(/^0+(?=\d)/, "");
  const percentFrac = frac.slice(2).replace(/0+$/, "").padEnd(2, "0");
  return `${negative ? "-" : ""}${percentWhole}.${percentFrac}%`;
}

function returnLabel(value: SolvedRate): string {
  if (value.status !== "available") return value.reason;
  return `${percentLabel(value.rate)} from ${formatUkDate(value.from)} to ${formatUkDate(value.to)}.`;
}

function AsOfField({ asOf }: { asOf: string }) {
  return <input type="hidden" name="as_of_view" value={asOf} />;
}

export function JournalPanel({
  summary,
  prices,
  rates,
  error,
  draftId,
}: {
  summary: JournalSummary;
  prices: readonly SuppliedPrice[];
  rates: readonly SuppliedRate[];
  error: string | null;
  draftId: string;
}) {
  const message = error ? ERRORS[error] : null;
  const preview = summary.preview;
  return (
    <div className="grid gap-[var(--space-6)]" data-testid="investment-journal">
      <section className="grid gap-[var(--space-3)]">
        <p>
          <a className="aq-quiet-link" href="/my-wealth">
            My wealth
          </a>
        </p>
        <p className="text-muted">
          Record deposits, withdrawals, buys, sells, fees, distributions and splits yourself. A market value uses only a price you supply for that date. Summary amounts use SGD.
        </p>
        {message ? <p className="text-foreground">{message}</p> : null}
        <form action="/my-wealth/journal" method="get" className="flex flex-wrap items-end gap-[var(--space-3)]">
          <label className="text-sm text-muted">
            As of
            <input type="date" name="asOf" defaultValue={summary.asOf} className={fieldClass} />
          </label>
          <button type="submit" className="aq-button">
            Show this date
          </button>
        </form>
      </section>

      <section className="grid gap-[var(--space-3)]">
        <h2 className="text-foreground">Position on {formatUkDate(summary.asOf)}</h2>
        <dl className="grid gap-[var(--space-3)]">
          <div>
            <dt className="text-sm text-muted">Investment value</dt>
            <dd>
              {summary.market.status === "available"
                ? formatMinor(summary.market.amountMinor, summary.market.currency)
                : "Unavailable"}
            </dd>
            <dd className="text-sm text-muted">
              {summary.market.status === "available" && summary.market.source === "supplied"
                ? `Supplied price as of ${formatUkDate(summary.market.asOf)}.`
                : summary.market.status === "available"
                  ? "No open holding, so the investment value is zero."
                  : summary.market.reason}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Portfolio total</dt>
            <dd className="aq-num">{moneyLabel(summary.total)}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Realised profit</dt>
            <dd className="aq-num">{moneyLabel(summary.realisedProfit)}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Unrealised gain</dt>
            <dd className="aq-num">{moneyLabel(summary.unrealisedGain)}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Net contributions</dt>
            <dd className="aq-num">{moneyLabel(summary.netContributions)}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Money-weighted return</dt>
            <dd>{returnLabel(summary.xirr)}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Time-weighted return</dt>
            <dd>{returnLabel(summary.twr)}</dd>
          </div>
        </dl>
        {summary.replay.positions.length === 0 ? (
          <p className="text-muted">No open holding.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Open holdings from the journal</caption>
              <thead>
                <tr className="text-muted">
                  <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Account</th>
                  <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Instrument</th>
                  <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Quantity</th>
                  <th className="py-[var(--space-2)] font-medium">Cost</th>
                </tr>
              </thead>
              <tbody>
                {summary.replay.positions.map((position) => (
                  <tr key={`${position.accountId}-${position.instrumentId}`} className="border-t border-border">
                    <td className="py-[var(--space-2)] pr-[var(--space-3)]">{position.accountId}</td>
                    <td className="py-[var(--space-2)] pr-[var(--space-3)]">{position.instrumentId}</td>
                    <td className="py-[var(--space-2)] pr-[var(--space-3)] aq-num">{position.quantity}</td>
                    <td className="py-[var(--space-2)] aq-num">
                      {position.costMinor === null ? "Unavailable" : formatMinor(position.costMinor, position.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {prices.length === 0 ? (
          <p className="text-muted">No price has been supplied.</p>
        ) : (
          <ul className="grid gap-[var(--space-1)] text-sm">
            {prices.map((price) => (
              <li key={`${price.instrumentId}-${price.currency}-${price.asOf}`}>
                {price.instrumentId}: {formatMinor(price.unitPriceMinor, price.currency)} supplied as of {formatUkDate(price.asOf)}.
              </li>
            ))}
          </ul>
        )}
        {rates.length === 0 ? (
          <p className="text-muted">No exchange rate has been supplied.</p>
        ) : (
          <ul className="grid gap-[var(--space-1)] text-sm">
            {rates.map((rate) => (
              <li key={`${rate.baseCurrency}-${rate.quoteCurrency}-${rate.asOf}`}>
                {rate.baseCurrency} to {rate.quoteCurrency}: {rate.rate} supplied as of {formatUkDate(rate.asOf)}.
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid max-w-prose gap-[var(--space-3)]">
        <h2 className="text-foreground">Record an entry</h2>
        <p className="text-sm text-muted">
          Enter the cash amount as a positive number. A buy, a fee or a withdrawal is saved as cash leaving the account. If you enter both a cash amount and a unit price and they differ, the cash amount is saved and the unit price is not. A split needs only the instrument and the ratio.
        </p>
        <form action={saveJournalEntry} className="grid gap-[var(--space-3)]" autoComplete="off">
          <AsOfField asOf={summary.asOf} />
          <input type="hidden" name="draft_id" value={draftId} />
          <label className="text-sm text-muted">
            Entry type
            <select name="event_type" defaultValue="deposit" className={fieldClass}>
              {MANUAL_EVENT_TYPES.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {EVENT_LABELS[eventType]}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-muted">
            Date
            <input type="date" name="occurred_on" required defaultValue={summary.asOf} className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Account
            <input name="account_id" required autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Currency
            <input name="currency" required defaultValue="SGD" autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Cash amount
            <input name="cash_amount" inputMode="decimal" autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Instrument
            <input name="instrument_id" autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Quantity
            <input name="quantity" inputMode="decimal" autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Unit price
            <input name="unit_price" inputMode="decimal" autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Split numerator
            <input name="split_numerator" inputMode="numeric" autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Split denominator
            <input name="split_denominator" inputMode="numeric" autoComplete="off" className={fieldClass} />
          </label>
          <button type="submit" className="aq-button">
            Save entry
          </button>
        </form>
      </section>

      <section className="grid max-w-prose gap-[var(--space-3)]">
        <h2 className="text-foreground">Supplied price</h2>
        <p className="text-sm text-muted">
          Investment value is shown only when a price was supplied for that date. A missing price is left unavailable.
        </p>
        <form action={saveSuppliedPrice} className="grid gap-[var(--space-3)]" autoComplete="off">
          <AsOfField asOf={summary.asOf} />
          <label className="text-sm text-muted">
            Instrument
            <input name="instrument_id" required autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Currency
            <input name="currency" required defaultValue="SGD" autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Unit price
            <input name="unit_price" required inputMode="decimal" autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Date
            <input type="date" name="as_of" required defaultValue={summary.asOf} className={fieldClass} />
          </label>
          <button type="submit" className="aq-button">
            Save price
          </button>
        </form>
      </section>

      <section className="grid max-w-prose gap-[var(--space-3)]">
        <h2 className="text-foreground">Supplied exchange rate</h2>
        <p className="text-sm text-muted">
          How many Singapore dollars one unit of this currency bought on that date. A missing rate is left unavailable.
        </p>
        <form action={saveSuppliedRate} className="grid gap-[var(--space-3)]" autoComplete="off">
          <AsOfField asOf={summary.asOf} />
          <input type="hidden" name="quote_currency" value="SGD" />
          <label className="text-sm text-muted">
            Base currency
            <input name="base_currency" required autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Rate
            <input name="rate" required inputMode="decimal" autoComplete="off" className={fieldClass} />
          </label>
          <label className="text-sm text-muted">
            Date
            <input type="date" name="as_of" required defaultValue={summary.asOf} className={fieldClass} />
          </label>
          <button type="submit" className="aq-button">
            Save exchange rate
          </button>
        </form>
      </section>

      <section className="grid max-w-prose gap-[var(--space-3)]">
        <h2 className="text-foreground">Statement preview</h2>
        <p className="text-sm text-muted">
          Paste a CSV to preview it. Matching idempotency keys are skipped. Ambiguous rows stay out of the journal. Nothing is read from a broker archive.
        </p>
        <p className="text-sm text-muted">The first row must be: {JOURNAL_CSV_HEADER}</p>
        <form action={saveJournalPreview} className="grid gap-[var(--space-3)]" autoComplete="off">
          <AsOfField asOf={summary.asOf} />
          <label className="text-sm text-muted">
            CSV
            <textarea name="csv" required maxLength={CSV_MAX_CHARS} rows={6} className={fieldClass} />
          </label>
          <button type="submit" className="aq-button">
            Preview CSV
          </button>
        </form>
        {preview ? (
          <div className="grid gap-[var(--space-3)]">
            {preview.recognised ? (
              <p>
                {preview.accepted.length === 1 ? "1 row is ready to add." : `${preview.accepted.length} rows are ready to add.`}{" "}
                {preview.duplicates.length === 1 ? "1 is already recorded." : `${preview.duplicates.length} are already recorded.`}{" "}
                {preview.held.length === 1 ? "1 is held for review." : `${preview.held.length} are held for review.`}
              </p>
            ) : (
              <p>The file was not recognised. Nothing was imported.</p>
            )}
            {preview.held.length > 0 ? (
              <ul className="grid gap-[var(--space-1)] text-sm">
                {preview.held.map((row) => (
                  <li key={`${row.line}-${row.reason}`}>
                    Line {row.line}. {row.reason}
                  </li>
                ))}
              </ul>
            ) : null}
            {preview.replay ? (
              <p className="text-sm text-muted">
                Preview holdings:{" "}
                {preview.replay.positions.length === 0
                  ? "no open holding."
                  : `${preview.replay.positions.map((position) => `${position.instrumentId} ${position.quantity}`).join(", ")}.`}
              </p>
            ) : null}
            <div className="flex flex-wrap gap-[var(--space-3)]">
              {preview.recognised && preview.accepted.length > 0 ? (
                <form action={applyJournalPreview}>
                  <AsOfField asOf={summary.asOf} />
                  <button type="submit" className="aq-button">
                    Add accepted rows
                  </button>
                </form>
              ) : null}
              <form action={discardJournalPreview}>
                <AsOfField asOf={summary.asOf} />
                <button type="submit" className="aq-button">
                  Discard preview
                </button>
              </form>
            </div>
          </div>
        ) : null}
      </section>

      <section className="grid gap-[var(--space-3)]">
        <h2 className="text-foreground">Entries</h2>
        {summary.events.length === 0 ? (
          <p className="text-muted">No entries yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Journal entries</caption>
              <thead>
                <tr className="text-muted">
                  <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Date</th>
                  <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Type</th>
                  <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Account</th>
                  <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Instrument</th>
                  <th className="py-[var(--space-2)] pr-[var(--space-3)] font-medium">Quantity</th>
                  <th className="py-[var(--space-2)] font-medium">Cash</th>
                </tr>
              </thead>
              <tbody>
                {summary.events.map((event) => (
                  <tr key={event.eventId} className="border-t border-border">
                    <td className="py-[var(--space-2)] pr-[var(--space-3)]">{formatUkDate(event.occurredOn)}</td>
                    <td className="py-[var(--space-2)] pr-[var(--space-3)]">
                      {EVENT_LABELS[event.eventType as ManualEventType] ?? event.eventType}
                    </td>
                    <td className="py-[var(--space-2)] pr-[var(--space-3)]">{event.accountId}</td>
                    <td className="py-[var(--space-2)] pr-[var(--space-3)]">{event.instrumentId ?? ""}</td>
                    <td className="py-[var(--space-2)] pr-[var(--space-3)] aq-num">
                      {event.eventType === "split"
                        ? `${event.splitNumerator ?? ""} for ${event.splitDenominator ?? ""}`
                        : (event.quantity ?? "")}
                    </td>
                    <td className="py-[var(--space-2)] aq-num">
                      {event.cashAmountMinor === null ? "" : formatMinor(event.cashAmountMinor, event.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
