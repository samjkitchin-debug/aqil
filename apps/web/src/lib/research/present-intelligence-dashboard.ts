import {
  CONDITION_REGIONS,
  type MacroConditionsView,
  type MacroPanelState,
  type MacroSeriesPanel,
} from "./present-macro-conditions.ts";
import type { SeriesChartModel } from "./series-chart-model.ts";

/** Collapsed accordions show a few observations, not every stored series. */
export const DASHBOARD_SUMMARY_LIMIT = 3;

const CATEGORY_LABEL: Record<string, string> = {
  growth: "Production",
};

export type DashboardMetric = {
  sourceId: string;
  name: string;
  region: string;
  valueLabel: string | null;
  valueUnit: string | null;
  periodLabel: string | null;
  changeLabel: string | null;
  state: MacroPanelState;
  chart: SeriesChartModel | null;
};

export type DashboardCategory = {
  id: string;
  label: string;
  summary: DashboardMetric[];
  panels: MacroSeriesPanel[];
};

export type IntelligenceDashboard = {
  regionId: MacroConditionsView["regionId"];
  regionLabel: string;
  scopeLine: string | null;
  completenessLine: string;
  revisionLimit: string;
  freshnessRule: string;
  intro: string;
  categories: DashboardCategory[];
  absentLine: string | null;
};

export function presentIntelligenceDashboard(view: MacroConditionsView): IntelligenceDashboard {
  const regionLabel = CONDITION_REGIONS.find((item) => item.id === view.regionId)?.label ?? "Global";
  const absent = view.unavailable.map((item) => item.name);
  return {
    regionId: view.regionId,
    regionLabel,
    scopeLine:
      view.regionId === "global"
        ? "All stored regions are listed. This is not a world aggregate."
        : null,
    completenessLine: view.completenessLine,
    revisionLimit: view.revisionLimit,
    freshnessRule: view.freshnessRule,
    intro: view.intro,
    categories: view.groups.map((group) => ({
      id: group.id,
      label: CATEGORY_LABEL[group.id] ?? group.label,
      summary: group.panels.slice(0, DASHBOARD_SUMMARY_LIMIT).map(toMetric),
      panels: group.panels,
    })),
    absentLine: absent.length === 0 ? null : `No live series is stored for ${joinNames(absent)}.`,
  };
}

function toMetric(panel: MacroSeriesPanel): DashboardMetric {
  return {
    sourceId: panel.sourceId,
    name: panel.name,
    region: panel.region,
    valueLabel: panel.valueLabel,
    valueUnit: panel.valueUnit,
    periodLabel: panel.periodLabel,
    changeLabel: summaryChange(panel.changeLabel),
    state: panel.state,
    chart: panel.chart,
  };
}

function summaryChange(label: string | null): string | null {
  if (!label) return null;
  if (label.startsWith("A previous observation") || label.startsWith("The stored values")) {
    return "No change stored";
  }
  return label;
}

function joinNames(names: readonly string[]): string {
  if (names.length === 1) return names[0] ?? "";
  if (names.length === 2) return `${names[0]} or ${names[1]}`;
  return `${names.slice(0, -1).join(", ")}, or ${names[names.length - 1]}`;
}
