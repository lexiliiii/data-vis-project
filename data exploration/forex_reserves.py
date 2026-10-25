"""
Global foreign exchange reserves by country, last 20 years, with a gold /
non-gold composition split.

Source
------
World Bank World Development Indicators (api.worldbank.org) - free, no API key.
    FI.RES.TOTL.CD   Total reserves (includes gold), current US$
    FI.RES.XGLD.CD   Total reserves minus gold, current US$
Gold's dollar value is derived as TOTL - XGLD (the World Bank values monetary
gold at market price, per the IMF BPM6 reserve-asset methodology, so this
difference is a real, published quantity - not an estimate we're inventing).

A caveat worth stating up front: no public source breaks an individual
country's reserves down *by currency* (USD / EUR / JPY / CNY / ...). The
IMF's COFER survey collects exactly that split, but for confidentiality
reasons only publishes it in aggregate - advanced economies, emerging
markets, and the world total - never by individual reporting country. So
"composition" here means the one split that *is* published per country:
gold vs. everything else (foreign exchange holdings, SDRs, and the reserve
position in the IMF, which the World Bank lumps together and does not
separate further by country).

Outputs (written to --outdir)
------------------------------
reserves_by_country_long.csv     one row per (year, country): total_reserves_usd,
                                  gold_usd, non_gold_usd, gold_share
reserves_top_holders_summary.csv countries ranked by latest-year total reserves

Usage
-----
    pip install requests pandas
    python forex_reserves.py                        # 2006-2025, all countries
    python forex_reserves.py --start 2005 --end 2024
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

WB_BASE = "https://api.worldbank.org/v2"
INDICATORS = {
    "total_reserves_usd": "FI.RES.TOTL.CD",   # includes gold
    "non_gold_usd": "FI.RES.XGLD.CD",         # excludes gold
}


def get_json(url: str, params: dict, retries: int = 5, backoff: float = 2.0):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == retries:
                raise
            wait = backoff * attempt
            print(f"    retry {attempt}/{retries} after error: {e} (sleep {wait:.0f}s)")
            time.sleep(wait)


def fetch_country_metadata() -> pd.DataFrame:
    """iso3 -> country name, filtered down to real countries (drops WB's
    regional/income-group aggregates, which share the /country endpoint)."""
    print("Fetching country list ...")
    rows = []
    page = 1
    while True:
        js = get_json(f"{WB_BASE}/country", {"format": "json", "per_page": 400, "page": page})
        meta, data = js[0], js[1] or []
        rows.extend(data)
        if page >= meta["pages"]:
            break
        page += 1
    df = pd.DataFrame(rows)
    df["region_id"] = df["region"].apply(lambda r: r.get("id"))
    df = df[df["region_id"] != "NA"]  # "NA" region = aggregate, not a country
    df = df.rename(columns={"id": "iso3", "name": "country_name"})
    print(f"  {len(df)} countries (aggregates excluded)")
    return df[["iso3", "country_name"]]


def fetch_indicator(indicator: str, start: int, end: int) -> pd.DataFrame:
    print(f"Fetching {indicator} for {start}-{end} ...")
    rows = []
    page = 1
    while True:
        js = get_json(
            f"{WB_BASE}/country/all/indicator/{indicator}",
            {"date": f"{start}:{end}", "format": "json", "per_page": 20000, "page": page},
        )
        meta, data = js[0], js[1] or []
        rows.extend(data)
        if page >= meta.get("pages", 1):
            break
        page += 1
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["iso3", "year", "value"])
    df = df.rename(columns={"countryiso3code": "iso3", "date": "year"})
    df["year"] = df["year"].astype(int)
    df = df[["iso3", "year", "value"]].dropna(subset=["value"])
    print(f"  {len(df)} observations")
    return df


def build_outputs(start: int, end: int, outdir: Path) -> None:
    countries = fetch_country_metadata()

    total = fetch_indicator(INDICATORS["total_reserves_usd"], start, end)
    non_gold = fetch_indicator(INDICATORS["non_gold_usd"], start, end)

    df = total.merge(non_gold, on=["iso3", "year"], how="outer",
                      suffixes=("_total", "_nongold"))
    df = df.rename(columns={"value_total": "total_reserves_usd",
                             "value_nongold": "non_gold_usd"})
    df = df.merge(countries, on="iso3", how="inner")  # drops any remaining aggregates

    df["gold_usd"] = (df["total_reserves_usd"] - df["non_gold_usd"]).clip(lower=0)
    df["gold_share"] = (df["gold_usd"] / df["total_reserves_usd"]).where(
        df["total_reserves_usd"] > 0)

    df = df.sort_values(["country_name", "year"])[
        ["year", "iso3", "country_name", "total_reserves_usd",
         "gold_usd", "non_gold_usd", "gold_share"]]

    outdir.mkdir(parents=True, exist_ok=True)
    long_path = outdir / "reserves_by_country_long.csv"
    df.to_csv(long_path, index=False)

    latest_year = df["year"].max()
    summary = (df[df["year"] == latest_year]
               .dropna(subset=["total_reserves_usd"])
               .sort_values("total_reserves_usd", ascending=False)
               [["country_name", "iso3", "total_reserves_usd", "gold_usd", "gold_share"]])
    summary.to_csv(outdir / "reserves_top_holders_summary.csv", index=False)

    print(f"\nWrote {len(df):,} rows -> {long_path}")
    print(f"Years: {df.year.min()}-{df.year.max()}, countries: {df.country_name.nunique()}")
    print(f"\nTop 10 reserve holders, {latest_year} (USD bn):")
    top = summary.head(10).copy()
    top["total_reserves_usd"] = (top["total_reserves_usd"] / 1e9).round(1)
    top["gold_usd"] = (top["gold_usd"] / 1e9).round(1)
    top["gold_share"] = (top["gold_share"] * 100).round(1).astype(str) + "%"
    print(top.to_string(index=False))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--end", type=int, default=2025,
                    help="last year (default 2025, the latest full year)")
    p.add_argument("--start", type=int, default=None,
                    help="first year (default: end - 19, i.e. 20 years)")
    p.add_argument("--outdir", type=Path, default=Path(__file__).parent / "output")
    args = p.parse_args()

    start = args.start if args.start is not None else args.end - 19
    print(f"Extracting global forex reserves, {start}-{args.end}")

    build_outputs(start, args.end, args.outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
