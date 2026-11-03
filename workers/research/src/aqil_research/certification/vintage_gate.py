"""Decide whether one registered method has an original vintage for its own inputs.

The real GDP growth vintage is not relabelled as an input. ALFRED is not
archived. A current file that the rights register allows to be stored is still
not an original vintage. This module does not change methodology mathematics
and does not manufacture a timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass

GDP_SERIES = "bea.vintage.real_gdp.pct_preceding"
ALFRED_DATASET = "fred.alfred.UNRATE"

PREFERRED_DATASETS = frozenset(
    {
        "bls.ln.LNS14000000",
        "bls.cu.CUSR0000SA0",
        "fed.g17.IP.B50001.S",
        "fed.h15.RIFLGFCY10_N.M",
        "fed.h15.RIFLGFCM03_N.M",
        "fed.h15.RIFSPFF_N.M",
    }
)

# Publications the rights register already describes. None is an original vintage
# panel for a registered method's inputs. The phrases follow those rows.
NOT_AN_ORIGINAL_VINTAGE: dict[str, str] = {
    "bls.ln.LNS14000000": (
        "The registered publication is the current LN flat file. It has no vintage column."
    ),
    "bls.empsit.archive": (
        "The rights row says archived Employment Situation releases may have been revised "
        "and are not established as original vintages."
    ),
    "bls.cu.CUSR0000SA0": (
        "The registered publication is the current CPI-U series, not a vintage panel."
    ),
    "bls.cpi.archive": (
        "The rights row says archived CPI releases may be revised by later releases."
    ),
    "fed.g17.IP.B50001.S": (
        "The registered publication is the current G.17 package, not a vintage panel."
    ),
    "fed.h15.RIFLGFCY10_N.M": (
        "The registered publication is the current H.15 package, not a vintage panel."
    ),
    "fed.h15.RIFLGFCM03_N.M": (
        "The registered publication is the current H.15 package, not a vintage panel."
    ),
    "fed.h15.RIFSPFF_N.M": (
        "The registered publication is the current H.15 package, not a vintage panel."
    ),
}


@dataclass(frozen=True)
class MethodInputs:
    method_id: str
    datasets: tuple[str, ...]
    vintage_class: str


@dataclass(frozen=True)
class Gate5Assessment:
    method_count: int
    eligible_method_ids: tuple[str, ...]
    gdp_is_required_by_any_method: bool
    alfred_historical_archiving: str
    blocker: str | None

    @property
    def gate6_allowed(self) -> bool:
        return self.blocker is None and len(self.eligible_method_ids) == 1


def inputs_covered(
    method: MethodInputs,
    *,
    archiving: dict[str, str],
    live_provider_vintages: frozenset[str],
    not_original: dict[str, str],
) -> bool:
    """True when every required dataset is a live original vintage the register may archive."""
    if not method.datasets:
        return False
    for dataset_id in method.datasets:
        if dataset_id == ALFRED_DATASET or archiving.get(dataset_id) != "permitted":
            return False
        if dataset_id in not_original:
            return False
        if dataset_id not in live_provider_vintages:
            return False
    return True


def assess_gate5(
    methods: tuple[MethodInputs, ...],
    *,
    archiving: dict[str, str],
    live_provider_vintages: frozenset[str],
    not_original: dict[str, str] | None = None,
) -> Gate5Assessment:
    """Return a blocked assessment unless exactly one method is covered and declared vintage."""
    excluded = NOT_AN_ORIGINAL_VINTAGE if not_original is None else not_original
    gdp_required = any(GDP_SERIES in method.datasets for method in methods)
    eligible: list[str] = []
    for method in methods:
        covered = inputs_covered(
            method,
            archiving=archiving,
            live_provider_vintages=live_provider_vintages,
            not_original=excluded,
        )
        # Coverage alone does not relabel a latest_revised declaration.
        if covered and method.vintage_class == "provider_vintage":
            eligible.append(method.method_id)
    alfred = archiving.get(ALFRED_DATASET, "missing")
    declared = {method.vintage_class for method in methods}
    blocker = None
    if len(eligible) != 1:
        blocker = _blocker(
            method_count=len(methods),
            gdp_required=gdp_required,
            alfred=alfred,
            live_provider_vintages=live_provider_vintages,
            vintage_classes=declared,
        )
    return Gate5Assessment(
        method_count=len(methods),
        eligible_method_ids=tuple(eligible),
        gdp_is_required_by_any_method=gdp_required,
        alfred_historical_archiving=alfred,
        blocker=blocker,
    )


def _blocker(
    *,
    method_count: int,
    gdp_required: bool,
    alfred: str,
    live_provider_vintages: frozenset[str],
    vintage_classes: set[str],
) -> str:
    gdp_role = (
        f"{GDP_SERIES} is a required input"
        if gdp_required
        else f"{GDP_SERIES} is not a required input of any registered method"
    )
    live = ", ".join(sorted(live_provider_vintages)) or "none"
    declared = ", ".join(sorted(vintage_classes)) or "none"
    return (
        f"Gate 5 is blocked. {method_count} registered methods were inspected. "
        f"Declared vintage classes: {declared}. This pass does not relabel one. "
        f"{gdp_role}. "
        f"Live provider-vintage datasets on the preserved database: {live}. "
        f"{ALFRED_DATASET} historical archiving is {alfred}, so ALFRED is not stored. "
        "Unemployment, CPI-U, industrial production, and the H.15 Treasury yields are "
        "permitted to be archived as their current publications. Those publications are "
        "not original vintages. The Employment Situation archive and the CPI archive are "
        "also permitted to be archived, and the rights rows say those archived releases "
        "may have been revised. No rights-cleared source supplies an original vintage for "
        "every input of one registered method. No methodology and no vintage were manufactured."
    )


def load_registered_assessment() -> Gate5Assessment:
    """Read the 26 registrations, the rights register, and live vintages. No writes."""
    import csv

    import psycopg

    from aqil_research.long_horizon.pilot import LOCAL_RESEARCH_URL, repo_root
    from aqil_research.methods.registry import default_method_registry

    methods = tuple(
        MethodInputs(
            method.method_id,
            tuple(method.required_dataset_ids()),
            method.dependency().vintage_class,
        )
        for method in default_method_registry().registered()
    )
    rank = {"prohibited": 0, "unknown": 1, "permitted": 2}
    archiving: dict[str, str] = {}
    rights_path = repo_root() / "docs" / "sources" / "SOURCE_RIGHTS.csv"
    with rights_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            dataset_id = row["dataset_id"]
            value = row["historical_archiving"]
            current = archiving.get(dataset_id)
            if current is None or rank.get(value, 1) < rank.get(current, 1):
                archiving[dataset_id] = value
    with psycopg.connect(LOCAL_RESEARCH_URL) as connection:
        connection.read_only = True
        rows = connection.execute(
            """
            select distinct o.dataset_id
            from research.economic_observations o
            join research.source_retrievals r on r.retrieval_id = o.retrieval_id
            where o.series_provenance = 'provider_vintage'
              and r.collection_mode = 'live'
            """
        ).fetchall()
    live = frozenset(row[0] for row in rows)
    return assess_gate5(
        methods,
        archiving=archiving,
        live_provider_vintages=live,
    )
