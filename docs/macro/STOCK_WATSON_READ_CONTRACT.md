# Stock–Watson read contract

**Scientific validation:** numerically verified against statsmodels after the initial state, with the full-sample likelihood difference explained in `docs/macro/dossiers/STOCK_WATSON_DFM.md`. Empirically evaluated on revised data only.

**Operational scheduling:** manual local refresh is implemented. The unattended Windows task is not registered. Hosted scheduling is off.

**Publication eligibility:** not eligible. `publication_allowed` is false.

**Latest available observation period:** July 2026. The balanced level sample ends at 2026-07-01 because real manufacturing and trade sales end there.

**Last execution timestamp:** 2026-10-25 00:31:12 UTC for the stored estimation run. A later filter update, if one exists, is a separate completed row with `update_kind` `filter_update`.

**Model version:** `0.1.0`.

**Fitted parameter version:** run `3f8c7611-c2a1-44a0-8c7e-01bebbfe9a8a`. Do not replace this row. A filter update keeps its parameters and its training moments.

**Input-data vintage:** `latest_revised` live retrievals. Not a real-time vintage.

**Current health:** the stored run is completed. A failed filter update is a `failed_method` row and is not the factor a reader should display. Read the latest `completed` row whose calculation contains `loadings_ip_income_sales_payroll`.

**Method:** `STOCK_WATSON_COINCIDENT_1988_MODERN_REFIT`

A frontend may read that research run. It must not treat the row as publishable.

The calculation JSON contains:

- `specification`, `sample_levels`, `growth_start`
- `loadings_ip_income_sales_payroll` in the order industrial production, real income excluding transfers, real manufacturing and trade sales, payrolls
- `factor_ar`, `idiosyncratic_ar`, `idiosyncratic_scale`, `log_likelihood`
- `filtered_factor`, one value per log-difference month beginning at `growth_start`
- `real_time`: false
- `sources`
- `moments`, the training-sample mean and scale

The filtered value is the model's scale after the industrial-production loading is kept positive. It is not a GDP growth rate and not a recession probability. The inputs are latest revised. The path is not a real-time historical vintage.

Input dataset ids:

- `fed.g17.IP.B50001.S`
- `bea.nipa.T20600.W875RX`
- `bea.nipa.U002BU.KPMT`
- `bls.ce.CES0000000001`

A later methodology may use the same run table with a different method id. Do not force those outputs into these field names.

Regression tolerance: filtered factor after index 20 within 1e-8 of an independent filter that uses the same parameters. Do not require the full-sample log likelihoods to match more tightly than 1 unless the initial-state timing is the same. Aqil's likelihood is authoritative for this run.
