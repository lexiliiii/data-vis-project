"""
US imports by HS2 chapter from EVERY partner country, 2006-2025.

Companion to us_trade_by_commodity.py (which pulls ~97 chapters for a fixed
list of 9 partners). This one flips the axis: a curated set of chapters, but
all ~200 partners, so the website can compute each chapter's supplier mix,
top-1 supplier share, and HHI concentration (sketches 7, 8, 21).

One call = one chapter x one year (~200 partner rows, inside the preview
endpoint's 500-row cap). Results are cached per chapter in
output/commodity_partners/hs<NN>.csv, so the script can be stopped and
re-run; finished (chapter, year) pairs are skipped.

Output
------
output/commodity_partners/hs<NN>.csv     year, hs2, partner_code, partner_name, imports_usd
output/us_imports_by_chapter_partner.csv all chapters concatenated

Usage
-----
    python fetch_commodity_partners.py
    python fetch_commodity_partners.py --chapters 85 72 --years 2017 2025
Set COMTRADE_API_KEY to use the full (faster, higher-limit) endpoint.
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd

from us_trade_by_commodity import FULL, PREVIEW, USA_M49, get_json

# Chapters chosen to cover the storyboard: tech supply chain, steel, oil,
# consumer goods that left China, rare earths, and agriculture.
CHAPTERS = {
    "85": "Electrical equipment & electronics",
    "84": "Machinery & computers",
    "72": "Iron & steel",
    "73": "Articles of iron or steel",
    "27": "Mineral fuels & oil",
    "87": "Vehicles & parts",
    "30": "Pharmaceuticals",
    "90": "Optical & medical instruments",
    "94": "Furniture & lighting",
    "95": "Toys & sports equipment",
    "61": "Apparel (knit)",
    "62": "Apparel (not knit)",
    "39": "Plastics",
    "28": "Inorganic chemicals (incl. rare earths)",
    "10": "Cereals",
    "12": "Oil seeds",
}
YEARS = list(range(2006, 2026))


def fetch(year: int, hs2: str, api_key: str | None) -> pd.DataFrame:
    params = {
        "reporterCode": USA_M49,
        "period": year,
        "flowCode": "M",
        "cmdCode": hs2,
        "partner2Code": 0,
        "customsCode": "C00",
        "motCode": 0,
        "includeDesc": "true",
    }
    if api_key:
        url, headers = FULL, {"Ocp-Apim-Subscription-Key": api_key}
    else:
        url, headers = PREVIEW, None
    rows = (get_json(url, params, headers) or {}).get("data") or []
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["year", "hs2", "partner_code", "partner_name", "imports_usd"])
    df = df.rename(columns={"partnerCode": "partner_code", "partnerDesc": "partner_name",
                            "primaryValue": "imports_usd"})
    df = df.groupby(["partner_code", "partner_name"], as_index=False)["imports_usd"].sum()
    df.insert(0, "hs2", hs2)
    df.insert(0, "year", year)
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapters", nargs="+", default=list(CHAPTERS))
    ap.add_argument("--years", nargs="+", type=int, default=YEARS)
    ap.add_argument("--outdir", type=Path, default=Path(__file__).parent / "output")
    args = ap.parse_args()

    api_key = os.environ.get("COMTRADE_API_KEY")
    pause = 1.0 if api_key else 2.5
    cache = args.outdir / "commodity_partners"
    cache.mkdir(parents=True, exist_ok=True)

    for hs2 in args.chapters:
        path = cache / f"hs{hs2}.csv"
        have = pd.read_csv(path, dtype={"hs2": str}) if path.exists() else pd.DataFrame()
        done = set(have["year"]) if not have.empty else set()
        todo = [y for y in args.years if y not in done]
        print(f"HS{hs2} {CHAPTERS.get(hs2, '')}: {len(todo)} years to fetch")
        for year in todo:
            d = fetch(year, hs2, api_key)
            print(f"  {year}: {len(d)} partners", flush=True)
            if not d.empty:
                have = pd.concat([have, d], ignore_index=True)
                have.to_csv(path, index=False)      # checkpoint after every call
            time.sleep(pause)

    frames = [pd.read_csv(p, dtype={"hs2": str}) for p in sorted(cache.glob("hs*.csv"))]
    allp = pd.concat(frames, ignore_index=True)
    allp["chapter"] = allp["hs2"].map(CHAPTERS)
    out = args.outdir / "us_imports_by_chapter_partner.csv"
    allp.to_csv(out, index=False)
    print(f"wrote {out} ({len(allp):,} rows)")


if __name__ == "__main__":
    main()
