"""
Data storyboard (hook -> rising insights -> main message -> solution) for the
US trade-partner story, built from output/us_trade_partners_long.csv.
Writes output/data_storyboard.png - a reference for the team's paper/Miro sketch.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

HERE = Path(__file__).parent
d = pd.read_csv(HERE / "output" / "us_trade_partners_long.csv")
d["partner_name"] = d["partner_name"].replace({"Other Asia, nes": "Taiwan", "Viet Nam": "Vietnam"})
tot = d.pivot_table(index="year", columns="partner_name", values="total_trade_usd") / 1e9
bal = d.pivot_table(index="year", columns="partner_name", values="trade_balance_usd") / 1e9
share = tot.div(tot.sum(1), axis=0) * 100
us_deficit = -bal.sum(1)

BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#8a8a8a"
INK, MUTED, SURF = "#0b0b0b", "#5c5c5c", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#bdbdbd",
                     "axes.spines.top": False, "axes.spines.right": False,
                     "xtick.color": MUTED, "ytick.color": MUTED, "text.parse_math": False})

fig = plt.figure(figsize=(22, 10), facecolor=SURF)

fig.text(0.5, 0.965, "Data storyboard: “The US didn’t shrink its China problem, it moved it”",
         ha="center", fontsize=19, weight="bold", color=INK)

# Story arc: rises through the insights, peaks at the main message, resolves at the solution
arc = fig.add_axes([0.03, 0.80, 0.94, 0.12]); arc.axis("off"); arc.set_xlim(0, 5); arc.set_ylim(0, 1)
xs = [0.5, 1.5, 2.5, 3.5, 4.5]; ys = [0.15, 0.40, 0.62, 0.92, 0.35]
arc.plot(xs, ys, color=GRAY, lw=2.5, ls="--", zorder=1)
labels = ["1  HOOK", "2  RISING INSIGHT", "3  RISING INSIGHT", "4  MAIN MESSAGE", "5  SOLUTION"]
for x, y, l, c in zip(xs, ys, labels, [BLUE, BLUE, BLUE, ORANGE, AQUA]):
    arc.scatter(x, y, s=180, color=c, zorder=2)
    arc.text(x, y + 0.14, l, ha="center", fontsize=11, weight="bold", color=c)

W, H, Y, GAP, X0 = 0.172, 0.40, 0.33, 0.02, 0.03
def frame(i, color):
    x = X0 + i * (W + GAP)
    fig.add_artist(FancyBboxPatch((x - 0.006, 0.06), W + 0.012, 0.72, boxstyle="round,pad=0.004",
                                  transform=fig.transFigure, fc="white", ec=color, lw=2, zorder=-10))
    return x
def caption(x, head, body):
    fig.text(x, 0.30, head, fontsize=11.5, weight="bold", color=INK, va="top", wrap=True)
    fig.text(x, 0.225, body, fontsize=9.6, color=MUTED, va="top", linespacing=1.45)
def bn(ax): ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:,.0f}B"))

# 1 HOOK
x = frame(0, BLUE); ax = fig.add_axes([x + 0.02, Y + 0.03, W - 0.03, H - 0.04])
ax.plot(share.index, share["China"], color=BLUE, lw=2.5)
ax.axvline(2018, color=GRAY, ls=":", lw=1); ax.text(2018.3, 6.5, "2018\ntariffs", fontsize=8.5, color=MUTED)
for yr in (2017, 2025):
    ax.scatter(yr, share.loc[yr, "China"], color=BLUE, zorder=3)
    ax.annotate(f"{share.loc[yr,'China']:.1f}%", (yr, share.loc[yr, "China"]), xytext=(-18, 8),
                textcoords="offset points", fontsize=10, weight="bold", color=BLUE)
ax.set_ylim(5, 19); ax.yaxis.set_major_formatter(mt.PercentFormatter(decimals=0))
ax.set_title("China's share of US goods trade", fontsize=10, color=INK, loc="left")
caption(x, "China’s share of US trade\nhas halved since 2017.",
        "Hook: “Did decoupling work?”\nThe headline most people\nexpect to see confirmed.")

# 2 RISING: Mexico overtakes
x = frame(1, BLUE); ax = fig.add_axes([x + 0.03, Y + 0.03, W - 0.04, H - 0.04])
for c, col in (("Mexico", ORANGE), ("Canada", GRAY), ("China", BLUE)):
    ax.plot(tot.index, tot[c], color=col, lw=2.5 if c != "Canada" else 1.5)
    ax.text(2025.3, tot.loc[2025, c], c, color=col, fontsize=9, va="center", weight="bold")
ax.set_xlim(2006, 2028.5); bn(ax)
ax.set_title("Total trade (exports + imports)", fontsize=10, color=INK, loc="left")
caption(x, "Mexico is now the #1 US\ntrading partner (since 2023).",
        f"Mexico: ${tot.loc[2017,'Mexico']:.0f}B (2017) → ${tot.loc[2025,'Mexico']:.0f}B (2025)\n"
        f"China:  ${tot.loc[2017,'China']:.0f}B → ${tot.loc[2025,'China']:.0f}B\nNearshoring picks up the slack.")

# 3 RISING: Asia substitutes
x = frame(2, BLUE); ax = fig.add_axes([x + 0.03, Y + 0.03, W - 0.04, H - 0.04])
cs = ["Taiwan", "Vietnam", "India", "Thailand"]
import numpy as np
pos = np.arange(len(cs))
ax.barh(pos + 0.2, [tot.loc[2017, c] for c in cs], 0.38, color="#c9d9ef", label="2017")
ax.barh(pos - 0.2, [tot.loc[2025, c] for c in cs], 0.38, color=BLUE, label="2025")
for p, c in zip(pos, cs):
    ax.text(tot.loc[2025, c] + 4, p - 0.2, f"{tot.loc[2025,c]/tot.loc[2017,c]:.1f}×", va="center", fontsize=9, weight="bold", color=BLUE)
ax.set_yticks(pos, cs); ax.invert_yaxis(); ax.set_xlim(0, 310)
ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:,.0f}B"))
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
ax.set_title("Total trade, 2017 vs 2025", fontsize=10, color=INK, loc="left")
caption(x, "Vietnam and Taiwan tripled\nor more.",
        "Vietnam: #16 → #7 partner\nTaiwan: #11 → #4 partner\nSame goods, new routes? (check\ncommodity data: electronics, chips)")

# 4 MAIN MESSAGE
x = frame(3, ORANGE); ax = fig.add_axes([x + 0.035, Y + 0.03, W - 0.045, H - 0.04])
trio = -(bal["Mexico"] + bal["Vietnam"] + bal["Taiwan"])
ax.plot(us_deficit.index, us_deficit, color=INK, lw=2.5)
ax.plot(bal.index, -bal["China"], color=BLUE, lw=2)
ax.plot(trio.index, trio, color=ORANGE, lw=2.5)
ax.text(2025.4, us_deficit.loc[2025], "Total", fontsize=8.5, color=INK, weight="bold", va="center")
ax.text(2025.4, -bal.loc[2025, "China"] - 30, "China", fontsize=8.5, color=BLUE, weight="bold", va="center")
ax.text(2025.4, trio.loc[2025] + 30, "MX+VN+TW", fontsize=8.5, color=ORANGE, weight="bold", va="center")
ax.set_xlim(2006, 2030)
ax.axvline(2018, color=GRAY, ls=":", lw=1); bn(ax); ax.set_ylim(0, 1450)
ax.set_title("US goods trade deficit", fontsize=10, color=INK, loc="left")
caption(x, "Decoupling moved the deficit,\nit didn’t shrink it.",
        f"2017→2025: deficit with China −${-bal.loc[2017,'China']+bal.loc[2025,'China']:.0f}B,\n"
        f"with Mexico+Vietnam+Taiwan +${trio.loc[2025]-trio.loc[2017]:.0f}B.\n"
        f"Total deficit: ${us_deficit.loc[2017]:.0f}B → ${us_deficit.loc[2025]:,.0f}B (+{us_deficit.loc[2025]/us_deficit.loc[2017]*100-100:.0f}%).")

# 5 SOLUTION
x = frame(4, AQUA); ax = fig.add_axes([x, Y, W, H]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
recs = ["Judge trade policy by where\nsupply chains end up, not by\none bilateral deficit.",
        "Track rerouting: rules of origin\n& transshipment via Vietnam/Mexico.",
        "Use our dashboard to follow\nthe same goods across partners\n(steel, chips, electronics)."]
for k, r in enumerate(recs):
    yy = 0.88 - k * 0.33
    ax.scatter(0.06, yy - 0.02, s=260, color=AQUA); ax.text(0.06, yy - 0.02, str(k + 1), ha="center", va="center", color="white", weight="bold")
    ax.text(0.15, yy, r, va="top", fontsize=10, color=INK, linespacing=1.4)
caption(x, "Follow the goods,\nnot the flag.", "Call to action for policymakers,\nanalysts and students reading\nthe headlines.")

fig.text(0.03, 0.02, "Source: UN Comtrade, US-reported goods trade, current USD, 2006–2025. Taiwan = “Other Asia, nes”.",
         fontsize=8.5, color=MUTED)
out = HERE / "output" / "data_storyboard.png"
fig.savefig(out, dpi=150, facecolor=SURF); print(out)
