"""
US trade by commodity chapter (HS2) and partner - who supplies what, and how it
shifted away from China.

Companion to us_trading_partners.py (which pulls country totals only). This one
breaks each partner's trade into the ~97 HS2 chapters so you can see WHICH goods
left China and WHERE they went.

Outputs (in --outdir, default ./output)
--------------------------------------
us_trade_by_commodity_long.csv   year, partner, hs2, chapter, flow, value_usd
china_shift_by_chapter.csv       per chapter: US imports from China in the base
                                 year vs the latest year, the change, and the
                                 matching change for Vietnam / Mexico / Taiwan /
                                 India / Thailand ("where it went")
china_import_share_by_chapter.csv  China's % share of US imports, per chapter per year
commodity_shift.png              chart of the chapters that moved most

Usage
-----
    pip install requests pandas matplotlib
    python us_trade_by_commodity.py                       # 2017 vs 2024 vs 2025
    python us_trade_by_commodity.py --years 2017 2019 2025
    python us_trade_by_commodity.py --no-plot

Set COMTRADE_API_KEY (free at comtradedeveloper.un.org) to use the full API
instead of the rate-limited public preview endpoint.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

USA_M49 = 842
PREVIEW = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
FULL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"

# Partner M49 codes. "Taiwan" is reported by Comtrade as "Other Asia, nes" (490).
PARTNERS = {
    156: "China",
    704: "Vietnam",
    484: "Mexico",
    490: "Taiwan",
    699: "India",
    764: "Thailand",
    410: "Korea, Rep.",
    458: "Malaysia",
    0:   "World",
}
# Alternatives whose gains we compare against China's losses
ALTERNATIVES = ["Vietnam", "Mexico", "Taiwan", "India", "Thailand", "Malaysia"]


def get_json(url, params, headers=None, retries=5, backoff=4.0):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=90)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == retries:
                raise
            wait = backoff * attempt
            print(f"      retry {attempt}/{retries}: {e} (sleep {wait:.0f}s)")
            time.sleep(wait)


def fetch(year: int, partner: int, flow: str, api_key: str | None) -> pd.DataFrame:
    """All HS2 chapters for one partner / year / flow. ~97 rows, inside the
    preview endpoint's 500-row cap."""
    params = {
        "reporterCode": USA_M49,
        "period": year,
        "partnerCode": partner,
        "flowCode": flow,              # M = US imports, X = US exports
        "cmdCode": "AG2",              # every 2-digit HS chapter
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
    if not rows:
        return pd.DataFrame(columns=["hs2", "chapter", "value_usd"])
    df = pd.DataFrame(rows)
    df = df.rename(columns={"cmdCode": "hs2", "cmdDesc": "chapter",
                            "primaryValue": "value_usd"})
    df["hs2"] = df["hs2"].astype(str).str.zfill(2)
    df = df[df["hs2"].str.fullmatch(r"\d{2}")]          # drop TOTAL / aggregates
    return df.groupby(["hs2", "chapter"], as_index=False)["value_usd"].sum()


def extract(years, api_key) -> pd.DataFrame:
    pause = 1.0 if api_key else 2.5
    frames = []
    for year in years:
        for code, name in PARTNERS.items():
            for flow, label in (("M", "us_imports"), ("X", "us_exports")):
                print(f"  {year} {name:<12} {label} ...", end=" ", flush=True)
                d = fetch(year, code, flow, api_key)
                print(f"{len(d)} chapters")
                d["year"], d["partner"], d["flow"] = year, name, label
                frames.append(d)
                time.sleep(pause)
    return pd.concat(frames, ignore_index=True)


def analyse(df: pd.DataFrame, outdir: Path, plot: bool) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df.to_csv(outdir / "us_trade_by_commodity_long.csv", index=False)

    imp = df[df.flow == "us_imports"]
    base, last = int(imp.year.min()), int(imp.year.max())

    # Chapter labels: Comtrade's description, shortened for charts
    names = (imp.sort_values("year").groupby("hs2")["chapter"].last()
                .str.slice(0, 48))

    piv = imp.pivot_table(index="hs2", columns=["partner", "year"],
                          values="value_usd", aggfunc="sum").fillna(0)

    def col(partner, year):
        return piv[(partner, year)] if (partner, year) in piv.columns else 0

    out = pd.DataFrame({"chapter": names})
    out[f"china_{base}"] = col("China", base)
    out[f"china_{last}"] = col("China", last)
    out["china_change"] = out[f"china_{last}"] - out[f"china_{base}"]
    out["china_pct_change"] = (out["china_change"] /
                               out[f"china_{base}"].replace(0, pd.NA) * 100)
    alt_change = sum(col(a, last) - col(a, base) for a in ALTERNATIVES)
    out["alternatives_change"] = alt_change
    out["world_change"] = col("World", last) - col("World", base)
    for a in ALTERNATIVES:
        out[f"{a.lower().replace(', ', '_')}_change"] = col(a, last) - col(a, base)
    # How much of China's lost volume the alternatives picked up
    out["replacement_ratio"] = (out["alternatives_change"] /
                                (-out["china_change"]).replace(0, pd.NA))
    out = out.sort_values(f"china_{base}", ascending=False)
    out.to_csv(outdir / "china_shift_by_chapter.csv")

    # China's share of US imports, per chapter per year
    share = (imp[imp.partner == "China"].pivot_table(index="hs2", columns="year",
                                                     values="value_usd", aggfunc="sum")
             / imp[imp.partner == "World"].pivot_table(index="hs2", columns="year",
                                                       values="value_usd", aggfunc="sum")
             * 100)
    share.insert(0, "chapter", names)
    share.round(1).to_csv(outdir / "china_import_share_by_chapter.csv")

    top = out.head(15)
    print(f"\nUS imports from China by HS chapter, {base} vs {last} (USD bn):")
    show = top[["chapter", f"china_{base}", f"china_{last}", "china_pct_change",
                "alternatives_change"]].copy()
    for c in (f"china_{base}", f"china_{last}", "alternatives_change"):
        show[c] = (show[c] / 1e9).round(1)
    show["china_pct_change"] = show["china_pct_change"].round(0)
    print(show.to_string())

    if plot:
        make_chart(out, base, last, outdir)


def make_chart(out: pd.DataFrame, base: int, last: int, outdir: Path) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mt
    import numpy as np

    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "text.parse_math": False})
    top = out.head(12).iloc[::-1]
    pos = np.arange(len(top))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7.5), facecolor="#fcfcfb",
                                   gridspec_kw={"width_ratios": [1.25, 1]})

    ax1.barh(pos + 0.2, top[f"china_{base}"] / 1e9, 0.38, color="#c9d9ef", label=str(base))
    ax1.barh(pos - 0.2, top[f"china_{last}"] / 1e9, 0.38, color="#2a78d6", label=str(last))
    ax1.set_yticks(pos, top["chapter"], fontsize=9)
    ax1.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:,.0f}B"))
    ax1.set_title(f"US imports from China by HS chapter, {base} vs {last}",
                  loc="left", fontsize=11)
    ax1.legend(frameon=False)

    ax2.barh(pos, top["china_change"] / 1e9, 0.38, color="#e34948", label="China")
    ax2.barh(pos, top["alternatives_change"] / 1e9, 0.38, color="#1baf7a",
             left=0, alpha=0.75, height=0.2, label="Vietnam/Mexico/Taiwan/India/Thailand/Malaysia")
    ax2.axvline(0, color="#8a8a8a", lw=1)
    ax2.set_yticks(pos, [""] * len(top))
    ax2.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:,.0f}B"))
    ax2.set_title(f"Change in US imports, {base} → {last}", loc="left", fontsize=11)
    ax2.legend(frameon=False, fontsize=8.5, loc="lower right")

    fig.suptitle("Which goods left China, and whether anyone else picked them up",
                 fontsize=14, weight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.01, "Source: UN Comtrade, US-reported goods imports, current USD. "
                         "Taiwan = “Other Asia, nes”.", fontsize=8.5, color="#5c5c5c")
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    path = outdir / "commodity_shift.png"
    fig.savefig(path, dpi=150, facecolor="#fcfcfb")
    print(f"\nChart: {path}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--years", type=int, nargs="+", default=[2017, 2024, 2025],
                   help="years to pull; first = base, last = comparison year")
    p.add_argument("--outdir", type=Path, default=Path(__file__).parent / "output")
    p.add_argument("--no-plot", dest="plot", action="store_false")
    args = p.parse_args()

    years = sorted(args.years)
    key = os.getenv("COMTRADE_API_KEY")
    print(f"US trade by HS2 chapter, years {years}, "
          f"{len(PARTNERS)} partners ({'full API' if key else 'public preview'})")
    df = extract(years, key)
    if df.empty:
        print("No data returned.", file=sys.stderr)
        return 1
    analyse(df, args.outdir, args.plot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
