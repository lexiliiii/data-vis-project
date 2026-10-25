# China trade explorer data

This package supplies the Share trails / Supplier ribbons explorer in `draft.html`. The page embeds the annual Comtrade data, CPI factors, and policy milestones; the Census monthly series is saved separately for future exploration.

## What is ready

- **Annual trade, 2006–2025:** 46,287 source rows covering 16 HS2 categories. Reused from the project's existing UN Comtrade extract, not freshly downloaded. Its original retrieval date is unknown. A byte-for-byte snapshot and SHA-256 hash are retained.
- **Category summaries:** 320 category/year rows, using the reported World record as denominator, with China share, leading supplier, and HHI.
- **Inflation:** freshly downloaded BLS CPI-U `CUUR0000SA0`, all items, U.S. city average, not seasonally adjusted. 240 month slots; 239 observed values. October 2025 is missing in the official source and remains missing here.
- **Policy context:** downloaded official source pages/PDFs plus 10 selected dated milestones. These are not a complete tariff-rate history. Detailed product/exclusion matching is not implemented.

## Census monthly data: downloaded and validated

**470,973 rows in 256 cached responses**, covering January 2010–December 2025 for all 16 HS2 categories, all reported suppliers, totals, and country groups. There are **3,072 category/month summaries**, with China and the reported World total present in every month. No download gaps or duplicate category/month/country keys were found. Individual-country sums reconcile exactly with reported World totals after excluding overlapping regional groups.

The table includes imports-for-consumption value and calculated duties. Product quantities are not downloaded: choose exact HTS10 products and review their historical codes and units before enabling quantity comparisons.

The resumable downloader is `scripts/download_census_trade.py`. To refresh or extend the saved data:

1. Request a free key at https://api.census.gov/data/key_signup.html and activate it through the email from Census.
2. Keep the key outside this repository, in a text file containing only the key. Do not commit the key or paste it in a chat.
3. From this directory, run:

```sh
python3 scripts/download_census_trade.py --key-file /absolute/path/to/private/key.txt
```

Alternatively, supply `CENSUS_API_KEY` through your shell environment. The downloader never saves the key in data, provenance, or logs. `--plan` shows scope without network access or a key.

Default scope: monthly imports for consumption, 2010–2025, 16 HS2 categories, all reported suppliers and total records. Each category/year is cached separately. Resume an interrupted download with the same command. Requests can take several minutes. Authenticated downloads were verified. Up to four requests run concurrently; API errors remain visible instead of being turned into empty data.

For quantity, add `--products` followed by exact 10-digit HTS codes after choosing the products to compare. The downloader retrieves value, quantity, units, and flags together. Historical code changes and units must be reviewed before comparison. Category-level quantity is not produced because unlike units cannot be added. A raw zero with a missing-value flag is not an observed zero.

The Census files use **imports for consumption**. The legacy Comtrade files use the project's existing U.S.-reported import series. Do not splice them into one unmarked time series.

## Main files

| Path | Purpose |
| --- | --- |
| `processed/census_monthly_categories.csv` | 470,973 Census rows with original names and values; includes overlapping country groups |
| `processed/census_monthly_category_summary.csv` | 3,072 monthly China/World summaries, calculated-duty ratios, and CPI-adjusted values |
| `raw/census/` | 256 original Census response tables |
| `metadata/census_download_status.json` | Download scope, key-free source URLs, hashes, and gaps |
| `metadata/census_validation.json` | Coverage, uniqueness, hashes, and reconciliation checks |
| `metadata/census_world_reconciliation.csv` | Monthly World totals versus individual-country sums |
| `metadata/website_validation.json` | Browser checks for the new section and existing charts |
| `processed/annual_category_summary.csv` | 320 category/year summaries for charting |
| `processed/annual_trade_by_supplier.csv` | All source partners, including World, with nominal and CPI-adjusted values |
| `processed/cpi_monthly_2006_2025.csv` | Monthly CPI, missing flags, and factors to 2025 dollars |
| `processed/cpi_annual_2006_2025.csv` | Annual mean CPI, observed-month counts, and factors |
| `processed/inflation_factors.json` | Compact factors for the browser switch |
| `processed/policy_events.json` / `.csv` | Selected policy/context dates with direct source URLs |
| `raw/bls/` | Unmodified BLS API responses |
| `raw/existing_comtrade/` | Snapshot of the pre-existing trade CSV |
| `raw/policy/` | Official notices, tariff annexes, and source pages |
| `metadata/sources.json` | URLs, retrieval times, hashes, download/reuse status |
| `metadata/status.json` | Ready, missing, and incomplete parts of the package |
| `metadata/world_total_reconciliation.csv` | World totals versus the sum of reported partners |
| `metadata/validation.json` | Validation results for this package |
| `DATA_DICTIONARY.md` | Fields, interpretation, and limits |

## Inflation method

`value_2025_usd = nominal_value × CPI_2025 / CPI_observation_period`

For annual trade, use each year's annual mean CPI. The 2025 base is **321.943**. Annual means use published nonmissing months, rounded to three decimals; 2025 has 11 observations because BLS could not collect October data. The monthly October 2025 adjustment factor stays blank; no value is interpolated.

The UI label is **2025 USD · CPI-U**. This adjusts general U.S. purchasing power; it is not a product-specific import-price deflator and does not estimate physical quantities. With the same factor applied to China and World in a given annual observation, the percentage share is unchanged. Only dollar amounts change.

## Policy coverage

The downloaded notices contain product lists, proposed actions, exclusions/revisions, and effective dates. Those sections must be distinguished before mapping codes. For example, the List 1 notice includes a proposed additional list; List 4B should not be treated as implemented merely because it appears in a notice. The UI events distinguish announcement, signing, effective date, and global shock.

`affected_hts_codes` is null and `coverage_status` is `not_yet_mapped`. A displayed rate is an additional duty for covered products in a historical action, not a total tariff or a rate for every product in an HS2 category. Exclusions, Section 232, base duties, and the full sequence of 2025 changes have not been resolved. Do not use this milestone dataset as a tariff calculator or as evidence of causation.

## Rebuilding public data

```sh
python3 scripts/prepare_public_data.py
```

The builder reuses cached public responses and the existing source CSV, recalculates the tables, and retries previously unavailable source files. The source trade CSV must remain one directory above this package. Python's standard library is sufficient, with a working CA certificate store. TLS verification remains enabled. The public-data builder preserves the separate Census download status.

After a Census download, rebuild and validate its monthly summaries:

```sh
python3 scripts/prepare_census_summary.py
```

To refresh only the annual explorer's embedded data in `draft.html`:

```sh
python3 scripts/build_website_explorer.py
```

This does not replace any of the original page's charts or their embedded data.

Official references:

- https://www.census.gov/data/developers/data-sets/international-trade.html
- https://api.census.gov/data/timeseries/intltrade/imports/hs/variables.html
- https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm
- https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm
- https://ustr.gov/issue-areas/enforcement/section-301-investigations/tariff-actions
- https://hts.usitc.gov/download/archive
