"""Download public sources and prepare the China trade explorer data package."""
import csv, hashlib, json, shutil, time, urllib.request, urllib.error
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'us_imports_by_chapter_partner.csv'
CHAPTERS=['10','12','27','28','30','39','61','62','72','73','84','85','87','90','94','95']
STAMP=datetime.now(timezone.utc).isoformat()
DOWNLOADS=[
 ('metadata/census_variables.json','https://api.census.gov/data/timeseries/intltrade/imports/hs/variables.json'),
 ('raw/policy/list1.html','https://ustr.gov/issue-areas/enforcement/section-301-investigations/section-301-china/34-billion-trade-action'),
 ('raw/policy/list2.html','https://ustr.gov/issue-areas/enforcement/section-301-investigations/section-301-china/16-billion-trade-action'),
 ('raw/policy/list3.html','https://ustr.gov/issue-areas/enforcement/section-301-investigations/section-301-china/200-billion-trade-action'),
 ('raw/policy/list4.html','https://ustr.gov/issue-areas/enforcement/section-301-investigations/section-301-china/300-billion-trade-action'),
 ('raw/policy/list1_notice.pdf','https://ustr.gov/sites/default/files/2018-13248.pdf'),
 ('raw/policy/list2_notice.pdf','https://ustr.gov/sites/default/files/enforcement/301Investigations/2018-17709.pdf'),
 ('raw/policy/list3_notice.pdf','https://ustr.gov/sites/default/files/enforcement/301Investigations/83%20FR%2047974.pdf'),
 ('raw/policy/list3_remove_subheadings.pdf','https://ustr.gov/sites/default/files/enforcement/301Investigations/2018-21303.pdf'),
 ('raw/policy/list3_delay_dec2018.pdf','https://ustr.gov/sites/default/files/enforcement/301Investigations/83_FR_65198.pdf'),
 ('raw/policy/list3_delay_mar2019.pdf','https://ustr.gov/sites/default/files/enforcement/301Investigations/84_FR_7966.pdf'),
 ('raw/policy/list3_increase_may2019.pdf','https://ustr.gov/sites/default/files/enforcement/301Investigations/84_FR_20459.pdf'),
 ('raw/policy/list4a_list4b_notice.pdf','https://ustr.gov/sites/default/files/enforcement/301Investigations/Notice_of_Modification_(List_4A_and_List_4B).pdf'),
 ('raw/policy/list4_rate_aug2019.pdf','https://ustr.gov/sites/default/files/enforcement/301Investigations/Notice_of_Modification%E2%80%93August_2019.pdf'),
 ('raw/policy/list4a_reduction_jan2020.pdf','https://ustr.gov/sites/default/files/enforcement/301Investigations/Notice_of_Modification-January_2020.pdf'),
 ('raw/policy/phase_one.html','https://ustr.gov/phase-one'),
 ('raw/policy/who_pandemic_20200311.pdf','https://www.who.int/docs/default-source/coronaviruse/situation-REPORTS/20200311-SITREP-51-COVID-19.PDF'),
 ('raw/policy/section301_review_2024.html','https://ustr.gov/about-us/policy-offices/press-office/press-releases/2024/september/ustr-finalizes-action-china-tariffs-following-statutory-four-year-review'),
 ('raw/policy/reciprocal_announcement_2025.pdf','https://www.govinfo.gov/content/pkg/FR-2025-04-07/pdf/2025-06063.pdf'),
 ('raw/policy/usitc_archive_index.html','https://hts.usitc.gov/download/archive'),
]

def dump(path,obj):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def write_csv(path,rows):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fetch(path,url):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():return {'path':path,'url':url,'status':'cached','bytes':p.stat().st_size,'sha256':digest(p)}
 for attempt in range(3):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'CS6730 educational trade data project'})
   with urllib.request.urlopen(req,timeout=45) as r:body=r.read();mime=r.headers.get('Content-Type','')
   if path.endswith('.pdf') and not body.startswith(b'%PDF'):raise ValueError('Expected PDF, received another format')
   if path.endswith('.json'):json.loads(body)
   p.write_bytes(body)
   print('Downloaded',path,len(body),flush=True)
   return {'path':path,'url':url,'status':'downloaded','retrieved_utc':datetime.now(timezone.utc).isoformat(),'content_type':mime,'bytes':len(body),'sha256':digest(p)}
  except Exception as e:
   if isinstance(e,urllib.error.HTTPError) and e.code in [401,403,404]:break
   if attempt<2:time.sleep(2**attempt)
 print('Unavailable',path,str(e) if 'e' in locals() else 'request failed',flush=True)
 return {'path':path,'url':url,'status':'unavailable'}

def main():
 ROOT.mkdir(parents=True,exist_ok=True)
 raw=ROOT/'raw';(raw/'bls').mkdir(parents=True,exist_ok=True);(raw/'existing_comtrade').mkdir(exist_ok=True)
 manifest=[]
 monthly=[]
 for start,end in [(2006,2015),(2016,2025)]:
  dest=raw/'bls'/f'bls_cpi_post_{start}_{end}.json'
  if not dest.exists():
   request_body=json.dumps({'seriesid':['CUUR0000SA0'],'startyear':str(start),'endyear':str(end)}).encode()
   req=urllib.request.Request('https://api.bls.gov/publicAPI/v1/timeseries/data/',data=request_body,headers={'Content-Type':'application/json','User-Agent':'CS6730 academic trade visualization'})
   with urllib.request.urlopen(req,timeout=60) as response:body=response.read()
   parsed=json.loads(body)
   if parsed.get('status')!='REQUEST_SUCCEEDED':raise RuntimeError('BLS request failed; refusing to save invalid CPI data')
   dest.write_bytes(body)
  payload=json.loads(dest.read_text());assert payload['status']=='REQUEST_SUCCEEDED'
  assert payload['Results']['series'][0]['seriesID']=='CUUR0000SA0'
  manifest.append({'path':str(dest.relative_to(ROOT)),'url':'https://api.bls.gov/publicAPI/v1/timeseries/data/','request_method':'POST','request_body':{'seriesid':['CUUR0000SA0'],'startyear':str(start),'endyear':str(end)},'status':'downloaded','retrieved_utc':datetime.fromtimestamp(dest.stat().st_mtime,timezone.utc).isoformat(),'sha256':digest(dest)})
  for r in payload['Results']['series'][0]['data']:
   if r['period']=='M13':continue
   value=None if r['value']=='-' else float(r['value'])
   monthly.append({'date':f"{r['year']}-{r['period'][1:]}",'year':int(r['year']),'month':int(r['period'][1:]),'series_id':'CUUR0000SA0','cpi':value,'missing':value is None,'note':' | '.join(x.get('text','') for x in r.get('footnotes',[]) if x)})
 monthly.sort(key=lambda r:r['date']);assert len(monthly)==240;assert len({r['date'] for r in monthly})==240
 annual=[]
 for year in range(2006,2026):
  vals=[Decimal(str(r['cpi'])) for r in monthly if r['year']==year and r['cpi'] is not None]
  avg=float((sum(vals)/len(vals)).quantize(Decimal('.001'),rounding=ROUND_HALF_UP))
  annual.append({'year':year,'cpi_annual_average':avg,'months_observed':len(vals),'missing_months':','.join(str(r['month']) for r in monthly if r['year']==year and r['cpi'] is None),'method':'Mean of published nonmissing monthly CPI-U levels, rounded to 3 decimals'})
 assert annual[-1]['cpi_annual_average']==321.943
 base=annual[-1]['cpi_annual_average'];cpi={r['year']:r['cpi_annual_average'] for r in annual}
 for r in annual:r['factor_to_2025_usd']=base/r['cpi_annual_average']
 for r in monthly:r['factor_to_2025_usd']=base/r['cpi'] if r['cpi'] is not None else None
 write_csv('processed/cpi_monthly_2006_2025.csv',monthly);write_csv('processed/cpi_annual_2006_2025.csv',annual)
 snapshot=raw/'existing_comtrade'/'us_imports_by_chapter_partner.csv';shutil.copy2(SOURCE,snapshot)
 manifest.append({'path':str(snapshot.relative_to(ROOT)),'status':'reused_existing_local_extract_not_redownloaded','original_path':str(SOURCE),'original_download_date':'unknown','sha256':digest(snapshot)})
 rows=list(csv.DictReader(snapshot.open()));groups=defaultdict(list);clean=[]
 for r in rows:
  year=int(r['year']);hs=r['hs2'].zfill(2);code=int(r['partner_code']);nominal=float(r['imports_usd']);assert nominal>=0
  clean.append({'year':year,'hs2':hs,'chapter':r['chapter'],'partner_code':code,'partner_name':r['partner_name'],'imports_usd_nominal':nominal,'imports_usd_2025_cpi':round(nominal*base/cpi[year],2),'cpi_factor_to_2025':base/cpi[year],'source':'UN Comtrade existing project extract','trade_basis':'US-reported imports; original extractor primaryValue'})
  groups[hs,year].append(r)
 summaries=[];reconciliation=[]
 for (hs,year),g in sorted(groups.items()):
  bycode=defaultdict(float);names={}
  for r in g:bycode[int(r['partner_code'])]+=float(r['imports_usd']);names[int(r['partner_code'])]=r['partner_name']
  assert 0 in bycode and bycode[0]>0,(hs,year)
  world=bycode[0];cn=bycode.get(156,0);partner_sum=sum(v for k,v in bycode.items() if k!=0);top=max((k for k in bycode if k!=0),key=lambda k:bycode[k])
  reconciliation.append({'hs2':hs,'year':year,'world_usd':world,'sum_nonworld_partners_usd':partner_sum,'difference_usd':partner_sum-world})
  summaries.append({'hs2':hs,'chapter':g[0]['chapter'],'year':year,'china_imports_usd_nominal':cn,'world_imports_usd_nominal':world,'china_imports_usd_2025_cpi':round(cn*base/cpi[year],2),'world_imports_usd_2025_cpi':round(world*base/cpi[year],2),'china_share_pct':cn/world*100,'top_supplier':names[top],'top_supplier_share_pct':bycode[top]/world*100,'hhi':sum((v/world)**2 for k,v in bycode.items() if k!=0)*10000})
 assert len(summaries)==320
 write_csv('processed/annual_trade_by_supplier.csv',clean);write_csv('processed/annual_category_summary.csv',summaries);write_csv('metadata/world_total_reconciliation.csv',reconciliation)
 dump('processed/inflation_factors.json',{'series':'CUUR0000SA0','base_year':2025,'base_cpi':base,'method':'Annual CPI-U purchasing-power adjustment; not a physical-volume estimate','annual':annual,'missing_months':[r['date'] for r in monthly if r['missing']]})
 for path,url in DOWNLOADS:manifest.append(fetch(path,url))
 urls=dict(DOWNLOADS)
 specs=[
 ('301-list1','2018-07-06','effective','Section 301 List 1 begins','25% additional duty on covered products.','raw/policy/list1_notice.pdf',25),
 ('301-list2','2018-08-23','effective','Section 301 List 2 begins','25% additional duty on covered products.','raw/policy/list2_notice.pdf',25),
 ('301-list3','2018-09-24','effective','Section 301 List 3 begins','10% additional duty on covered products.','raw/policy/list3_notice.pdf',10),
 ('301-list3-increase','2019-05-10','effective','List 3 additional duty increases','10% to 25%; transit exceptions and later exclusions apply.','raw/policy/list3_increase_may2019.pdf',25),
 ('301-list4a','2019-09-01','effective','List 4A additional duty begins','15% on covered List 4A products; do not treat List 4B as implemented.','raw/policy/list4_rate_aug2019.pdf',15),
 ('phase-one','2020-01-15','signed','Phase One agreement signed','Signing date; does not itself define all tariff effective dates.','raw/policy/phase_one.html',None),
 ('301-list4a-reduction','2020-02-14','effective','List 4A additional duty reduced','15% to 7.5% on covered products.','raw/policy/list4a_reduction_jan2020.pdf',7.5),
 ('covid-pandemic','2020-03-11','global_shock','WHO characterizes COVID-19 as a pandemic','Context event, not a tariff measure.','raw/policy/who_pandemic_20200311.pdf',None),
 ('301-review-2024','2024-09-13','announced','Section 301 review finalized','Implementation dates and rates vary by product; no chapter-wide rate assigned.','raw/policy/section301_review_2024.html',None),
 ('reciprocal-2025','2025-04-02','announced','Reciprocal tariff executive order','Announcement only; subsequent amendments, exceptions and litigation are not mapped in this dataset.','raw/policy/reciprocal_announcement_2025.pdf',None),
 ]
 events=[{'id':i,'date':d,'date_type':t,'title':name,'description':desc,'additional_rate_percent':rate,'affected_hts_codes':None,'coverage_status':'not_yet_mapped','source_url':urls[path],'local_source':path,'source_downloaded':(ROOT/path).exists(),'scope_note':'Selected milestones only; not a complete tariff history or causal estimate'} for i,d,t,name,desc,path,rate in specs]
 dump('processed/policy_events.json',events)
 write_csv('processed/policy_events.csv',[{**e,'affected_hts_codes':''} for e in events])
 dump('metadata/sources.json',{'created_utc':STAMP,'downloads':manifest})
 previous_status=json.loads((ROOT/'metadata/status.json').read_text()) if (ROOT/'metadata/status.json').exists() else {}
 package_status={'annual_comtrade':'ready_reused_existing_extract','inflation':'ready_downloaded_240_month_slots_239_observations','census_monthly':'blocked_missing_api_key','quantity':'blocked_missing_census_key_and_specific_product_selection','policy_sources_downloaded':sum(1 for r in manifest if r['path'].startswith('raw/policy/') and r['status'] in ['downloaded','cached']),'policy_events':'10_selected_milestones_not_complete_history','policy_product_mapping':'not_done','policy_exclusions_and_2025_rate_history':'not_complete','trade_rows':len(clean),'category_year_rows':len(summaries),'cpi_base_year':2025}
 package_status.update({k:v for k,v in previous_status.items() if k.startswith('census_') or k=='quantity'})
 dump('metadata/status.json',package_status)
 print('READY',ROOT,'trade rows',len(clean),'category-years',len(summaries),flush=True)

if __name__=='__main__':main()
