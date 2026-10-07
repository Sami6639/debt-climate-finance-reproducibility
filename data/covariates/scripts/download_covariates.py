#!/usr/bin/env python3
"""Download immutable official covariate sources. Existing downloads are not overwritten.
Source selection is documented in metadata/README.md. Requires only Python stdlib.
"""
import urllib.request,json,hashlib,datetime,time,concurrent.futures,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
CODES=['DT.TDS.DPPF.XP.ZS','DT.TDS.DPPG.XP.ZS','DT.TDS.DECT.EX.ZS','DT.TDS.DPPG.CD','DT.TDS.DIMF.CD','DT.TDS.DECT.CD','DT.DOD.DECT.GN.ZS','DT.DOD.DECT.CD','DT.DOD.DPPG.CD','BX.GSR.TOTL.CD','BX.GSR.GNFS.CD','NY.GDP.PCAP.KD','NY.GDP.PCAP.CD','NY.GNP.PCAP.KD','NY.GNP.PCAP.CD','SP.POP.TOTL']
TASKS=[]
for c in CODES:
 TASKS += [(f'raw/wb_{c}_2010_2024.json', f'https://api.worldbank.org/v2/country/all/indicator/{c}?source=2&date=2010:2024&format=json&per_page=20000'),(f'raw/wb_metadata_{c}.json',f'https://api.worldbank.org/v2/indicator/{c}?source=2&format=json')]
TASKS += [('raw/wb_countries.json','https://api.worldbank.org/v2/country?format=json&per_page=400'),('raw/wb_sources.json','https://api.worldbank.org/v2/source?format=json&per_page=100'),('raw/pvcci_ferdi.xlsx','https://ferdi.fr/dl/df-ree2t55nEkkw7KJwo6Kfc6n7/data-physical-vulnerability-to-climate-change-index-pvcci.xlsx'),('raw/pvcci_ferdi_landing.html','https://ferdi.fr/en/indicators/an-index-of-physical-vulnerability-to-climate-change'),('raw/pvcci_datagouv_record.json','https://www.data.gouv.fr/api/1/datasets/indicateur-de-vulnerabilite-physique-au-changement-climatique/'),('raw/pvcci_datagouv.xlsx','https://static.data.gouv.fr/resources/indicateur-de-vulnerabilite-physique-au-changement-climatique/20260601-094547/donnees-indicateur-de-vulnerabilite-physique-au-changement-climatique.xlsx'),('raw/pvcci_method_2018.pdf','https://ferdi.fr/dl/df-cgNSGwK15ZjskHbTazpGKHzq/ferdi-p213-a-physical-vulnerability-to-climate-change-index-which-are-the.pdf'),('raw/pvcci_method_2022.pdf','https://ferdi.fr/dl/df-bkMSsFLrDt9rahw7WnRGbHrY/ferdi-wp305-the-physical-vulnerability-to-climate-change-index-computed-at.pdf'),('raw/wb_ppg_imf_glossary.html','https://databank.worldbank.org/metadataglossary/world-development-indicators/series/DT.TDS.DPPF.XP.ZS')]
TASKS.append(('raw/un_2025_refinement_report.pdf','https://documents.un.org/doc/undoc/gen/n24/402/01/pdf/n2440201.pdf'))
def download(task):
 rel,url=task; dest=ROOT/rel
 if dest.exists():
  b=dest.read_bytes(); sidecar=ROOT/'metadata'/f'{dest.name}.provenance.json'
  prior=json.loads(sidecar.read_text()) if sidecar.exists() else {}
  return {**prior,'file':rel,'url':url,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'status':'existing immutable file'}
 for attempt in range(4):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Academic research data acquisition; Python urllib'})
   with urllib.request.urlopen(req,timeout=90) as r:b=r.read();headers=dict(r.headers);finalurl=r.url
   if rel.endswith('.json'):json.loads(b)
   dest.write_bytes(b)
   result={'file':rel,'url':url,'resolved_url':finalurl,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'headers':headers,'status':'downloaded'}
   (ROOT/'metadata'/f'{dest.name}.provenance.json').write_text(json.dumps(result,indent=2))
   print('OK',rel,len(b),flush=True); return result
  except Exception as e:
   if attempt<3:time.sleep(2*(attempt+1))
   else:print('FAIL',rel,str(e),flush=True);return {'file':rel,'url':url,'status':'failed','error':str(e)}
if __name__=='__main__':
 for folder in ['raw','processed','metadata']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex: results=list(ex.map(download,TASKS))
 (ROOT/'metadata/download_manifest.json').write_text(json.dumps(results,indent=2))
 print('Done:',len(results),'sources;',sum(x['status']=='failed' for x in results),'failed')
