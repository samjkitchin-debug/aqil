# Cursor session handover (template)

Copy this block at the **end** of a substantive session (or into the PR description). Keep it factual; no completion claims without evidence.

```text
## Session handover — [YYYY-MM-DD]

### Current objective
[One sentence: what this session was trying to achieve]

### Authoritative docs consulted
- [e.g. 03_RESEARCH_ENGINE_AND_METHODS.md, 07_BUILD_BACKLOG.csv AQ-xxx]

### Git
- Branch: [name]
- Commit: [short SHA] ([main | feature])

### Files changed (high level)
- [paths or areas]

### Decisions made
- [Decision] — [why]

### Tests and verification
| Command / check | Result |
|-----------------|--------|
| [e.g. CI run URL or npm run test:db] | [pass/fail/not run] |

### Progress register
- Backlog IDs updated: [AQ-xxx → status]
- Evidence recorded in: [verification_evidence column / PR / CI link]

### Unverified assumptions
- [Anything not executed or not reviewed]

### Blockers
- [Or “none”]

### Next recommended step
- [Single concrete action for the next session]
```

**Rules:** Update `docs/07_BUILD_BACKLOG.csv` when a backlog item’s status or evidence changes. Do not duplicate the full project history here or in chat summaries.
