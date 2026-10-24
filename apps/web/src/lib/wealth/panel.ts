import type { SaxoLinkState } from "../saxo/link-state.ts";
import { formatAccumulatedReturn } from "../saxo/performance.ts";
import {
  formatQuantity,
  formatReportedAmount,
  formatRetrievedAt,
  type BrokerHoldingView,
  type BrokerPortfolioView,
} from "../saxo/portfolio.ts";

export const BROKERAGE_SHARE_CLASS_UNRESOLVED =
  "The share class is unresolved because the saved line has no ISIN.";

const RECONNECT_ERRORS = new Set([
  "refresh_failed",
  "no_session",
  "saxo_exchange",
  "saxo_denied",
  "saxo_state",
  "saxo_user",
]);

const RECONCILE_TOLERANCE = 0.05;

export type PanelTone = "positive" | "negative" | "flat";

export type PanelHolding = {
  key: string;
  name: string;
  ticker: string;
  kind: string;
  value: string | null;
  weightLabel: string | null;
  openAmount: string | null;
  openPercent: string | null;
  tone: PanelTone | null;
  quantity: string;
  tradingCurrency: string | null;
  lots: number | null;
  basisLabel: string | null;
  priceLabel: string;
  accountLabel: string;
};

export type PanelSegment = {
  key: string;
  label: string;
  kind: string;
  weightPct: number;
  weightLabel: string;
  valueLabel: string;
  swatch: number;
};

export type WealthPanel = {
  simulation: boolean;
  headline: { amount: string; currency: string; basis: "Standard account value" } | null;
  openPosition: {
    label: "Open-position gain" | "Open-position loss" | "Open-position result";
    amount: string;
    percentOfCost: string | null;
    tone: PanelTone;
    period: "Since these positions were opened";
  } | null;
  monthReturn: {
    label: "Time-weighted return";
    period: "This month";
    text: string;
    tone: PanelTone;
  } | null;
  chart: {
    points: { date: string; value: string }[];
    currency: string | null;
    from: string;
    to: string;
  } | null;
  freshness: {
    environment: "Live account" | "Simulation account";
    retrieved: string;
    prices: "Live prices included" | "Live prices unavailable";
    connection: "connected" | "saved" | "reconnect";
    connectionLabel: "Saxo is connected" | "Saved snapshot" | "Reconnect Saxo";
  };
  cash: string | null;
  investmentCount: number;
  largest: { name: string; ticker: string; kind: string; weightLabel: string } | null;
  composition: {
    basis: "Share of the standard account value";
    etfNote: boolean;
    segments: PanelSegment[];
  } | null;
  holdings: PanelHolding[];
  extended: { amount: string; retrieved: string } | null;
  standardAmount: string | null;
  buyingPower: string | null;
  limitations: string[];
};

function asNumber(value: string | null): number | null {
  if (value === null) return null;
  const amount = Number(value);
  return Number.isFinite(amount) ? amount : null;
}

function toneOf(amount: number): PanelTone {
  if (amount > 0) return "positive";
  if (amount < 0) return "negative";
  return "flat";
}

function formatPlain(amount: number): string {
  return new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatSigned(amount: number, currency: string | null): string {
  const formatted = new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: "exceptZero",
  }).format(amount);
  return currency ? `${formatted} ${currency}` : formatted;
}

function formatWeight(fraction: number): string {
  return new Intl.NumberFormat("en-GB", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(fraction);
}

function formatSignedPercent(fraction: number): string {
  return new Intl.NumberFormat("en-GB", {
    style: "percent",
    maximumFractionDigits: 1,
    signDisplay: "exceptZero",
  }).format(fraction);
}

export function displayTicker(symbol: string | null): string {
  if (!symbol) return "No ticker";
  const head = symbol.split(":")[0]?.trim();
  return head || symbol;
}

export function instrumentKind(assetType: string | null): string {
  if (!assetType) return "Holding";
  if (assetType.toLowerCase() === "etf") return "ETF";
  if (assetType.toLowerCase() === "stock") return "Stock";
  return assetType;
}

function ranked(holdings: BrokerHoldingView[]): BrokerHoldingView[] {
  return [...holdings].sort((left, right) => (asNumber(right.marketValue) ?? Number.NEGATIVE_INFINITY) - (asNumber(left.marketValue) ?? Number.NEGATIVE_INFINITY));
}

function basisLabel(basis: BrokerHoldingView["valueBasis"]): string | null {
  if (basis === "live") return "Live market value";
  if (basis === "broker-market-value") return "Standard broker market value";
  return null;
}

function connectionOf(link: SaxoLinkState, error: string | null): WealthPanel["freshness"]["connection"] {
  if ((error && RECONNECT_ERRORS.has(error)) || link === "expired" || link === "absent") return "reconnect";
  if (link === "active") return "connected";
  return "saved";
}

function connectionLabel(connection: WealthPanel["freshness"]["connection"]): WealthPanel["freshness"]["connectionLabel"] {
  if (connection === "connected") return "Saxo is connected";
  if (connection === "reconnect") return "Reconnect Saxo";
  return "Saved snapshot";
}

function openResult(amount: number, currency: string | null, cost: number | null): WealthPanel["openPosition"] {
  const label = amount > 0 ? "Open-position gain" : amount < 0 ? "Open-position loss" : "Open-position result";
  return {
    label,
    amount: formatSigned(amount, currency),
    percentOfCost: cost !== null && cost > 0 ? formatSignedPercent(amount / cost) : null,
    tone: toneOf(amount),
    period: "Since these positions were opened",
  };
}

export function buildWealthPanel(input: {
  broker: BrokerPortfolioView;
  link: SaxoLinkState;
  error: string | null;
}): WealthPanel {
  const account = input.broker.accounts.length === 1 ? input.broker.accounts[0] : null;
  const currency = account?.currency ?? null;
  const holdings = ranked(input.broker.holdings);
  const standard = asNumber(account?.brokerReportedValue ?? null);
  const cash = asNumber(account?.cashBalance ?? null);
  const holdingValues = holdings.map((holding) => asNumber(holding.marketValue));
  const priced = holdingValues.every((value) => value !== null);
  const holdingsSum = priced ? holdingValues.reduce<number>((sum, value) => sum + (value ?? 0), 0) : null;
  const reconciled =
    account !== null &&
    standard !== null &&
    cash !== null &&
    holdingsSum !== null &&
    Math.abs(cash + holdingsSum - standard) <= RECONCILE_TOLERANCE;
  const sameCurrency = holdings.every((holding) => !holding.currency || holding.currency === currency);
  const openValues = holdings.map((holding) => asNumber(holding.profitLoss));
  const openComplete = openValues.every((value) => value !== null);
  const openSum =
    openComplete && sameCurrency && currency && holdings.length > 0
      ? openValues.reduce<number>((sum, value) => sum + (value ?? 0), 0)
      : null;
  let cost: number | null = null;
  if (openSum !== null && holdingsSum !== null && openComplete) {
    const costs = holdings.map((holding, index) => {
      const market = holdingValues[index];
      const profit = openValues[index];
      if (market === null || profit === null) return null;
      return market - profit;
    });
    cost = costs.every((value) => value !== null && value > 0)
      ? costs.reduce<number>((sum, value) => sum + (value ?? 0), 0)
      : null;
  }

  const denominator = reconciled && standard !== null && standard > 0 ? standard : null;
  const weightOf = (amount: number | null): number | null =>
    denominator !== null && amount !== null ? amount / denominator : null;

  const segments: PanelSegment[] = [];
  if (denominator !== null && cash !== null) {
    holdings.forEach((holding, index) => {
      const amount = holdingValues[index];
      const weight = weightOf(amount);
      if (amount === null || weight === null) return;
      segments.push({
        key: `${displayTicker(holding.symbol)}-${index}`,
        label: displayTicker(holding.symbol),
        kind: instrumentKind(holding.assetType),
        weightPct: weight * 100,
        weightLabel: formatWeight(weight),
        valueLabel: formatReportedAmount(holding.marketValue, holding.currency),
        swatch: (index % 5) + 1,
      });
    });
    const cashWeight = weightOf(cash);
    if (cashWeight !== null) {
      segments.push({
        key: "cash",
        label: "Cash",
        kind: "Cash",
        weightPct: cashWeight * 100,
        weightLabel: formatWeight(cashWeight),
        valueLabel: formatReportedAmount(account?.cashBalance ?? null, currency),
        swatch: 0,
      });
    }
  }

  const largestHolding = holdings.find((holding) => asNumber(holding.marketValue) !== null) ?? null;
  const largestWeight = largestHolding ? weightOf(asNumber(largestHolding.marketValue)) : null;
  const performance = input.broker.performance?.status === "ok" ? input.broker.performance : null;
  const latestReturn = performance?.timeWeightedAccumulated.at(-1) ?? null;
  const returnText = performance ? formatAccumulatedReturn(latestReturn?.value ?? null) : null;
  const returnAmount = asNumber(latestReturn?.value ?? null);
  const chartPoints = performance && performance.accountValue.length > 1 ? performance.accountValue : null;
  const connection = connectionOf(input.link, input.error);
  const extended = asNumber(account?.extendedReportedValue ?? null);
  const buying = asNumber(account?.buyingPower ?? null);

  return {
    simulation: input.broker.environment === "simulation",
    headline:
      standard !== null && currency
        ? { amount: formatPlain(standard), currency, basis: "Standard account value" }
        : null,
    openPosition: openSum !== null ? openResult(openSum, currency, cost) : null,
    monthReturn:
      returnText && returnAmount !== null
        ? {
            label: "Time-weighted return",
            period: "This month",
            text: returnText,
            tone: toneOf(returnAmount),
          }
        : null,
    chart: chartPoints
      ? {
          points: chartPoints,
          currency: performance?.currency ?? null,
          from: chartPoints[0]?.date ?? "",
          to: chartPoints.at(-1)?.date ?? "",
        }
      : null,
    freshness: {
      environment: input.broker.environment === "live" ? "Live account" : "Simulation account",
      retrieved: formatRetrievedAt(input.broker.retrievedAt),
      prices: input.broker.coverage.livePrices ? "Live prices included" : "Live prices unavailable",
      connection,
      connectionLabel: connectionLabel(connection),
    },
    cash: account ? formatReportedAmount(account.cashBalance, currency) : null,
    investmentCount: holdings.length,
    largest:
      largestHolding && largestWeight !== null
        ? {
            name: largestHolding.name,
            ticker: displayTicker(largestHolding.symbol),
            kind: instrumentKind(largestHolding.assetType),
            weightLabel: formatWeight(largestWeight),
          }
        : null,
    composition:
      segments.length > 0
        ? {
            basis: "Share of the standard account value",
            etfNote: segments.some((segment) => segment.kind === "ETF"),
            segments,
          }
        : null,
    holdings: holdings.map((holding, index) => {
      const amount = holdingValues[index];
      const profit = openValues[index];
      const weight = weightOf(amount);
      const holdingCost = amount !== null && profit !== null ? amount - profit : null;
      const holdingCurrency = holding.currency;
      const comparable = holdingCurrency === currency && profit !== null;
      return {
        key: `${holding.uic ?? holding.symbol ?? holding.name}-${index}`,
        name: holding.name,
        ticker: displayTicker(holding.symbol),
        kind: instrumentKind(holding.assetType),
        value: amount !== null ? formatReportedAmount(holding.marketValue, holding.currency) : null,
        weightLabel: weight !== null ? formatWeight(weight) : null,
        openAmount: comparable ? formatSigned(profit, holdingCurrency) : null,
        openPercent: comparable && holdingCost !== null && holdingCost > 0 ? formatSignedPercent(profit / holdingCost) : null,
        tone: comparable ? toneOf(profit) : null,
        quantity: formatQuantity(holding.quantity),
        tradingCurrency: holding.tradingCurrency,
        lots: holding.lotCount,
        basisLabel: basisLabel(holding.valueBasis),
        priceLabel: holding.price ? formatReportedAmount(holding.price, holding.tradingCurrency) : "Price unavailable",
        accountLabel: holding.accountLabel,
      };
    }),
    extended:
      extended !== null && currency && account?.extendedReportedValue !== account?.brokerReportedValue
        ? { amount: formatReportedAmount(account?.extendedReportedValue ?? null, currency), retrieved: formatRetrievedAt(input.broker.retrievedAt) }
        : null,
    standardAmount: standard !== null && currency ? formatReportedAmount(account?.brokerReportedValue ?? null, currency) : null,
    buyingPower:
      buying !== null && account?.buyingPower !== account?.cashBalance
        ? formatReportedAmount(account?.buyingPower ?? null, currency)
        : null,
    limitations: input.broker.limitations,
  };
}
