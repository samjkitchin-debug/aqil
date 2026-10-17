# The Sausage — engineering transfer (historical reference)

This folder holds **investigations and post-mortems** from the prior application *The Sausage*. It is **not** canonical product or implementation truth for Aqil.

## How to use this material

| Use | Do |
|-----|-----|
| Understand failure modes and discipline gaps | Read summaries and link to canonical Aqil docs |
| Copy code, workarounds or stack choices | **Do not** — principles are extracted into `docs/AUTH_AND_SESSION_DOCTRINE.md`, `docs/DOCUMENTATION_AUTHORITY.md`, and `docs/06_ENGINEERING_DISCIPLINE.md` |
| Instruct Cursor to restore Sausage behaviour | **Forbidden** — see `docs/CURSOR_COLLABORATION_WORKFLOW.md` |

## Files in this folder (reference)

| File | Role |
|------|------|
| `00_READ_FIRST.md` | How to read the transfer; G0 deploy remains blocked until RLS tests run |
| `01_TRANSFER_AUDIT.md` | Failure modes and what not to copy |
| `02_AQIL_AUTH_PWA_DOCTRINE_PROPOSAL.md` | Proposal absorbed into `AUTH_AND_SESSION_DOCTRINE.md` |
| `03_AQIL_ENGINEERING_GATES_PROPOSAL.md` | Proposal absorbed into `06_ENGINEERING_DISCIPLINE.md` |
| `04_AQIL_DOCS_GOVERNANCE_PROPOSAL.md` | Proposal absorbed into `DOCUMENTATION_AUTHORITY.md` |
| `05_CURSOR_INTEGRATION_PROMPT.md` | Historical task prompt; not a standing instruction |

Do not recreate a parallel `docs/canon/` tree or port Sausage auth recovery query parameters, diagnostic codes, or sports-domain SQL.

## Canonical destinations (Aqil)

- Authentication and PWA sessions → `docs/AUTH_AND_SESSION_DOCTRINE.md`
- Documentation tiers and ADRs → `docs/DOCUMENTATION_AUTHORITY.md`
- CI, migrations, RLS, release → `docs/06_ENGINEERING_DISCIPLINE.md` §7–8
- Data immutability and provenance → `docs/04_ARCHITECTURE_AND_DATA.md`, `docs/03_RESEARCH_ENGINE_AND_METHODS.md`
