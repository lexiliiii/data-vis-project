"""
Line charts of US trade with its top 10 partners, 2006-2025.

Reads the CSVs already written by us_trading_partners.py:
    output/us_trade_partners_long.csv      year, partner, exports/imports/total/balance
    output/us_top_partners_summary.csv     partners ranked by cumulative total trade

...and renders two line charts, one line per partner, x = year:

    output/us_top10_total_trade_line.png    total trade value (exports + imports)
    output/us_top10_trade_balance_line.png  trade balance (exports - imports), with a
                                             zero baseline separating US surplus from deficit

Usage
-----
    python plot_top10_line_charts.py                  # writes both PNGs to output/
    python plot_top10_line_charts.py --show            # also opens interactive windows
    python plot_top10_line_charts.py --indir X --outdir Y
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

# --------------------------------------------------------------------------- #
# Palette - the same validated categorical order used for the heatmap artifact
# (blue, orange, aqua, yellow, magenta, green, violet, red). Ranks 9-10 reuse
# the first two hues with a dashed line instead of inventing new colors, so
# identity still reads correctly through the (always-present) legend.
# --------------------------------------------------------------------------- #
HUES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
        "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
DIV_NEG = "#e34948"
DIV_POS = "#2a78d6"

# Comtrade reports Taiwan under this aggregate code for most reporters.
DISPLAY_NAME = {"Other Asia, nes": "Taiwan"}


def style_of(rank: int) -> tuple[str, str]:
    """(color, linestyle) for a partner's rank (0 = biggest)."""
    if rank < len(HUES):
        return HUES[rank], "-"
    return HUES[rank - len(HUES)], (0, (5, 2))  # dashed, reusing hue 1/2


def load_top10(indir: Path) -> tuple[pd.DataFrame, list[str]]:
    long_df = pd.read_csv(indir / "us_trade_partners_long.csv")
    summary = pd.read_csv(indir / "us_top_partners_summary.csv")
    top10 = summary.head(10)["partner_name"].tolist()
    df = long_df[long_df["partner_name"].isin(top10)].copy()
    df["display_name"] = df["partner_name"].map(lambda n: DISPLAY_NAME.get(n, n))
    order = [DISPLAY_NAME.get(n, n) for n in top10]
    return df, order


def base_axes(title: str, subtitle: str):
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.spines["bottom"].set_linewidth(1)

    ax.grid(axis="y", color=GRIDLINE, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0, labelsize=9, colors=TEXT_MUTED)

    fig.suptitle(title, x=0.06, y=0.975, ha="left", fontsize=16,
                 fontweight="bold", color=TEXT_PRIMARY)
    ax.set_title(subtitle, loc="left", fontsize=10.5, color=TEXT_SECONDARY, pad=14)
    return fig, ax


def draw_series(ax, years, df, value_col, order):
    for rank, name in enumerate(order):
        sub = df[df["display_name"] == name].sort_values("year")
        color, style = style_of(rank)
        ax.plot(sub["year"], sub[value_col], color=color, linestyle=style,
                 linewidth=2, solid_capstyle="round", zorder=3, label=name)
        ax.plot(sub["year"].iloc[-1], sub[value_col].iloc[-1],
                 marker="o", markersize=8, markerfacecolor=color,
                 markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)

    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=8.5)
    ax.set_xlim(years[0] - 0.4, years[-1] + 1.9)  # headroom for end markers/legend


def dollars_billions(ax):
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"${v / 1e9:,.0f}B"))


def add_legend(ax):
    leg = ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5),
                     frameon=False, fontsize=9.5, labelcolor=TEXT_PRIMARY,
                     handlelength=1.6, borderaxespad=0)
    for line in leg.get_lines():
        line.set_linewidth(2.5)


def annotate_extreme(ax, years, df, value_col, order, rank, note):
    """Label the one line the chart's story is about, at its endpoint."""
    name = order[rank]
    sub = df[df["display_name"] == name].sort_values("year")
    x, y = sub["year"].iloc[-1], sub[value_col].iloc[-1]
    color, _ = style_of(rank)
    ax.annotate(note, xy=(x, y), xytext=(8, 0), textcoords="offset points",
                fontsize=9, fontweight="bold", color=color, va="center")


def plot_total_trade(df, years, order, outdir: Path, show: bool):
    fig, ax = base_axes(
        "Total trade value, US top 10 partners",
        "Exports + imports by year, current USD  ·  UN Comtrade, reporter 842",
    )
    draw_series(ax, years, df, "total_trade_usd", order)
    dollars_billions(ax)
    add_legend(ax)
    annotate_extreme(ax, years, df, "total_trade_usd", order, 1, "  Mexico")
    fig.tight_layout(rect=(0, 0, 0.86, 0.94))
    out = outdir / "us_top10_total_trade_line.png"
    fig.savefig(out, facecolor=fig.get_facecolor())
    print(f"Wrote {out}")
    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_trade_balance(df, years, order, outdir: Path, show: bool):
    fig, ax = base_axes(
        "Trade balance, US top 10 partners",
        "Exports − imports by year  ·  above the line = US surplus, below = US deficit",
    )
    ymin = df["trade_balance_usd"].min() * 1.08
    ymax = max(df["trade_balance_usd"].max() * 1.4, 1e10)
    ax.axhspan(0, ymax, color=DIV_POS, alpha=0.05, zorder=0)
    ax.axhspan(ymin, 0, color=DIV_NEG, alpha=0.05, zorder=0)
    ax.axhline(0, color=BASELINE, linewidth=1.5, zorder=2)
    ax.set_ylim(ymin, ymax)
    ax.text(years[0] - 0.2, ymax * 0.94, "US surplus", fontsize=9,
             color=TEXT_MUTED, va="top")
    ax.text(years[0] - 0.2, ymin * 0.97, "US deficit", fontsize=9,
             color=TEXT_MUTED, va="bottom")

    draw_series(ax, years, df, "trade_balance_usd", order)
    dollars_billions(ax)
    add_legend(ax)
    annotate_extreme(ax, years, df, "trade_balance_usd", order, 2, "  China")
    fig.tight_layout(rect=(0, 0, 0.86, 0.94))
    out = outdir / "us_top10_trade_balance_line.png"
    fig.savefig(out, facecolor=fig.get_facecolor())
    print(f"Wrote {out}")
    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--indir", type=Path, default=Path(__file__).parent / "output")
    p.add_argument("--outdir", type=Path, default=Path(__file__).parent / "output")
    p.add_argument("--show", action="store_true", help="also open interactive windows")
    args = p.parse_args()

    df, order = load_top10(args.indir)
    years = sorted(df["year"].unique())
    args.outdir.mkdir(parents=True, exist_ok=True)

    plot_total_trade(df, years, order, args.outdir, args.show)
    plot_trade_balance(df, years, order, args.outdir, args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
