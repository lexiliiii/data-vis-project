"""
Build the compact JSON files the website loads (site/data/).

Inputs (from output/)
---------------------
us_trade_partners_long.csv          us_trading_partners.py
us_imports_by_chapter_partner.csv   fetch_commodity_partners.py  (optional - skipped if missing)

Outputs (to ../site/data/)
--------------------------
partners.json     per-partner exports / imports / total / balance / rank by year ($B)
commodities.json  per-chapter supplier series + concentration metrics by year
events.json       hand-curated policy & shock timeline (from EVENTS below)

Usage
-----
    python build_site_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "output"
SITE_DATA = HERE.parent / "site" / "data"

# Comtrade's names -> the names readers expect (same fixes as where_did_it_go.py)
NAMES = {
    "Other Asia, nes": "Taiwan",
    "Viet Nam": "Vietnam",
    "Rep. of Korea": "South Korea",
    "China, Hong Kong SAR": "Hong Kong",
    "Russian Federation": "Russia",
    "Türkiye": "Turkey",
    "Bolivarian Rep. of Venezuela": "Venezuela",
    "Venezuela (Bolivarian Rep. of)": "Venezuela",
    "Iran (Islamic Rep. of)": "Iran",
}

GROUPS = {
    "85": "Technology", "84": "Technology", "90": "Technology",
    "72": "Metals", "73": "Metals",
    "27": "Energy",
    "87": "Industrial", "39": "Industrial", "28": "Industrial", "30": "Industrial",
    "94": "Consumer", "95": "Consumer", "61": "Consumer", "62": "Consumer",
    "10": "Agriculture", "12": "Agriculture",
}

# scope: "all" | "china" | "steel" | "oil" | "tech" | "nafta"  (the site filters by it)
EVENTS = [
    {"date": "2008-09-15", "label": "Global financial crisis", "scope": "all"},
    {"date": "2018-03-23", "label": "Sec. 232 steel tariffs (25%)", "scope": "steel"},
    {"date": "2018-07-06", "label": "Sec. 301 tariffs on China begin", "scope": "china"},
    {"date": "2019-01-28", "label": "US sanctions on Venezuela's PDVSA", "scope": "oil"},
    {"date": "2020-01-15", "label": "US–China Phase One deal", "scope": "china"},
    {"date": "2020-03-11", "label": "COVID-19 pandemic", "scope": "all"},
    {"date": "2020-07-01", "label": "USMCA replaces NAFTA", "scope": "nafta"},
    {"date": "2022-03-08", "label": "US bans Russian oil imports", "scope": "oil"},
    {"date": "2022-08-09", "label": "CHIPS and Science Act", "scope": "tech"},
    {"date": "2025-04-02", "label": "2025 'reciprocal' tariffs", "scope": "all"},
    {"date": "2025-06-04", "label": "Steel tariffs raised to 50%", "scope": "steel"},
]

B = 1e9


def rnd(xs, nd=2):
    return [None if pd.isna(x) else round(float(x), nd) for x in xs]


def build_partners() -> dict:
    d = pd.read_csv(OUT / "us_trade_partners_long.csv")
    d["partner_name"] = d["partner_name"].replace(NAMES)
    years = sorted(d["year"].unique().tolist())

    # Keep every partner that was ever in the top 15 - enough for the bump chart,
    # indexed-growth lines and the share waffle's legend.
    keep = d.loc[d["rank_in_year"] <= 15, "partner_name"].unique()
    partners = []
    for name in keep:
        p = d[d["partner_name"] == name].set_index("year").reindex(years)
        partners.append({
            "name": name,
            "exports": rnd(p["exports_usd"] / B),
            "imports": rnd(p["imports_usd"] / B),
            "total": rnd(p["total_trade_usd"] / B),
            "balance": rnd(p["trade_balance_usd"] / B),
            "rank": [None if pd.isna(r) else int(r) for r in p["rank_in_year"]],
        })
    partners.sort(key=lambda p: p["rank"][-1] or 999)

    tot = d.groupby("year")[["exports_usd", "imports_usd", "total_trade_usd", "trade_balance_usd"]].sum()
    return {
        "years": years,
        "unit": "USD billions (current)",
        "us": {
            "exports": rnd(tot["exports_usd"] / B),
            "imports": rnd(tot["imports_usd"] / B),
            "total": rnd(tot["total_trade_usd"] / B),
            "balance": rnd(tot["trade_balance_usd"] / B),
        },
        "partners": partners,
    }


def build_commodities() -> dict | None:
    path = OUT / "us_imports_by_chapter_partner.csv"
    if not path.exists():
        print(f"  (skipping commodities: {path.name} not found - run fetch_commodity_partners.py)")
        return None
    d = pd.read_csv(path, dtype={"hs2": str})
    d["partner_name"] = d["partner_name"].replace(NAMES)
    d = d[d["partner_code"] != 0]                       # drop the "World" row; we sum partners
    years = sorted(d["year"].unique().tolist())

    chapters = []
    for hs2, g in d.groupby("hs2"):
        wide = g.pivot_table(index="year", columns="partner_name", values="imports_usd",
                             aggfunc="sum").reindex(years).fillna(0)
        total = wide.sum(axis=1)
        share = wide.div(total.where(total > 0), axis=0).astype(float)   # NaN for years with no data

        # Named suppliers: anyone in the top 6 in any year, always including China.
        top = set()
        for y in years:
            top |= set(wide.loc[y].nlargest(6).index)
        if "China" in wide.columns:
            top.add("China")
        top =sorted(top, key=lambda n: -wide[n].iloc[-1])
        other = wide.drop(columns=top).sum(axis=1)

        has = total > 0
        top1 = wide.idxmax(axis=1).where(has)
        top1_share = share.max(axis=1)
        hhi = ((share ** 2).sum(axis=1) * 10000).where(has)    # 0-10000 scale

        chapters.append({
            "hs2": hs2,
            "name": g["chapter"].iloc[0],
            "group": GROUPS.get(hs2, "Other"),
            "total": rnd(total / B),
            "suppliers": [{"name": n, "imports": rnd(wide[n] / B, 3)} for n in top]
                         + [{"name": "Rest of world", "imports": rnd(other / B, 3)}],
            "top1": [n if isinstance(n, str) else None for n in top1],
            "top1Share": rnd(top1_share, 4),
            "chinaShare": rnd(share["China"], 4) if "China" in share.columns else [0] * len(years),
            "hhi": rnd(hhi, 0),
        })
    chapters.sort(key=lambda c: -c["total"][-1])
    return {"years": years, "unit": "USD billions (current)", "chapters": chapters}


def main() -> None:
    SITE_DATA.mkdir(parents=True, exist_ok=True)

    def dump(name, obj):
        p = SITE_DATA / name
        p.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        print(f"  wrote {p} ({p.stat().st_size / 1024:.0f} KB)")

    dump("partners.json", build_partners())
    dump("events.json", EVENTS)
    c = build_commodities()
    if c:
        dump("commodities.json", c)


if __name__ == "__main__":
    main()
