import assert from "node:assert/strict";
import test from "node:test";

import { presentIntelligenceDashboard } from "./present-intelligence-dashboard.ts";
import type { MacroConditionsView, MacroSeriesPanel } from "./present-macro-conditions.ts";

function panel(sourceId: string, name: string, changeLabel: string | null = "+0.1 percentage points since August 2026"): MacroSeriesPanel {
  return {
    sourceId,
    name,
    region: "United States",
    state: "current",
    warning: null,
    valueLabel: "4.2",
    valueUnit: "percent",
    periodLabel: "September 2026",
    changeLabel,
    measures: "A stored measure.",
    matters: "Read it with the other series.",
    sourceLabel: "Bureau of Labor Statistics · Current Population Survey",
    sourceHref: "https://data.bls.gov/timeseries/LNS14000000",
    sourceLinkLabel: "Series page",
    sourceLinkNote: null,
    freshnessLabel: "Retrieved 1 October 2026.",
    gapLine: null,
    chartNote: null,
    details: ["source id bls_cps_unemployment_rate"],
    evidenceHref: "/research",
    chart: null,
  };
}

function view(groups: MacroConditionsView["groups"]): MacroConditionsView {
  return {
    regionId: "united-states",
    intro: "Each figure restates a stored live observation.",
    freshnessRule: "A monthly series is stale after two months.",
    completenessLine: "3 of 3 tracked series have a stored observation.",
    revisionLimit: "The stored series are latest revised.",
    groups,
    unavailable: [{ id: "liquidity", name: "Liquidity", detail: "No live series is stored." }],
  };
}

test("a collapsed category keeps three observations and the rest for expansion", () => {
  const dashboard = presentIntelligenceDashboard(
    view([
      {
        id: "labour",
        label: "Labour",
        panels: [
          panel("unemployment", "Unemployment rate"),
          panel("payrolls", "Payrolls"),
          panel("openings", "Job openings"),
          panel("claims", "Claims"),
        ],
      },
    ]),
  );
  const labour = dashboard.categories[0];
  assert.equal(labour?.label, "Labour");
  assert.equal(labour?.summary.length, 3);
  assert.deepEqual(
    labour?.summary.map((item) => item.name),
    ["Unemployment rate", "Payrolls", "Job openings"],
  );
  assert.equal(labour?.panels.length, 4);
  assert.equal(dashboard.absentLine, "No live series is stored for Liquidity.");
  assert.equal(JSON.stringify(dashboard).includes("favourable"), false);
});

test("production is the dashboard name for the growth group", () => {
  const dashboard = presentIntelligenceDashboard(
    view([{ id: "growth", label: "Growth", panels: [panel("ip", "Industrial production", null)] }]),
  );
  assert.equal(dashboard.categories[0]?.label, "Production");
  assert.equal(dashboard.categories[0]?.summary[0]?.changeLabel, null);
});

test("a missing comparison stays a short neutral line", () => {
  const dashboard = presentIntelligenceDashboard(
    view([
      {
        id: "rates",
        label: "Rates",
        panels: [panel("funds", "Federal funds rate", "A previous observation is not stored, so no change is shown.")],
      },
    ]),
  );
  assert.equal(dashboard.categories[0]?.summary[0]?.changeLabel, "No change stored");
  assert.equal(dashboard.regionLabel, "United States");
  assert.equal(dashboard.scopeLine, null);
});
