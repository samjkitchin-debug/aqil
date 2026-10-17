# Cursor prompt — use AFTER the current G0 database task has finished

AQIL — INCORPORATE PROVEN SAUSAGE ENGINEERING LESSONS (DOC-FIRST)

Context: Aqil's authoritative v2 documents and verified G0 scaffold are already in the repo. Founder supplied a retrospective of lessons learned from The Sausage; the proposed transfer documents are now in /docs/sausage-transfer/. Treat them as proposals, not a new product direction.

READ FIRST:
- /docs/00_READ_ME_FIRST.md
- /docs/04_ARCHITECTURE_AND_DATA.md
- /docs/06_ENGINEERING_DISCIPLINE.md
- /docs/07_ROADMAP_AND_GATES.md
- /docs/sausage-transfer/00_READ_FIRST.md through 04_AQIL_DOCS_GOVERNANCE_PROPOSAL.md

TASK: Inspect Aqil's CURRENT source and G0 database implementation. Report which transfer rules are already satisfied, which are missing, and which are too early or Sausage-specific.

Apply only these surgical documentation and G0 safeguards:
1. Add one focused future auth/session/PWA doctrine and link it from /docs/00_READ_ME_FIRST.md; do not implement speculative custom auth recovery now.
2. Make the existing database gate require real, role-accurate RLS and migration replay before hosted migration approval. If Docker is missing, present the lowest-friction Windows installation/WSL2 or isolated CI alternative; do not pretend blocked tests passed.
3. Make Supabase SQL grant/SECURITY DEFINER scrutiny explicit for future RPC work, including PUBLIC and anon role grants.
4. Update the existing engineering gate and docs hierarchy without duplicating or replacing v2 canonical product/research/architecture content.
5. Add a concise acceptance checklist for future mobile idle/resume/auth persistence tests; do not add UI/auth code yet.

CHECK CURRENT SUPABASE WORK: migration file naming/ordering, single authoritative migration path, CI tests actually run, and DB permissions executed as genuine request roles. Do not apply or reset the hosted Supabase project. Do not change investment research or portfolio architecture.

Report changes, tests, blocked checks and recommendations. Ask before destructive actions, deployment, commit or push. Plan briefly before edits, use smallest viable changes, preserve the already-working responsive shell.
