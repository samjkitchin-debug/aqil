import type { DeployCapitalInput } from "./deploy.ts";

/**
 * Illustration only. These figures are not a Saxo snapshot and not the founder's account.
 * Targets, budget and the instrument are invented so the screen can be opened before preferences exist.
 */
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
