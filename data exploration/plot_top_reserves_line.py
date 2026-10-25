"""
Line chart of the top 10 countries by foreign exchange reserves, 2006-2025.

Reads the CSVs written by forex_reserves.py:
    output/reserves_by_country_long.csv       year, country, total/gold/non-gold reserves
    output/reserves_top_holders_summary.csv   countries ranked by latest-year total reserves

...and renders one line per country, x = year, y = total reserves (includes gold),
styled to match plot_top10_line_charts.py (same palette, marks, and legend). Unlike
the trade-balance chart it's based on, reserves never go negative, so there's no
zero baseline to shade - the composition (gold vs. non-gold) lives in the CSV and
in reserves_top_holders_summary.csv, not on this line.

Output: output/top10_forex_reserves_line.png

Usage
-----
    python plot_top_reserves_line.py
    python plot_top_reserves_line.py --show
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from plot_top10_line_charts import (
    add_legend,
    annotate_extreme,
    base_axes,
    dollars_billions,
    draw_series,
)

DISPLAY_NAME = {"Korea, Rep.": "South Korea"}


def load_top10(indir: Path) -> tuple[pd.DataFrame, list[str]]:
    long_df = pd.read_csv(indir / "reserves_by_country_long.csv")
    summary = pd.read_csv(indir / "reserves_top_holders_summary.csv")
    top10 = summary.head(10)["country_name"].tolist()
    df = long_df[long_df["country_name"].isin(top10)].copy()
    df["display_name"] = df["country_name"].map(lambda n: DISPLAY_NAME.get(n, n))
    order = [DISPLAY_NAME.get(n, n) for n in top10]
    return df, order


def plot_reserves(df, years, order, outdir: Path, show: bool):
    fig, ax = base_axes(
        "Foreign exchange reserves, top 10 holders",
        "Total reserves (includes gold), current USD  ·  World Bank WDI",
    )
    draw_series(ax, years, df, "total_reserves_usd", order)
    dollars_billions(ax)
    add_legend(ax)
    annotate_extreme(ax, years, df, "total_reserves_usd", order, 0, "  China")
    fig.tight_layout(rect=(0, 0, 0.86, 0.94))
    out = outdir / "top10_forex_reserves_line.png"
    fig.savefig(out, facecolor=fig.get_facecolor())
    print(f"Wrote {out}")
    if show:
        import matplotlib.pyplot as plt
        plt.show()
    else:
        import matplotlib.pyplot as plt
        plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--indir", type=Path, default=Path(__file__).parent / "output")
    p.add_argument("--outdir", type=Path, default=Path(__file__).parent / "output")
    p.add_argument("--show", action="store_true", help="also open an interactive window")
    args = p.parse_args()

    df, order = load_top10(args.indir)
    years = sorted(df["year"].unique())
    args.outdir.mkdir(parents=True, exist_ok=True)

    plot_reserves(df, years, order, args.outdir, args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
