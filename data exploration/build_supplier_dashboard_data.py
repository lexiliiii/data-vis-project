"""Build the compact browser payload for the supplier-risk dashboard."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


LABELS = {
    "Other Asia, nes": "Taiwan",
    "Viet Nam": "Vietnam",
    "Rep. of Korea": "South Korea",
    "Russian Federation": "Russia",
}


def build(source: Path) -> dict:
    world: dict[tuple[str, int], float] = {}
    imports: dict[tuple[str, int, str], float] = defaultdict(float)
    chapters: dict[str, str] = {}
    years: set[int] = set()

    with source.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            hs = str(row["hs2"]).zfill(2)
            year = int(row["year"])
            value = float(row["imports_usd"])
            chapters[hs] = row["chapter"]
            years.add(year)
            if int(row["partner_code"]) == 0:
                world[(hs, year)] = value
            else:
                partner = LABELS.get(row["partner_name"], row["partner_name"])
                imports[(hs, year, partner)] += value

    ordered_years = sorted(years)
    categories = []
    for hs in sorted(chapters, key=int):
        names = sorted({partner for h, _, partner in imports if h == hs})
        all_shares: dict[str, list[float]] = {}
        for partner in names:
            values = []
            for year in ordered_years:
                denominator = world[(hs, year)]
                values.append(100 * imports[(hs, year, partner)] / denominator if denominator else 0)
            all_shares[partner] = values

        # Keep established suppliers in the browser payload. Smaller suppliers
        # remain represented in Other, while HHI and yearly leaders use all rows.
        selected = [name for name in names if max(all_shares[name]) >= 1.0]
        selected.sort(key=lambda name: max(all_shares[name]), reverse=True)

        leaders = []
        hhi = []
        for index, year in enumerate(ordered_years):
            ranked = sorted(((all_shares[name][index], name) for name in names), reverse=True)
            share, name = ranked[0]
            leaders.append({"name": name, "share": round(share, 4)})
            hhi.append(round(sum(value * value for value, _ in ranked), 2))

        categories.append({
            "hs": hs,
            "name": chapters[hs],
            "suppliers": selected,
            "shares": {name: [round(value, 4) for value in all_shares[name]] for name in selected},
            "leaders": leaders,
            "hhi": hhi,
        })

    return {
        "years": ordered_years,
        "categories": categories,
        "supplier_cutoff": "Included individually if share reaches 1% in any year; all smaller suppliers remain in Other.",
        "source": "UN Comtrade existing project extract; US-reported annual imports by HS2 and partner.",
    }


def main() -> None:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", type=Path, default=base / "output" / "us_imports_by_chapter_partner.csv")
    parser.add_argument("output", nargs="?", type=Path, default=base.parent / "supplier-dashboard-data.js")
    args = parser.parse_args()
    payload = json.dumps(build(args.source), ensure_ascii=False, separators=(",", ":"))
    args.output.write_text("window.SUPPLIER_DASHBOARD_DATA=" + payload + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()
