# Data dictionary

## Annual trade

- `year`: calendar year, 2006–2025.
- `hs2`: two-digit commodity chapter. Preserve as a string; these are commodities, not NAICS industries.
- `chapter`: description from the existing extract.
- `partner_code`: UN Comtrade code. `0` is World; `156` is China. This is not a Census country code.
- `partner_name`: original source name. `Other Asia, nes` is retained in raw data (displayed as Taiwan in the design).
- `imports_usd_nominal`: source import value in current USD.
- `imports_usd_2025_cpi`: nominal value times the annual factor, rounded to cents.
- `cpi_factor_to_2025`: 321.943 divided by that year's CPI annual mean.
- `source`, `trade_basis`: provenance and measurement notes.

World rows and individual partners coexist in the detailed table. Never sum both together. A reported World row is used directly for category denominators. Detailed source rows are preserved without silently converting missing product quantities into values.

## Category summaries

- `china_imports_usd_nominal`, `world_imports_usd_nominal`: same-category, same-year values for China and World.
- `china_imports_usd_2025_cpi`, `world_imports_usd_2025_cpi`: annual CPI purchasing-power adjustment of the corresponding amounts.
- `china_share_pct`: 100 × China / World. General CPI adjustment cancels within each annual ratio.
- `top_supplier`, `top_supplier_share_pct`: largest non-World source record and its share.
- `hhi`: sum of squared non-World supplier shares times 10,000. Relies on the partner coverage in the original extract. Reconciliation differences are reported separately.

## Inflation

- `series_id`: `CUUR0000SA0` (CPI-U, all items, U.S. city average, not seasonally adjusted).
- `cpi`: monthly index level, 1982–84=100; blank when unavailable.
- `missing`, `note`: explicit missing status and original BLS footnote text.
- `cpi_annual_average`: mean of published nonmissing monthly index levels, rounded to three decimals.
- `months_observed`, `missing_months`: annual completeness; 2025 has 11 observed months, with October missing.
- `factor_to_2025_usd`: base annual CPI 321.943 divided by the relevant monthly/annual CPI. Missing monthly CPI gives a missing factor.

## Policy events

- `id`, `title`, `description`: hand-curated identifier and concise historical description.
- `date`, `date_type`: the event date and whether it is effective, announced, signed, or a global shock. Do not substitute publication date for effective date.
- `additional_rate_percent`: historical additional rate on the covered list, where relevant; null otherwise. Not a complete tariff burden.
- `affected_hts_codes`: null until code coverage is reviewed and mapped.
- `coverage_status`: `not_yet_mapped`.
- `source_url`, `local_source`, `source_downloaded`: original source and saved copy.
- `scope_note`: explicitly limits the timeline to selected milestones and prohibits interpreting chronology as causation.

## Census monthly files (2010–2025)

The script retains returned column names and original flags, rather than claiming unverified normalized units. `CON_VAL_MO` and `CAL_DUT_MO` are imports-for-consumption value and calculated duties. Quantity is `CON_QY1_MO` / `CON_QY2_MO`, with corresponding `UNIT_QY1` / `UNIT_QY2` and flags. Use the exact same product code, period, and unit for China and World quantity shares. Handle code revisions before linking a product across years. Totals and country groups can be present; do not sum every returned country row indiscriminately.


The downloaded table has 470,973 rows. `time` is `YYYY-MM`; `I_COMMODITY` is a two-digit chapter; `COMM_LVL` is `HS2`. `CTY_CODE` is a Census code, not a Comtrade code: `5700` is China and `-` is the reported World total. Numeric codes below 1000 are aggregate country groups in this extract and overlap individual countries. Exclude them when reconciling supplier sums.

`census_monthly_category_summary.csv` contains 3,072 category/month observations:

- `china_imports_usd_nominal`, `world_imports_usd_nominal`: monthly imports for consumption, current USD.
- `china_share_pct`: China value divided by the same-month reported World total, times 100.
- `china_calculated_duties_usd`: Census `CAL_DUT_MO` for China.
- `china_effective_duty_pct`: calculated duties divided by imports-for-consumption value, times 100; blank when the denominator is zero. This aggregate ratio reflects composition and exemptions; it is not a statutory tariff or a causal estimate.
- `cpi_factor_to_2025`: 2025 annual CPI (321.943) divided by that month's CPI.
- `china_imports_usd_2025_cpi`, `world_imports_usd_2025_cpi`: monthly nominal values times the CPI factor, rounded to cents.
- `cpi_missing`: true for October 2025 in all 16 categories; adjusted dollar amounts stay blank for those observations. Nominal data and shares remain available.

The website deliberately uses the annual Comtrade table for its 2006–2025 range. Census is a distinct measurement series and is not mixed into that timeline.

## Website supplier ribbons

The embedded `supplier_order` is China, Mexico, Vietnam, Taiwan, Other. Each category/year has `suppliers`, five percentage shares in that order, calculated from `annual_trade_by_supplier.csv` using the reported World total. Other is the remainder after the four named suppliers; the five shares sum to 100%. Taiwan uses Comtrade code 490 (Other Asia, nes). The same annual data, category selection, and CPI controls are shared with Share trails. CPI adjustment does not change supplier shares.
