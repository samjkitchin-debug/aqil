import type { DeployCapitalInput } from "./deploy.ts";

/**
 * Illustration only. These figures are not a Saxo snapshot and not the founder's account.
 * Targets, budget and the instrument are invented so the screen can be opened before preferences exist.
 * Nothing here is a cited share class.
 */

/** Zero cited share classes. This sentence is not a fund recommendation. */
export const NO_FUND_COMPARISON_COPY =
  "No fund comparison is available. No cited share class is stored.";

/**
 * Cited share-class count for Deploy capital. It stays zero until a permitted
 * issuer document has been stored on instruments.
 */
export const CITED_SHARE_CLASS_COUNT = 0;

export function fundComparisonCopy(citedShareClassCount: number): string {
  if (citedShareClassCount === 0) return NO_FUND_COMPARISON_COPY;
  return (
    "Cited share classes are stored. This screen does not place an order and does not recommend a fund."
  );
}

export const MADE_UP_EXAMPLE_COPY =
  "The amounts below are made up so the calculation can be inspected. They are not your holdings.";

export const exampleDeployment: DeployCapitalInput = {
  reportingCurrency: "SGD",
  classValues: [
    { assetClass: "global_equity", currency: "SGD", amountMinor: 800000n },
    { assetClass: "cash_investable", currency: "SGD", amountMinor: 200000n },
  ],
  targets: [
    { assetClass: "global_equity", targetWeightBps: 5000 },
    { assetClass: "cash_investable", targetWeightBps: 5000 },
  ],
  additionalCashMinor: 100000n,
  instruments: [
    {
      id: "example-world",
      name: "Example world equity unit",
      assetClass: "global_equity",
      currency: "SGD",
      minimumUnit: 1n,
      priceMinor: 3000n,
    },
  ],
  fx: [],
};

export const unconfiguredDeployment: DeployCapitalInput = {
  reportingCurrency: "SGD",
  classValues: [],
  targets: null,
  additionalCashMinor: null,
  instruments: null,
  fx: [],
};
