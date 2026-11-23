# Where US Imports Went

Final project for CS 6730 Data Visualization. This interactive data story examines how US goods imports changed from 2006 to 2025. It focuses on China's declining share, the growth of Mexico, Vietnam, and Taiwan, and the product categories that still depend heavily on one supplier.

## Project links

- **Public website:** https://lexiliiii.github.io/data-vis-project/
- **Three-minute screencast:** https://drive.google.com/file/d/1SXZ0tkBRVgUP3POB7ge9NqrPbbdw76Dt/view?usp=drive_link
- **Source repository:** https://github.com/lexiliiii/data-vis-project

## What is included

| Path | Contents |
|---|---|
| `index.html` | Final data story, page layout, styles, embedded story data, and D3 interaction code |
| `supplier-dashboard-data.js` | Generated data payload used by the linked supplier dashboard |
| `data exploration/` | Our Python scripts for downloading, cleaning, analyzing, and visualizing the data |
| `data exploration/output/` | Cleaned data, cached API results, generated figures, and source documentation |
| `README.md` | Project overview, instructions, data sources, and interface notes |

`index.html`, `supplier-dashboard-data.js`, and the Python files in `data exploration/` are project code. Generated CSV, JSON, and image files are project outputs. D3, Google Fonts, and the Python packages listed below are third-party libraries.

```
.
├── index.html              # final interactive visualization (D3 v7, loaded from a CDN)
├── supplier-dashboard-data.js  # compact generated payload for the sourcing dashboard
└── data exploration/
    ├── us_trading_partners.py       # fetch: US trade totals by partner (UN Comtrade / Census)
    ├── us_trade_by_commodity.py     # fetch: US trade by HS2 chapter for 9 key partners
    ├── fetch_commodity_partners.py  # fetch: US imports for 16 chapters from every partner
    ├── forex_reserves.py            # fetch: FX reserves by country (World Bank)
    ├── plot_top10_line_charts.py    # plot: top-10 partners total trade + trade balance
    ├── plot_top_reserves_line.py    # plot: top-10 FX reserve holders
    ├── where_did_it_go.py           # plot: change in import share, 2017 vs 2025
    ├── storyboard_sketch.py         # plot: 5-panel data storyboard
    ├── build_site_data.py           # build: compact JSON for the website
    ├── build_supplier_dashboard_data.py # build: sourcing dashboard payload
    └── output/                      # all generated CSVs, PNGs, and cached API pulls
```

## Run the final website

Keep `index.html` and `supplier-dashboard-data.js` in the same directory. The page also loads D3 v7 and web fonts from public CDNs, so an internet connection is required for the complete presentation.

Open `index.html` directly, or serve the project directory locally:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000/.

## Interface guide

- **Select a period:** Use the From/To menus, the 2017–2025 preset, or drag across the opening chart. The selected period updates the partner ranking and supplier dashboard.
- **Explore product categories:** In “Watch America's reliance on China change,” select a product row and move the year slider. Use the view buttons to compare China with 2017 or show all suppliers.
- **Use the guided examples:** Expand “Try the explorer” or “Try the linked charts” for one-click interaction examples.
- **Read linked feedback:** Text below the controls reports the active years and identifies the charts that changed.
- **Inspect supplier concentration:** In the supplier dashboard, choose a commodity to update all three panels. The same commodity is selected in the final concentration comparison.
- **Open the detailed comparison:** The 16-product concentration chart is collapsed by default. Select “Open comparison” near the end of the story to display it.
- **View exact values:** Select “View data table” below a chart when a table is available.
- **Keyboard use:** Interactive bubbles and buttons can be reached with Tab and activated with Enter or Space.

## China share explorer

An interactive **Share trails / Supplier ribbons** section appears after the partner-ranking story. It uses eight selected HS2 categories from the existing 2006–2025 annual Comtrade extract, matching the rest of the page.

- Switch between **Share trails** and **Supplier ribbons**. Ribbons show China, Mexico, Vietnam, Taiwan, and all other suppliers as a 100% stacked bar; the year and selected category are shared between views.
- Drag the year slider, or jump to a milestone year; marks animate from their previous positions and respect reduced-motion settings.
- Select a category to view its share history, change from 2017, dollar amounts, and sourced policy context as of the selected year-end.

The chart renders in the browser using D3/SVG, with embedded data; it does not load saved images or call Python/API services at runtime. It remains usable by opening `index.html` directly. Policy dates are selected context, not a complete tariff history, product-coverage mapping, or a causal estimate.

Downloaded sources, processed tables, and provenance are in [`data exploration/output/china_trade_explorer/`](data%20exploration/output/china_trade_explorer/README.md). Census monthly imports for consumption are stored separately and are not spliced into the annual Comtrade series. No API key is embedded in the page.

To refresh only this explorer's embedded data after rebuilding its processed source tables:

```bash
python "data exploration/output/china_trade_explorer/scripts/build_website_explorer.py"
```

## Supplier sourcing dashboard

The linked sourcing dashboard near the end of the story uses all 16 HS2 categories and the full 2006–2025 partner history. Its commodity selector is linked to the final concentration chart. Its year controls are linked to the opening chart and partner ranking, while the product explorer follows the selected end year.

The compact browser payload keeps suppliers that reached at least 1% of a category's US import market in any year. Smaller suppliers remain included in `Other`; yearly leaders and HHI are calculated from every partner row before compaction.

To rebuild the payload after refreshing `us_imports_by_chapter_partner.csv`:

```bash
python "data exploration/build_supplier_dashboard_data.py"
```

## Running the data scripts

### Setup

You need Python 3.10 or newer (the scripts were developed on 3.11/3.12).

```bash
cd "data exploration"
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install requests pandas numpy matplotlib
```

Run every script from inside `data exploration/`. Some of them import from each other (for example, `fetch_commodity_partners.py` imports `us_trade_by_commodity.py`).

### API keys

Comtrade supports public requests without a key; a key raises its rate limits. Census data requests require an activated API key:

| Variable | Used by | Get one at |
|---|---|---|
| `COMTRADE_API_KEY` | `us_trading_partners.py`, `us_trade_by_commodity.py`, `fetch_commodity_partners.py` | https://comtradedeveloper.un.org (free) |
| `CENSUS_API_KEY` | `us_trading_partners.py --source census`, `output/china_trade_explorer/scripts/download_census_trade.py` | https://api.census.gov/data/key_signup.html |

Without `COMTRADE_API_KEY` the scripts use the public Comtrade preview endpoint and wait about 2.5 s between calls, so a full pull can take a while.

```bash
# PowerShell
$env:COMTRADE_API_KEY = "your-key"
# bash
export COMTRADE_API_KEY="your-key"
```

### Pipeline

`output/` already holds the results of a full run, so you can skip straight to the plotting scripts. To rebuild everything, run the steps in this order:

```bash
# 1. Fetch raw data (needs network)
python us_trading_partners.py          # -> us_trade_partners_long.csv, us_trade_partners_total_wide.csv,
                                       #    us_top_partners_summary.csv
python fetch_commodity_partners.py     # -> commodity_partners/hs<NN>.csv, us_imports_by_chapter_partner.csv
python forex_reserves.py               # -> reserves_by_country_long.csv, reserves_top_holders_summary.csv
python us_trade_by_commodity.py        # -> us_trade_by_commodity_long.csv, china_shift_by_chapter.csv,
                                       #    china_import_share_by_chapter.csv, commodity_shift.png

# 2. Make the charts (offline; they read the CSVs from step 1)
python plot_top10_line_charts.py       # -> us_top10_total_trade_line.png, us_top10_trade_balance_line.png
python plot_top_reserves_line.py       # -> top10_forex_reserves_line.png
python where_did_it_go.py              # -> where_did_it_go.png
python storyboard_sketch.py            # -> data_storyboard.png

# 3. Build the website's JSON
python build_site_data.py              # -> ../site/data/{partners,commodities,events}.json
```

All outputs go to `data exploration/output/` unless noted. `build_site_data.py` writes to `site/data/` at the repo root and creates the folder if it doesn't exist.

### Useful options

Every script that takes arguments supports `--help`.

```bash
python us_trading_partners.py --start 2005 --end 2024
python us_trading_partners.py --source census --start 2013     # legacy Census totals workflow
python us_trade_by_commodity.py --years 2017 2019 2025 --no-plot
python fetch_commodity_partners.py --chapters 85 72 --years 2017 2025
python forex_reserves.py --start 2005 --end 2024
python plot_top10_line_charts.py --show                        # also open interactive windows
```

`fetch_commodity_partners.py` saves a checkpoint after every API call to `output/commodity_partners/`. If it's interrupted, just run it again and it will skip the (chapter, year) pairs it already has.

## Data sources

- **UN Comtrade** reports US-reported goods trade, in current USD. Comtrade lists Taiwan as "Other Asia, nes", and the scripts relabel it as Taiwan.
- **US Census Bureau International Trade API** supplies the separate monthly HS import package from January 2010 onward. The legacy totals-script example above uses 2013 onward.
- **World Bank WDI** provides `FI.RES.TOTL.CD` and `FI.RES.XGLD.CD` for total reserves and reserves minus gold. No public source breaks down an individual country's reserves by currency, so the only split available is gold vs. non-gold.