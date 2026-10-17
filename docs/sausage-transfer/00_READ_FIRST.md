# The Sausage → Aqil: transfer review

**Status:** proposed additions to the existing Aqil v2 ground-zero specification, not a replacement or new product vision.

**Evidence:** reviewed the user-provided `docs.zip` (The Sausage documentation snapshot; 150 archive entries, roughly 1.2 MB of documentation). This is a documentary audit, **not** a current source-code audit of either repository. Statements that describe The Sausage's behaviour are based on its documented canon/runbooks, which sometimes acknowledge legacy or superseded implementations. Do not copy code assumptions without inspection and tests.

## Files in this supplement

1. `01_TRANSFER_AUDIT.md` — findings, priority and adaptation decisions.
2. `02_AQIL_AUTH_PWA_DOCTRINE_PROPOSAL.md` — foundational auth/session contract for Next.js + Supabase + mobile PWA.
3. `03_AQIL_ENGINEERING_GATES_PROPOSAL.md` — layered build/DB/production release gates.
4. `04_AQIL_DOCS_GOVERNANCE_PROPOSAL.md` — authority, drift-control and canonical-document rules.
5. `05_CURSOR_INTEGRATION_PROMPT.md` — tightly scoped future Cursor task to integrate after current database work.

**Not yet approved or applied.** Fold the findings into Aqil `/docs` and tests only after reviewing their fit against actual Aqil code. Do not import the entire Sausage docs folder into Aqil; preserve it separately as reference material.

## Immediate G0 guidance

The first Aqil Supabase migration has **not** passed executable RLS tests: local Docker is missing and CI has not run the new database job. Do **not** approve remote deployment yet. Establish a disposable Supabase/PostgreSQL test environment, replay the migration and execute role-authenticated negative RLS cases. Review the timestamp `20260317103000_...`: it predates the present development work; if unapplied, use a correctly ordered current migration identifier. Track database changes through a single Git versioned migration path. The MCP connection is a tool, not the source of truth.
