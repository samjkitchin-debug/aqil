# Founding design catalogue

**Status:** design register. These rows are not empirical results and this note is not Verified.

The three Downloads files are copied into `docs/research/long-horizon/founding-catalogue/`. They contain no adjusted prices and no credentials. The copies match the Downloads checksums. The files are not byte-identical, so all three are kept. Parsed fields that were compared agree. Nothing was silently dropped.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `aqil_long_horizon_scenarios_v1.json` | 829998 | `4c741b4ce40d5ab5ecee5f856653beb2d814f327c1fb7fea0d65cc9f9d62edc0` |
| `aqil_long_horizon_strategy_research_matrix_v1.xlsx` | 131542 | `c6abbe20bd15cbd23198a811dc54abe55d40925caf1cf0ea419e5de66a883ee1` |
| `aqil_long_horizon_scenarios_v1.csv` | 492482 | `e4a38f60f2178ddef84ea93f0472852abc6af1e05fa4ef18f7c935aca1b3ee4e` |

The JSON declares 309 signals, 618 scenarios, and 26 families. The parsed unique signal count is 309. The parsed unique scenario count is 618. JSON scenario rows: 618. CSV scenario rows: 618. Workbook scenario rows: 618. JSON versus CSV field mismatches: 0. Workbook scenario cell mismatches: 0. Workbook mechanism mismatches: 0. Identifier differences in either direction: none.

`Supported?` is `No` on every signal. Execution status is `Not executed` on every signal. That is the catalogue's own label. It is not a scientific result.

Workbook sheet row counts, including the header row:

| Sheet | Rows including header |
| --- | ---: |
| Start Here | 21 |
| Source & Limits | 7 |
| Signal Dictionary | 310 |
| Scenario Matrix | 619 |
| Control Policies | 13 |
| Historical Eras | 6 |
| Suite Roadmap | 18 |
| Scorecard Metrics | 21 |
| Run Registry Template | 51 |
| Event Ledger Schema | 21 |
| Nonnegotiable Checks | 19 |
| Research Dashboard | 30 |

Import writes one candidate row per source file. The same scenario identifier therefore exists once for each file that contains it. `empirical_result` is false. The 309 signals are not registered as hypotheses, because that would require inventing an economic rationale for each one. The only registered hypothesis is `LH-H-001`, and it is not one of the 618 catalogue scenarios.
