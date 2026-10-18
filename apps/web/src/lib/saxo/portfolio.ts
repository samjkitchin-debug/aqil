import type { SaxoPerformanceState } from "./performance.ts";
import type { SaxoEnvironment } from "./sim-guard.ts";

export type BrokerAccountView = {
  label: string;
  currency: string | null;
  cashBalance: string | null;
  brokerReportedValue: string | null;
  extendedReportedValue: string | null;
  buyingPower: string | null;
};

export type BrokerHoldingView = {
  accountLabel: string;
  name: string;
  symbol: string | null;
  assetType: string | null;
  uic: number | null;
  quantity: string | null;
  currency: string | null;
  tradingCurrency: string | null;
  price: string | null;
  marketValue: string | null;
  valueBasis: "live" | "broker-market-value" | null;
  profitLoss: string | null;
  lotCount: number | null;
  classification: "unclassified";
};

export type BrokerCoverage = {
  accounts: boolean;
  balances: boolean;
  netPositions: boolean;
  livePrices: boolean;
};

export type BrokerPortfolioView = {
  environment: SaxoEnvironment;
  retrievedAt: string;
  coverage: BrokerCoverage;
  accounts: BrokerAccountView[];
  holdings: BrokerHoldingView[];
  limitations: string[];
  performance?: SaxoPerformanceState;
};

type AccountIdentity = { key: string; id: string | null; label: string; currency: string | null };

export function formatReportedAmount(value: string | null, currency: string | null): string {
  if (value === null) return "Unavailable";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "Unavailable";
  const formatted = new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
  return currency ? `${formatted} ${currency}` : formatted;
}

export function formatQuantity(value: string | null): string {
  if (value === null) return "Unavailable";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "Unavailable";
  return new Intl.NumberFormat("en-GB", { maximumFractionDigits: 8 }).format(amount);
}

export function formatRetrievedAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Singapore",
  }).format(date);
}

export function repairStoredPortfolio(portfolio: BrokerPortfolioView): BrokerPortfolioView {
  if (portfolio.coverage) return portfolio;
  return {
    ...portfolio,
    coverage: {
      accounts: portfolio.accounts.length > 0,
      balances: portfolio.accounts.some((account) => account.cashBalance !== null || account.brokerReportedValue !== null),
      netPositions: false,
      livePrices: false,
    },
    holdings: portfolio.holdings.map((holding) => ({
      ...holding,
      price: holding.price === "0" ? null : holding.price,
      marketValue: holding.marketValue === "0" ? null : holding.marketValue,
      valueBasis: null,
      profitLoss: holding.profitLoss ?? null,
      lotCount: holding.lotCount ?? null,
      uic: holding.uic ?? null,
      tradingCurrency: holding.tradingCurrency ?? null,
    })),
    limitations: [
      ...portfolio.limitations,
      "This stored snapshot treated a closed-market zero as a price. Refresh Saxo to replace it.",
    ],
  };
}

/** Maps only values Saxo returned. Cash available for trading is not treated as cash. */
export function normaliseSaxoPortfolio(input: {
  environment: SaxoEnvironment;
  retrievedAt: string;
  pagesComplete: boolean;
  accountsBody: unknown;
  clientBalance: unknown;
  accountBalances: unknown[];
  positionsBody: unknown;
  netPositionsBody?: unknown;
}): BrokerPortfolioView {
  const identities = accountIdentities(input.accountsBody);
  const limitations: string[] = [];
  if (!input.pagesComplete) limitations.push("Saxo did not return every page, so this is not the full list.");

  const balanceRecords = input.accountBalances.map(record).filter((row): row is Record<string, unknown> => row !== null);
  const clientRecord = record(input.clientBalance);
  const singleAccount = identities.length === 1;
  const accountViews = identities.map((identity) => {
    const matched = findBalance(balanceRecords, identity);
    const balance =
      matched ?? (singleAccount && balanceRecords.length === 1 ? balanceRecords[0] : null) ??
      (singleAccount ? clientRecord : null);
    const currency = text(balance, "Currency") ?? text(clientRecord, "Currency") ?? identity.currency;
    return {
      label: identity.label,
      currency,
      cashBalance: numberText(balance, "CashBalance") ?? (singleAccount ? numberText(clientRecord, "CashBalance") : null),
      brokerReportedValue:
        numberText(balance, "TotalValue") ?? (singleAccount ? numberText(clientRecord, "TotalValue") : null),
      extendedReportedValue:
        numberText(record(balance?.ExtendedTradingHoursData), "TotalValue") ??
        (singleAccount ? numberText(record(clientRecord?.ExtendedTradingHoursData), "TotalValue") : null),
      buyingPower: numberText(balance, "CashAvailableForTrading"),
    };
  });

  const clientTotal = numberText(record(input.clientBalance), "TotalValue");
  const accountTotals = accountViews.some((account) => account.brokerReportedValue !== null);
  if (clientTotal && accountTotals) {
    limitations.push("Saxo also returned a client-level total. It is not added to the account values.");
  } else if (clientTotal && accountViews.length === 0) {
    accountViews.push({
      label: "Saxo client",
      currency: text(clientRecord, "Currency"),
      cashBalance: numberText(clientRecord, "CashBalance"),
      brokerReportedValue: clientTotal,
      extendedReportedValue: numberText(record(clientRecord?.ExtendedTradingHoursData), "TotalValue"),
      buyingPower: numberText(clientRecord, "CashAvailableForTrading"),
    });
  }

  const valueCurrency = accountViews.find((account) => account.currency)?.currency ?? null;
  const collateral = collateralByUic([...balanceRecords, clientRecord]);
  const netHoldings = attachCollateral(holdingsFrom(input.netPositionsBody, identities, "net"), collateral, valueCurrency);
  const lotHoldings = groupLots(holdingsFrom(input.positionsBody, identities, "lot"));
  const holdings = netHoldings.length > 0 ? netHoldings : attachCollateral(lotHoldings, collateral, valueCurrency);
  if (netHoldings.length > 0) {
    limitations.push("Each line is the net position in that account. Separate purchase lots stay behind that line.");
  }
  if (holdings.some((holding) => holding.valueBasis === "broker-market-value")) {
    limitations.push(
      "Holding values are the market values Saxo uses in the standard account total. A live price of zero is not shown as the price.",
    );
  } else if (holdings.some((holding) => holding.marketValue === null)) {
    limitations.push("Some holdings have no broker-reported market value. Their quantity is still shown.");
  }
  if (accountViews.some((account) => account.extendedReportedValue && account.extendedReportedValue !== account.brokerReportedValue)) {
    limitations.push(
      "Saxo's extended-hours account value is shown separately. It is not added to the standard total, and this response does not split it across holdings.",
    );
  }
  limitations.push("Holdings are unclassified until you classify them. They are not treated as global equity.");
  limitations.push("No combined currency total is calculated unless a sourced exchange rate exists.");

  return {
    environment: input.environment,
    retrievedAt: input.retrievedAt,
    coverage: {
      accounts: identities.length > 0,
      balances: accountViews.some((account) => account.cashBalance !== null || account.brokerReportedValue !== null),
      netPositions: netHoldings.length > 0,
      livePrices: holdings.length > 0 && holdings.every((holding) => holding.price !== null),
    },
    accounts: accountViews,
    holdings,
    limitations,
  };
}

function accountIdentities(body: unknown): AccountIdentity[] {
  return arrayData(body).flatMap((row) => {
    const recordRow = record(row);
    const key = text(recordRow, "AccountKey");
    if (!key) return [];
    const currency = text(recordRow, "Currency");
    const display = text(recordRow, "AccountDisplayName") ?? text(recordRow, "DisplayName");
    return [
      {
        key,
        id: text(recordRow, "AccountId"),
        label: display ?? (currency ? `Saxo ${currency} account` : "Saxo account"),
        currency,
      },
    ];
  });
}

function findBalance(balances: unknown[], identity: AccountIdentity): Record<string, unknown> | null {
  for (const balance of balances) {
    const row = record(balance);
    if (text(row, "AccountKey") === identity.key) return row;
    const id = text(row, "AccountId");
    if (id && id === identity.id) return row;
  }
  return null;
}

function holdingsFrom(
  body: unknown,
  identities: AccountIdentity[],
  kind: "net" | "lot",
): BrokerHoldingView[] {
  return arrayData(body).map((row) => {
    const base = record(record(row)?.PositionBase);
    const view = record(record(row)?.PositionView);
    const display = record(record(row)?.DisplayAndFormat);
    const netBase = record(record(row)?.NetPositionBase);
    const netView = record(record(row)?.NetPositionView);
    const source = kind === "net" ? netBase : (base ?? netBase);
    const prices = kind === "net" ? netView : (view ?? netView);
    const accountId = text(source, "AccountId") ?? text(source, "PositionsAccount");
    const identity = identities.find((item) => item.id && item.id === accountId);
    const symbol = text(display, "Symbol");
    const description = text(display, "Description");
    const valuation = valuationFrom(prices, null);
    const lots = prices?.PositionCount;
    const uic = source?.Uic;
    return {
      accountLabel: identity?.label ?? "Saxo account",
      name: description ?? symbol ?? "Unnamed instrument",
      symbol,
      assetType: text(source, "AssetType") ?? text(record(row), "AssetType"),
      uic: typeof uic === "number" && Number.isFinite(uic) ? uic : null,
      quantity: numberText(source, "Amount"),
      currency: identity?.currency ?? null,
      tradingCurrency: text(display, "Currency") ?? text(prices, "ExposureCurrency"),
      price: valuation.price,
      marketValue: valuation.marketValue,
      valueBasis: valuation.basis,
      profitLoss: numberText(prices, "ProfitLossOnTradeInBaseCurrency"),
      lotCount: typeof lots === "number" && Number.isFinite(lots) ? lots : null,
      classification: "unclassified" as const,
    };
  });
}

function collateralByUic(balances: Array<Record<string, unknown> | null>): Map<number, string> {
  const values = new Map<number, string>();
  for (const balance of balances) {
    const details = record(balance?.MarginCollateralNotAvailableDetail);
    const rows = details?.InstrumentCollateralDetails;
    if (!Array.isArray(rows)) continue;
    for (const item of rows) {
      const row = record(item);
      const uic = row?.Uic;
      const amount = numberText(row, "MarketValue");
      if (typeof uic === "number" && amount && amount !== "0") values.set(uic, amount);
    }
  }
  return values;
}

function attachCollateral(
  holdings: BrokerHoldingView[],
  collateral: Map<number, string>,
  valueCurrency: string | null,
): BrokerHoldingView[] {
  return holdings.map((holding) => {
    const amount = holding.uic === null ? undefined : collateral.get(holding.uic);
    if (!amount || holding.marketValue) return holding;
    return {
      ...holding,
      currency: valueCurrency ?? holding.currency,
      marketValue: amount,
      valueBasis: "broker-market-value",
    };
  });
}

function groupLots(holdings: BrokerHoldingView[]): BrokerHoldingView[] {
  const groups = new Map<string, BrokerHoldingView[]>();
  for (const holding of holdings) {
    const key = `${holding.uic ?? "none"}|${holding.assetType ?? ""}|${holding.symbol ?? ""}|${holding.accountLabel}`;
    groups.set(key, [...(groups.get(key) ?? []), holding]);
  }
  return [...groups.values()].map((rows) => {
    const first = rows[0];
    if (!first || rows.length === 1) return first as BrokerHoldingView;
    return {
      ...first,
      quantity: sumQuantities(rows.map((row) => row.quantity)),
      marketValue: null,
      valueBasis: null,
      profitLoss: null,
      lotCount: rows.length,
    };
  });
}

function sumQuantities(values: Array<string | null>): string | null {
  let sum = 0;
  for (const value of values) {
    if (value === null) return null;
    const amount = Number(value);
    if (!Number.isFinite(amount)) return null;
    sum += amount;
  }
  return String(sum);
}

/** A zero live price is not a valuation. The open-value field is not the current market value. */
function valuationFrom(
  prices: Record<string, unknown> | null,
  collateralAmount: string | null,
): {
  price: string | null;
  marketValue: string | null;
  basis: "live" | "broker-market-value" | null;
} {
  const liveValue = numberText(prices, "MarketValue");
  const livePrice = numberText(prices, "CurrentPrice");
  const price = livePrice !== null && livePrice !== "0" ? livePrice : null;
  if (liveValue !== null && liveValue !== "0") {
    return { price, marketValue: liveValue, basis: "live" };
  }
  if (collateralAmount && collateralAmount !== "0") {
    return { price, marketValue: collateralAmount, basis: "broker-market-value" };
  }
  return { price, marketValue: null, basis: null };
}

function arrayData(body: unknown): unknown[] {
  const data = record(body)?.Data;
  return Array.isArray(data) ? data : [];
}

function record(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function text(source: Record<string, unknown> | null, key: string): string | null {
  const value = source?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function numberText(source: Record<string, unknown> | null, key: string): string | null {
  const value = source?.[key];
  return typeof value === "number" && Number.isFinite(value) ? String(value) : null;
}
