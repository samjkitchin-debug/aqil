# Reproduction

**Status:** research record. This is not an investment claim and it is not Verified.

From `workers/research`, after the local databases are available:

```text
uv run python -m aqil_research.long_horizon.reproduce
```

The command reads execution `LH-X-001`, evidence `LH-V-001`, and the current claim status. It fails if `publication_allowed` is true, if the stored specification hash, package code hash, or evidence hash disagrees with the files and the stored artefact, or if the recomputed status disagrees with the stored status. It reloads listing prices from `aqil_etf` read-only and recomputes the artefact hash. It does not write.

The historical command that first stores the execution is:

```text
uv run python -m aqil_research.long_horizon.pilot
```

That command refuses to run unless the only dirty worktree file is `apps/web/public/icons/icon.svg`. It stores the frozen specification before it reads prices. The prices themselves are not copied into Git. The public manifest records checksums and reconciliation totals. The full path stays in `research.evidence_records`.

A change to any Python file in `aqil_research.long_horizon` changes the code hash. The stored execution is not overwritten to hide that change.
