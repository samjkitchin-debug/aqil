import type { BrokerHoldingView } from "../saxo/portfolio.ts";

/** Stable identity for a Saxo snapshot line, aligned with net-position grouping in portfolio normalisation. */
export function brokerHoldingKey(
  holding: Pick<BrokerHoldingView, "accountLabel" | "symbol" | "assetType" | "uic">,
): string {
  return `${holding.uic ?? "none"}|${holding.assetType ?? ""}|${holding.symbol ?? ""}|${holding.accountLabel}`;
}
