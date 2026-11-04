# Reproduction

From `workers/research`:

```text
uv run python -m aqil_research.long_horizon.vwra_discovery
```

The command reads the local research database and `aqil_etf`.
It does not apply a hosted migration and it does not call the portfolio simulator.
A second run that reproduces the same artifact inserts nothing.

| Execution | Artifact hash |
| --- | --- |
| LH-X-008 | `5342e697307bab1a035533ffc087346c777596a81233e73c42f5a3f40a3b2b0c` |
| LH-X-009 | `882ff96372ff1af1ad4a49c0fc0907b5153032f724db60398933752467a33feb` |
| LH-X-010 | `47c80b5dd2402b88aa2578b0f60682e2246b1769d7459c1e3547e78f47493eaa` |
| LH-X-011 | `6495408b4a4136052fe8ff881d14b1c27648838851c17c1baafac80e0bfdfe4c` |
