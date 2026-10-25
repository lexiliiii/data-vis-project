"""
US trading partners: exports, imports and total trade value by partner country,
for the last 20 years.

Sources
-------
comtrade (default)  UN Comtrade API, reporter = USA (842), commodity = TOTAL.
                    Covers every year in the window. Works without a key via the
                    public "preview" endpoint (max 500 rows/call, rate-limited);
                    set COMTRADE_API_KEY (free at comtradedeveloper.un.org) to use
                    the full endpoint instead.
census              US Census Bureau international trade API. The official US
                    figures, but the timeseries only starts in 2013, so it can't
                    cover 20 years on its own. Useful for cross-checking.
                    Optional CENSUS_API_KEY raises the rate limit.

Outputs (written to --outdir)
-------
us_trade_partners_long.csv    one row per (year, partner): exports, imports,
                              total_trade, balance (all in current USD)
us_trade_partners_total_wide.csv  partner x year matrix of total trade
us_top_partners_summary.csv   partners ranked by cumulative trade over the window

Usage
-----
    pip install requests pandas
    python us_trading_partners.py                          # 2006-2025, Comtrade
    python us_trading_partners.py --start 2005 --end 2024
    python us_trading_partners.py --source census --start 2013
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

USA_M49 = 842
COMTRADE_PREVIEW = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
COMTRADE_FULL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
CENSUS_BASE = "https://api.census.gov/data/timeseries/intltrade"

# Comtrade partner codes that are aggregates / not real countries.
COMTRADE_NON_COUNTRY = {
    0,    # World
    97,   # EU-28 / EU aggregate
    290,  # Northern Africa, nes
    471,  # CACM, nes
    473,  # LAIA, nes
    490,  # Other Asia, nes  (in practice = Taiwan for many reporters; kept below)
    527,  # Oceania, nes
    568,  # Other Europe, nes
    577,  # Other Africa, nes
    636,  # Rest of America, nes
    637,  # North America and Central America, nes
    697,  # Europe EFTA, nes
    837,  # Bunkers
    838,  # Free zones
    839,  # Special categories
    879,  # Western Asia, nes
    899,  # Areas, nes
}
# 490 "Other Asia, nes" is how Comtrade reports Taiwan - keep it as a partner.
COMTRADE_NON_COUNTRY.discard(490)


def get_json(url: str, params: dict, headers: dict | None = None,
             retries: int = 5, backoff: float = 3.0):
    """GET with retry/backoff for rate limits and transient errors."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=60)
            if r.status_code == 204:          # Census: no data for that query
                return None
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == retries:
                raise
            wait = backoff * attempt
            print(f"    retry {attempt}/{retries} after error: {e} (sleep {wait:.0f}s)")
            time.sleep(wait)


# --------------------------------------------------------------------------- #
# UN Comtrade
# --------------------------------------------------------------------------- #
def fetch_comtrade_year(year: int, flow: str, api_key: str | None) -> pd.DataFrame:
    """flow: 'X' (exports) or 'M' (imports). Returns partner_code, partner_name, value."""
    params = {
        "reporterCode": USA_M49,
        "period": year,
        "flowCode": flow,
        "cmdCode": "TOTAL",
        "partner2Code": 0,       # no second partner breakdown
        "customsCode": "C00",    # all customs procedures
        "motCode": 0,            # all modes of transport
        "includeDesc": "true",
    }
    if api_key:
        url, headers = COMTRADE_FULL, {"Ocp-Apim-Subscription-Key": api_key}
    else:
        url, headers = COMTRADE_PREVIEW, None

    js = get_json(url, params, headers)
    rows = (js or {}).get("data") or []
    if not rows:
        return pd.DataFrame(columns=["partner_code", "partner_name", "value"])

    df = pd.DataFrame(rows)
    df = df.rename(columns={"partnerCode": "partner_code",
                            "partnerDesc": "partner_name",
                            "primaryValue": "value"})
    df = df[~df["partner_code"].isin(COMTRADE_NON_COUNTRY)]
    return df[["partner_code", "partner_name", "value"]]


def extract_comtrade(years: list[int]) -> pd.DataFrame:
    api_key = os.getenv("COMTRADE_API_KEY")
    print(f"Source: UN Comtrade ({'full API' if api_key else 'public preview'})")
    pause = 1.0 if api_key else 2.5
    frames = []
    for y in years:
        per_flow = {}
        for flow, col in (("X", "exports_usd"), ("M", "imports_usd")):
            print(f"  {y} {col.split('_')[0]} ...", end=" ", flush=True)
            d = fetch_comtrade_year(y, flow, api_key)
            print(f"{len(d)} partners")
            per_flow[col] = d.rename(columns={"value": col})
            time.sleep(pause)
        merged = per_flow["exports_usd"].merge(
            per_flow["imports_usd"], on=["partner_code", "partner_name"], how="outer")
        merged["year"] = y
        frames.append(merged)
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- #
# US Census Bureau (2013+)
# --------------------------------------------------------------------------- #
# Census country codes are 4 digits; aggregates start with '0' (e.g. 0003 = EU)
# or end in 'XXX' (continents), and '-' is the world total.
CENSUS_COUNTRY_RE = re.compile(r"^[1-7]\d{3}$")


def fetch_census_year(year: int, flow: str, api_key: str | None) -> pd.DataFrame:
    """Annual totals = year-to-date value as of December."""
    if flow == "exports":
        val_col = "ALL_VAL_YR"          # total exports (domestic + foreign), f.a.s.
    else:
        val_col = "GEN_VAL_YR"          # general imports, customs value
    params = {"get": f"CTY_CODE,CTY_NAME,{val_col}", "time": f"{year}-12"}
    if api_key:
        params["key"] = api_key
    js = get_json(f"{CENSUS_BASE}/{flow}/hs", params)
    if not js:
        return pd.DataFrame(columns=["partner_code", "partner_name", "value"])

    df = pd.DataFrame(js[1:], columns=js[0])
    df = df[df["CTY_CODE"].str.match(CENSUS_COUNTRY_RE)]
    df["value"] = pd.to_numeric(df[val_col], errors="coerce")
    df = (df.rename(columns={"CTY_CODE": "partner_code", "CTY_NAME": "partner_name"})
            .groupby(["partner_code", "partner_name"], as_index=False)["value"].sum())
    return df


def extract_census(years: list[int]) -> pd.DataFrame:
    api_key = os.getenv("CENSUS_API_KEY")
    if min(years) < 2013:
        print("  note: Census timeseries starts in 2013; earlier years will be empty.")
    print("Source: US Census Bureau")
    frames = []
    for y in years:
        per_flow = {}
        for flow in ("exports", "imports"):
            print(f"  {y} {flow} ...", end=" ", flush=True)
            d = fetch_census_year(y, flow, api_key)
            print(f"{len(d)} partners")
            per_flow[flow] = d.rename(columns={"value": f"{flow}_usd"})
            time.sleep(0.5)
        merged = per_flow["exports"].merge(
            per_flow["imports"], on=["partner_code", "partner_name"], how="outer")
        merged["year"] = y
        frames.append(merged)
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_outputs(df: pd.DataFrame, outdir: Path) -> None:
    df = df.copy()
    df[["exports_usd", "imports_usd"]] = df[["exports_usd", "imports_usd"]].fillna(0)
    df["total_trade_usd"] = df["exports_usd"] + df["imports_usd"]
    df["trade_balance_usd"] = df["exports_usd"] - df["imports_usd"]

    # Partner names occasionally change spelling across years; use the latest.
    latest_name = (df.sort_values("year").groupby("partner_code")["partner_name"].last())
    df["partner_name"] = df["partner_code"].map(latest_name)

    # Rank within each year
    df["rank_in_year"] = (df.groupby("year")["total_trade_usd"]
                            .rank(ascending=False, method="min").astype(int))
    df = df.sort_values(["year", "rank_in_year"])[
        ["year", "partner_code", "partner_name", "exports_usd", "imports_usd",
         "total_trade_usd", "trade_balance_usd", "rank_in_year"]]

    outdir.mkdir(parents=True, exist_ok=True)
    long_path = outdir / "us_trade_partners_long.csv"
    df.to_csv(long_path, index=False)

    wide = (df.pivot_table(index=["partner_code", "partner_name"], columns="year",
                           values="total_trade_usd", aggfunc="sum")
              .reset_index())
    wide.to_csv(outdir / "us_trade_partners_total_wide.csv", index=False)

    summary = (df.groupby(["partner_code", "partner_name"], as_index=False)
                 .agg(years_reported=("year", "nunique"),
                      exports_usd=("exports_usd", "sum"),
                      imports_usd=("imports_usd", "sum"),
                      total_trade_usd=("total_trade_usd", "sum"))
                 .sort_values("total_trade_usd", ascending=False))
    summary["share_of_us_trade"] = summary["total_trade_usd"] / summary["total_trade_usd"].sum()
    summary.to_csv(outdir / "us_top_partners_summary.csv", index=False)

    print(f"\nWrote {len(df):,} rows -> {long_path}")
    print(f"Years: {df.year.min()}-{df.year.max()}, partners: {df.partner_code.nunique()}")
    print("\nTop 10 partners by cumulative total trade (USD bn):")
    top = summary.head(10)[["partner_name", "total_trade_usd", "share_of_us_trade"]].copy()
    top["total_trade_usd"] = (top["total_trade_usd"] / 1e9).round(1)
    top["share_of_us_trade"] = (top["share_of_us_trade"] * 100).round(1).astype(str) + "%"
    print(top.to_string(index=False))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", choices=["comtrade", "census"], default="comtrade")
    p.add_argument("--end", type=int, default=2025,
                   help="last year (default 2025, the latest full year)")
    p.add_argument("--start", type=int, default=None,
                   help="first year (default: end - 19, i.e. 20 years)")
    p.add_argument("--outdir", type=Path, default=Path(__file__).parent / "output")
    args = p.parse_args()

    start = args.start if args.start is not None else args.end - 19
    years = list(range(start, args.end + 1))
    print(f"Extracting US trade by partner, {years[0]}-{years[-1]}")

    raw = extract_comtrade(years) if args.source == "comtrade" else extract_census(years)
    if raw.empty:
        print("No data returned - check network access / API keys.", file=sys.stderr)
        return 1
    build_outputs(raw, args.outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
