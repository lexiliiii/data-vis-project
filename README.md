# Mapping U.S. Trade: Patterns, Shifts, and Global Events

CS 6730 Data Visualization project. It looks at how US goods trade has shifted between partner countries since 2006, and especially at where imports went once they left China after the 2018 tariffs.

```
.
├── index.html              # placeholder landing page
├── draft.html              # draft interactive visualization (D3 v7, loaded from a CDN)
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
    └── output/                      # all generated CSVs, PNGs, and cached API pulls
```

## Viewing the website

`draft.html` is self-contained apart from D3, which it loads from cdnjs, so you need an internet connection. You can open it straight in a browser, or serve the folder locally:

```bash
python -m http.server 8000
# then open http://localhost:8000/draft.html
```

## China share explorer

An interactive **Share trails / Supplier ribbons** section appears just before “China's decline is concentrated in a few product groups.” It uses eight selected HS2 categories from the existing 2006–2025 annual Comtrade extract, matching the rest of the page.

- Switch between **Share trails** and **Supplier ribbons**. Ribbons show China, Mexico, Vietnam, Taiwan, and all other suppliers as a 100% stacked bar; the year, selected category, and inflation setting are shared between views.
- Drag the year slider, or jump to a milestone year; marks animate from their previous positions and respect reduced-motion settings.
- Select a category to view its share history, change from 2017, dollar amounts, and sourced policy context as of the selected year-end.
- Turn on inflation adjustment to express dollar amounts in **2025 USD using CPI-U**. The share percentages stay unchanged. The 2025 CPI average uses 11 published months because October is unavailable.
- Quantity is disabled until specific products with comparable units are selected. Broad commodity groups cannot combine kilograms, item counts, and other units.

The chart renders in the browser using D3/SVG, with embedded data; it does not load saved images or call Python/API services at runtime. It remains usable by opening `draft.html` directly. Policy dates are selected context, not a complete tariff history, product-coverage mapping, or a causal estimate.

Downloaded sources, processed tables, and provenance are in [`data exploration/output/china_trade_explorer/`](data%20exploration/output/china_trade_explorer/README.md). Census monthly imports for consumption are stored separately and are not spliced into the annual Comtrade series. No API key is embedded in the page.

To refresh only this explorer's embedded data after rebuilding its processed source tables:

```bash
python "data exploration/output/china_trade_explorer/scripts/build_website_explorer.py"
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
