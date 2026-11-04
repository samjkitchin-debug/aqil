# VWRA discovery

This note records a retrospective reconstruction on stored latest-revised inputs.
It is not a point-in-time study and it is not an investment signal.
No portfolio simulation was run. Nothing here is cleared for publication.

Specification hash `fbd066ab20efcd5978a7ae52cb43b3f3ef8e991db3f9d5a49608b061d863d7b2`.

| Execution | Artifact hash |
| --- | --- |
| LH-X-008 | `5342e697307bab1a035533ffc087346c777596a81233e73c42f5a3f40a3b2b0c` |
| LH-X-009 | `882ff96372ff1af1ad4a49c0fc0907b5153032f724db60398933752467a33feb` |
| LH-X-010 | `47c80b5dd2402b88aa2578b0f60682e2246b1769d7459c1e3547e78f47493eaa` |
| LH-X-011 | `6495408b4a4136052fe8ff881d14b1c27648838851c17c1baafac80e0bfdfe4c` |

Decision dates, macro periods, and market episodes are separate counts.
Overlapping month-ends are not independent trials.

Reproduction: `uv run python -m aqil_research.long_horizon.vwra_discovery`.

A second run inserts nothing when the artifact hash matches.
