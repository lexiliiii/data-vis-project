"""Resume Census monthly downloads. Key stays local; no key is written to data or logs."""
import argparse, csv, hashlib, json, os, re, time
import urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE='https://api.census.gov/data/timeseries/intltrade/imports/hs'
CHAPTERS=['10','12','27','28','30','39','61','62','72','73','84','85','87','90','94','95']
ROOT=Path(__file__).resolve().parents[1]

def load_key(path):
 key=path.read_text().strip() if path else os.environ.get('CENSUS_API_KEY','').strip()
 if key and not re.fullmatch(r'[A-Za-z0-9]+',key):raise ValueError('Key file must contain only the activated API key, with no variable assignment.')
 return key

def request(params,key):
 url=BASE+'?'+urllib.parse.urlencode({**params,'key':key})
 for attempt in range(4):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'CS6730 academic trade visualization'})
   with urllib.request.urlopen(req,timeout=90) as r:
    if r.status==204:return None
    body=r.read()
   if body.lstrip().startswith(b'<'):raise RuntimeError('Census returned HTML instead of data; check that the key is activated.')
   data=json.loads(body)
   if not isinstance(data,list) or not data or not isinstance(data[0],list):raise RuntimeError('Census returned an unexpected data format.')
   return data
  except urllib.error.HTTPError as e:
   if e.code not in [429,500,502,503,504] or attempt==3:raise RuntimeError(f'Census HTTP {e.code}; request URL withheld to protect the key.') from None
  except urllib.error.URLError:
   if attempt==3:raise RuntimeError('Census network request failed; key and URL withheld.') from None
  time.sleep(2**attempt)

def decode(table):
 names=table[0]
 if any(len(r)!=len(names) for r in table[1:]):raise ValueError('Malformed response row')
 # Census can repeat a column requested in both `get` and a predicate.
 # Collapse identical copies only; never silently discard conflicting data.
 rows=[]
 for values in table[1:]:
  row={}
  for name,value in zip(names,values):
   if name in row and row[name]!=value:raise ValueError(f'Conflicting duplicate response column: {name}')
   row[name]=value
  rows.append(row)
 return rows

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--key-file',type=Path);p.add_argument('--output',type=Path,default=ROOT)
 p.add_argument('--start',type=int,default=2010);p.add_argument('--end',type=int,default=2025)
 p.add_argument('--chapters',nargs='+',default=CHAPTERS)
 p.add_argument('--products',nargs='*',default=[],help='Exact ten-digit HTS codes for quantity. Historical code changes require review.')
 p.add_argument('--plan',action='store_true',help='Show request scope without network or a key')
 p.add_argument('--workers',type=int,default=4,choices=range(1,5),help='Up to four concurrent requests; cached files are reused')
 a=p.parse_args()
 if not 2010<=a.start<=a.end<=2025:p.error('Use a year range within 2010–2025 for this historical package.')
 if any(not re.fullmatch(r'\d{2}',c) for c in a.chapters):p.error('Chapters must be two-digit strings.')
 if any(not re.fullmatch(r'\d{10}',c) for c in a.products):p.error('Products must be exact ten-digit strings.')
 print(f'Scope: {len(a.chapters)} chapters, {len(a.products)} specific products, {a.start}–{a.end}; all suppliers plus reported totals.')
 if a.plan:return
 key=load_key(a.key_file)
 if not key:raise SystemExit('Census requires an activated API key. Set CENSUS_API_KEY or pass --key-file /path/to/private/key.txt. No data downloaded.')
 raw=a.output/'raw'/'census';raw.mkdir(parents=True,exist_ok=True)
 out=a.output/'processed';out.mkdir(parents=True,exist_ok=True)
 metadata=a.output/'metadata';metadata.mkdir(parents=True,exist_ok=True)
 provenance=[];allrows={'HS2':[],'HS10':[]};gaps=[]
 def fetch_one(level,code,year):
    fields=['CTY_CODE','CTY_NAME','I_COMMODITY_LDESC','CON_VAL_MO','CAL_DUT_MO']
    if level=='HS10':fields+=['CON_QY1_MO','CON_QY1_MO_FLAG','UNIT_QY1','CON_QY2_MO','CON_QY2_MO_FLAG','UNIT_QY2']
    params={'get':','.join(fields),'I_COMMODITY':code,'COMM_LVL':level,'time':f'from {year}-01 to {year}-12'}
    dest=raw/f'{level}_{code}_{year}.json'
    if dest.exists():table=json.loads(dest.read_text())
    else:
     table=request(params,key)
     if table is None:return level,[],None,{'level':level,'code':code,'year':year,'reason':'HTTP 204: no returned data'}
     decode(table)
     part=dest.with_suffix('.part');part.write_text(json.dumps(table));part.replace(dest)
     time.sleep(.3)
    rows=decode(table)
    print(level,code,year,len(rows),'rows',flush=True)
    return level,rows,{'path':str(dest.relative_to(a.output)),'url_without_key':BASE+'?'+urllib.parse.urlencode(params),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},None
 with ThreadPoolExecutor(max_workers=a.workers) as pool:
  futures=[pool.submit(fetch_one,level,code,year) for level,codes in [('HS2',a.chapters),('HS10',a.products)] for code in codes for year in range(a.start,a.end+1)]
  for future in as_completed(futures):
   level,rows,source,gap=future.result()
   allrows[level].extend(rows)
   if source:provenance.append(source)
   if gap:gaps.append(gap)
 provenance.sort(key=lambda x:x['path'])
 gaps.sort(key=lambda x:(x['level'],x['code'],x['year']))
 for level,rows in allrows.items():
  if not rows:continue
  rows.sort(key=lambda r:(r['I_COMMODITY'],r['time'],r['CTY_CODE']))
  path=out/('census_monthly_categories.csv' if level=='HS2' else 'census_monthly_product_quantities.csv')
  with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 report={'finished_utc':datetime.now(timezone.utc).isoformat(),'basis':'imports for consumption; nominal current USD','preserved_raw_flags_and_units':True,'quantity_policy':'Never sum unlike units or code revisions. Retain missing flags. A zero can mean missing.','records':{k:len(v) for k,v in allrows.items()},'gaps':gaps,'files':provenance,'parameters':{'start':a.start,'end':a.end,'chapters':a.chapters,'products':a.products}}
 (metadata/'census_download_status.json').write_text(json.dumps(report,indent=2))
 print('Download finished. Check metadata/census_download_status.json for coverage. No API key was saved.')

if __name__=='__main__':main()
