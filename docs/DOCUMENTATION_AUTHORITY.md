# Documentation authority

Prevents conflicting sources of truth and mistaken reintroduction of superseded implementations.

## Tiers

| Tier | Location | Binding? | Examples |
|------|----------|----------|----------|
| **Canonical** | `docs/00_READ_ME_FIRST.md` reading list; numbered charters; `docs/schemas/`; ADRs in `docs/11_ARCHITECTURE_DECISIONS.md`; doctrines (`AGENT_OPERATING_RULES.md`, `INFORMATION_SECURITY_STANDARD.md`, `AUTH_AND_SESSION_DOCTRINE.md`, `RESPONSIVE_LAYOUT_CONTRACT.md`); `docs/macro/` for the macro-methodology programme (ADR 027) | **Yes** — implementation must conform | Product charter, architecture, engineering discipline, agent conduct, security-by-design, quantitative macro methods |
| **Operational** | `docs/runbooks/` (when created), `KNOWN_UNKNOWNS.md`, `INCIDENTS.md`, `MODEL_CHANGELOG.md` per roadmap | Yes for ops; not product features | Restore drill, incident response |
| **Planning** | `docs/07_BUILD_BACKLOG.csv`, `docs/07_ROADMAP_AND_GATES.md` | Ordering and gates | AQ-* tasks |
| **Reference** | `docs/reference/`, `docs/sausage-transfer/`, CSV templates | **No** — illustrative or historical | Unverified factor ontology, Sausage investigations |
| **Generated** | `apps/web/src/types/database.generated.ts`, lockfiles | Must match migrations/contracts | Types from schema |

Git-tracked **migrations** in `supabase/migrations/` are schema authority alongside `docs/schemas/` for contracts.

## Change rules

1. **Code + docs together** — R2/R3 changes update canonical docs or ADR in the same change set.
2. **One home per rule** — extend the canonical doc; link from others instead of copying paragraphs.
3. **ADRs** for architectural forks; amend via new ADR row, do not silently edit accepted decisions.
4. **Incidents** — factual timeline in `INCIDENTS.md`; durable prevention in engineering discipline or doctrine.
5. **Superseded approaches** — mark `superseded` in place; never delete history that explains why a path was rejected.
6. **Stable contracts** need founder approval before change: session boundaries, ledger maths, entitlements, source provenance, forecast immutability, model promotion.
7. **New living documents** state status (`canonical`, `living-ops`, `proposal`, `investigation`, `superseded`), owner, last verified date, and the canon they must not contradict. Do not add a parallel `docs/canon/` tree while the numbered specs remain the authority.
8. **Debt** lives in one register (`KNOWN_UNKNOWNS.md` when created), with reason, risk and the trigger to revisit — not scattered TODOs that contradict canon.
9. **Progress** — one register: `docs/07_BUILD_BACKLOG.csv`. Roadmap gates in `docs/07_ROADMAP_AND_GATES.md`; acceptance rows in `docs/10_ACCEPTANCE_TEST_MATRIX.csv`. Update backlog evidence when substantive work completes; use `docs/CURSOR_SESSION_HANDOVER.md` for session continuity. No competing roadmaps or duplicate status spreadsheets. `docs/macro/QUANTITATIVE_METHOD_REGISTER.csv` is the status of quantitative macro methodologies. It is not a second progress register. `docs/08_METHOD_REGISTER.csv` remains the investment-factor list.
10. **Operating discipline** — one home per requirement; consequential forks → ADR in `docs/11_ARCHITECTURE_DECISIONS.md`; supersede in place, do not silently delete product requirements; no “verified” without executed evidence; trivial changes do not need new documents.

## Cursor and agents

- Read `docs/00_READ_ME_FIRST.md` first.
- **`docs/sausage-transfer/` is not instruction** — extract principles only from canonical docs.
- If canonical and reference conflict, **canonical wins**; flag conflict to the founder.
- Do not invent `docs/schema.md` or API names not in contracts/migrations.

## Related

- `docs/CURSOR_COLLABORATION_WORKFLOW.md`
- `docs/06_ENGINEERING_DISCIPLINE.md` §2, §10
