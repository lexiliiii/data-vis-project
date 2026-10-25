"""Where did the China share go? US goods imports by partner, 2017 vs 2025.
Reads output/us_trade_partners_long.csv; writes output/where_did_it_go.png"""
from pathlib import Path
import matplotlib.pyplot as plt, matplotlib.ticker as mt, numpy as np, pandas as pd

H = Path(__file__).parent
d = pd.read_csv(H / "output" / "us_trade_partners_long.csv")
d["partner_name"] = d.partner_name.replace({"Other Asia, nes": "Taiwan", "Viet Nam": "Vietnam",
                                            "Rep. of Korea": "South Korea"})
imp = d.pivot_table(index="year", columns="partner_name", values="imports_usd") / 1e9
sh = imp.div(imp.sum(1), axis=0) * 100
chg = (sh.loc[2025] - sh.loc[2017]).dropna().sort_values()
pick = pd.concat([chg.head(4), chg.tail(9)]).sort_values()

BLUE, RED, GRAY, INK, MUTED, SURF = "#2a78d6", "#e34948", "#8a8a8a", "#0b0b0b", "#5c5c5c", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "text.parse_math": False,
                     "xtick.color": MUTED, "ytick.color": MUTED})
fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 7.5), facecolor=SURF,
                             gridspec_kw={"width_ratios": [1, 1.1]})

pos = np.arange(len(pick))
a1.barh(pos, pick.values, color=[RED if v < 0 else BLUE for v in pick.values], height=0.62)
for p, (n, v) in zip(pos, pick.items()):
    a1.text(v + (0.12 if v > 0 else -0.12), p, f"{v:+.1f}", va="center",
            ha="left" if v > 0 else "right", fontsize=9, weight="bold",
            color=BLUE if v > 0 else RED)
a1.set_yticks(pos, pick.index, fontsize=10)
a1.axvline(0, color=GRAY, lw=1); a1.set_xlim(-14.5, 6.5)
a1.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:+.0f} pts"))
a1.set_title("Change in share of US goods imports, 2017 → 2025", loc="left", fontsize=11, color=INK)

for c, col, lw in (("China", RED, 2.6), ("Mexico", "#eb6834", 2.2), ("Taiwan", BLUE, 2.2),
                   ("Vietnam", "#1baf7a", 2.2), ("Ireland", "#4a3aa7", 1.6),
                   ("Switzerland", "#eda100", 1.6)):
    a2.plot(sh.index, sh[c], color=col, lw=lw)
    off = {"Taiwan": 0.45, "Vietnam": -0.45}.get(c, 0)
    a2.text(2025.3, sh.loc[2025, c] + off, f" {c}", color=col, fontsize=9.5, weight="bold", va="center")
a2.set_xlim(2006, 2030); a2.yaxis.set_major_formatter(mt.PercentFormatter(decimals=0))
a2.axvline(2018, color=GRAY, ls=":", lw=1); a2.axvline(2025, color=GRAY, ls=":", lw=1)
a2.text(2018.2, 21, "2018 tariffs", fontsize=8.5, color=MUTED)
a2.set_title("Share of US goods imports, by partner", loc="left", fontsize=11, color=INK)

fig.suptitle("If not China, then where? China lost 12.5 points of US import share; "
             "Taiwan, Vietnam and Mexico took 10 of them",
             fontsize=14, weight="bold", x=0.015, ha="left")
fig.text(0.015, 0.012, "Source: UN Comtrade, US-reported goods imports, current USD. "
         "Taiwan = “Other Asia, nes”. Ireland = pharmaceuticals; Switzerland 2025 is "
         "inflated by gold bullion flows.", fontsize=8.5, color=MUTED)
fig.tight_layout(rect=[0, 0.035, 1, 0.945])
out = H / "output" / "where_did_it_go.png"
fig.savefig(out, dpi=150, facecolor=SURF); print(out)
