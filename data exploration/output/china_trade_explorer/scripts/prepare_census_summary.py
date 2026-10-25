"""Validate cached Census downloads and build monthly China/World chart tables."""
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main(root=ROOT):
    report = json.loads((root / 'metadata/census_download_status.json').read_text())
    with (root / 'processed/census_monthly_categories.csv').open() as f:
        records = list(csv.DictReader(f))
    with (root / 'processed/cpi_monthly_2006_2025.csv').open() as f:
        inflation = {r['date']: r for r in csv.DictReader(f)}
    assert not report['gaps'], 'Download has gaps; inspect census_download_status.json'
    assert len(records) == report['records']['HS2']
    for source in report['files']:
        assert 'key=' not in source['url_without_key']
        assert hashlib.sha256((root / source['path']).read_bytes()).hexdigest() == source['sha256']
    groups = defaultdict(dict)
    for row in records:
        key = row['I_COMMODITY'], row['time']
        assert row['CTY_CODE'] not in groups[key], 'Duplicate category/month/country'
        assert row['COMM_LVL'] == 'HS2'
        groups[key][row['CTY_CODE']] = row
    params = report['parameters']
    expected = {(hs, f'{year}-{month:02d}') for hs in params['chapters']
                for year in range(params['start'], params['end'] + 1) for month in range(1, 13)}
    assert set(groups) == expected, 'Missing category/month observations'
    output, reconciliation = [], []
    for (hs, date), countries in sorted(groups.items()):
        assert '-' in countries, f'Missing reported World total for {hs}/{date}'
        world_row, china_row = countries['-'], countries.get('5700')
        assert china_row is not None, f'Missing China observation for {hs}/{date}'
        world, china = int(world_row['CON_VAL_MO']), int(china_row['CON_VAL_MO'])
        assert world > 0 and 0 <= china <= world
        duties = int(china_row['CAL_DUT_MO'])
        factor_text = inflation[date]['factor_to_2025_usd']
        factor = float(factor_text) if factor_text else None
        # Census country groups (e.g. 0003 EU) overlap individual suppliers.
        individual = [r for code, r in countries.items() if code.isdigit() and int(code) >= 1000]
        partner_sum = sum(int(r['CON_VAL_MO']) for r in individual)
        reconciliation.append({'hs2': hs, 'date': date, 'world_imports_usd': world,
                               'individual_supplier_sum_usd': partner_sum,
                               'difference_usd': partner_sum - world})
        output.append({'date': date, 'hs2': hs, 'chapter': world_row['I_COMMODITY_LDESC'],
                       'china_imports_usd_nominal': china, 'world_imports_usd_nominal': world,
                       'china_share_pct': 100 * china / world,
                       'china_calculated_duties_usd': duties,
                       'china_effective_duty_pct': 100 * duties / china if china else None,
                       'cpi_factor_to_2025': factor,
                       'china_imports_usd_2025_cpi': round(china * factor, 2) if factor else None,
                       'world_imports_usd_2025_cpi': round(world * factor, 2) if factor else None,
                       'cpi_missing': factor is None,
                       'source': 'U.S. Census International Trade API',
                       'trade_basis': 'Imports for consumption'})
    def csv_file(path, rows):
        with (root / path).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    csv_file('processed/census_monthly_category_summary.csv', output)
    csv_file('metadata/census_world_reconciliation.csv', reconciliation)
    status = json.loads((root / 'metadata/status.json').read_text())
    status.update({'census_monthly': 'ready_authenticated_download',
                   'census_monthly_rows': len(records),
                   'census_category_month_rows': len(output),
                   'census_period': f"{params['start']}-01/{params['end']}-12",
                   'quantity': 'not_downloaded_specific_products_and_comparable_units_required'})
    (root / 'metadata/status.json').write_text(json.dumps(status, indent=2) + '\n')
    validation = {'passed': True, 'validated_utc': datetime.now(timezone.utc).isoformat(),
                  'authenticated_download': True, 'raw_files': len(report['files']),
                  'raw_records': len(records), 'category_months': len(output), 'gaps': report['gaps'],
                  'duplicate_keys': 0, 'china_and_world_present_every_month': True,
                  'all_sha256_hashes_match': True, 'provenance_urls_have_no_key': True,
                  'country_groups_excluded_from_supplier_sum': sorted({r['CTY_CODE'] for r in records if r['CTY_CODE'].isdigit() and int(r['CTY_CODE']) < 1000}),
                  'max_world_reconciliation_difference_usd': max(abs(r['difference_usd']) for r in reconciliation),
                  'missing_inflation_category_months': sum(r['cpi_missing'] for r in output),
                  'missing_cpi_dates': sorted({r['date'] for r in output if r['cpi_missing']})}
    (root / 'metadata/census_validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    main_validation = json.loads((root / 'metadata/validation.json').read_text())
    main_validation.update({'census_authenticated_download_tested': True,
                            'census_validation_report': 'census_validation.json'})
    (root / 'metadata/validation.json').write_text(json.dumps(main_validation, indent=2) + '\n')
    print(json.dumps(validation, indent=2))

if __name__ == '__main__':
    main()
