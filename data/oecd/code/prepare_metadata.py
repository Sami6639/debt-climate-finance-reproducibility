"""Convert immutable official OECD codebooks into analytical lookup tables."""
from pathlib import Path
import openpyxl,csv,json,hashlib
from xml.etree import ElementTree as E
ROOT=Path(__file__).resolve().parents[1];p=ROOT/'metadata'
w=openpyxl.load_workbook(p/'DAC-CRS-CODES.xlsx',read_only=True,data_only=True)
for s in w:
 if s.title in ['Donor','Recipient','Nature of submission','Bi_Multi','Type of flow','Type of finance','Co-operation modalities','Markers']:
  rows=list(s.values)
  with open(p/(s.title.lower().replace(' ','_')+'.csv'),'w') as f:csv.writer(f).writerows(rows)
  if s.title=='Donor':
   out=[]
   for r in rows[3:]:
    for i,k in [(0,'DAC'),(5,'multilateral'),(10,'non-DAC'),(15,'private')]:
     if isinstance(r[i],(int,float)) and r[i+2]:out.append({'donor_code':int(r[i]),'donor_de_code':r[i+1],'donor_name':r[i+2],'donor_type':k})
   assert len({r['donor_code'] for r in out})==len(out)
   with open(p/'donor_classification.csv','w') as f:d=csv.DictWriter(f,fieldnames=list(out[0]));d.writeheader();d.writerows(out)
  if s.title=='Recipient':
   out=[{'recipient_code':int(r[0]),'recipient_name':r[1],'iso3':r[3]} for r in rows[1:] if isinstance(r[0],(int,float))]
   with open(p/'recipient_lookup.csv','w') as f:d=csv.DictWriter(f,fieldnames=list(out[0]));d.writeheader();d.writerows(out)
root=E.parse(p/'dataflow.xml').getroot();ns={'s':'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure','c':'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common'}
for c in root.findall('.//s:Codelist',ns):
 out=[]
 for x in c.findall('s:Code',ns):
  out.append({'code':x.attrib['id'],'name':next((n.text for n in x.findall('c:Name',ns) if n.attrib.get('{http://www.w3.org/XML/1998/namespace}lang')=='en'),None)})
 with open(p/(c.attrib['id']+'.csv'),'w') as f:d=csv.DictWriter(f,fieldnames=['code','name']);d.writeheader();d.writerows(out)
urls={'DAC-CRS-CODES.xlsx':'https://webfs.oecd.org/oda/DataCollection/Resources/DAC-CRS-CODES.xlsx','DAC-tables-CRS-codebook.xlsx':'https://webfs.oecd.org/oda/DataCollection/Resources/DAC-tables-CRS-codebook.xlsx','Deflators-base-2024.xlsx':'https://webfs.oecd.org/oda/DataCollection/Resources/Deflators-base-2024.xlsx','dataflow.xml':'https://sdmx.oecd.org/dcd-public/rest/dataflow/OECD.DCD.FSD/DSD_CRS@DF_CRS/1.6?references=all','CRS_README.txt':'https://webfs-dcd.oecd.org/files/dotStat/DSD_CRS/crs%20readme_en.txt','terms_conditions.html':'https://www.oecd.org/en/about/terms-conditions.html'}
out=[]
for file,url in urls.items():
 b=(p/file).read_bytes();out.append({'file':file,'url':url,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'retrieval_date_utc':'2026-10-07'})
(p/'metadata_source_manifest.json').write_text(json.dumps(out,indent=2))
