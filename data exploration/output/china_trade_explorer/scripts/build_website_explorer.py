"""Refresh only the new explorer's embedded data in draft.html; no network needed."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parents[2] / 'draft.html'
CATEGORIES = [('85', 'Electronics'), ('84', 'Machinery'), ('87', 'Vehicles & parts'),
              ('94', 'Furniture & lighting'), ('95', 'Toys & sports'),
              ('61', 'Apparel · knit'), ('72', 'Iron & steel'), ('30', 'Pharmaceuticals')]

def payload(root=ROOT):
    with (root / 'processed/annual_category_summary.csv').open() as stream:
        rows = {(r['hs2'], int(r['year'])): r for r in csv.DictReader(stream)}
    with (root / 'processed/annual_trade_by_supplier.csv').open() as stream:
        suppliers = {(r['hs2'], int(r['year']), r['partner_code']): float(r['imports_usd_nominal'])
                     for r in csv.DictReader(stream)}
    categories = []
    for hs, name in CATEGORIES:
        values = []
        for year in range(2006, 2026):
            r = rows[hs, year]
            china, world = float(r['china_imports_usd_nominal']), float(r['world_imports_usd_nominal'])
            share = float(r['china_share_pct'])
            assert world > 0 and 0 <= share <= 100
            assert abs(share - china / world * 100) < 1e-8
            assert suppliers[hs, year, '0'] == world
            shares = [round(100 * suppliers.get((hs, year, code), 0) / world, 6)
                      for code in ['156', '484', '704', '490']]
            shares.append(round(100 - sum(shares), 6))
            assert min(shares) >= 0 and abs(sum(shares) - 100) < 1e-5
            assert abs(shares[0] - share) < 1e-5
            values.append({'share': round(share, 6), 'china': china, 'world': world, 'suppliers': shares})
        categories.append({'hs': hs, 'name': name, 'values': values})
    inflation = json.loads((root / 'processed/inflation_factors.json').read_text())
    events = json.loads((root / 'processed/policy_events.json').read_text())
    return {'categories': categories, 'inflation': inflation, 'events': events,
            'supplier_order': ['China', 'Mexico', 'Vietnam', 'Taiwan', 'Other'],
            'trade_source': 'Existing UN Comtrade annual extract; original retrieval date unknown',
            'scope': '8 selected categories, 2006–2025. Census monthly data is separate.'}

def main():
    content = json.dumps(payload(), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    original = SITE.read_text()
    updated, count = re.subn(r'(<script type="application/json" id="trade-explorer-data">).*?(</script>)',
                            lambda m: m[1] + content + m[2], original, flags=re.S)
    if count != 1:
        raise ValueError('Expected exactly one explorer data block; website left unchanged')
    SITE.write_text(updated)
    print('Updated 8 categories × 20 years, CPI factors, and selected policy events in draft.html')

if __name__ == '__main__':
    main()
