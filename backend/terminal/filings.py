import asyncio,json,os
from urllib.request import Request,urlopen

async def sec_filings(instrument,limit=20):
 cik=instrument.provider_symbols.get("sec_cik")
 if not cik:return []
 agent=os.getenv("SEC_USER_AGENT","NexusTerminal research@example.invalid")
 def fetch():
  with urlopen(Request(f"https://data.sec.gov/submissions/CIK{cik}.json",headers={"User-Agent":agent,"Accept-Encoding":"gzip, deflate"}),timeout=12) as response:return json.loads(response.read())
 data=await asyncio.to_thread(fetch);recent=data.get("filings",{}).get("recent",{});rows=[]
 for form,accession,document,date in zip(recent.get("form",[]),recent.get("accessionNumber",[]),recent.get("primaryDocument",[]),recent.get("filingDate",[])):
  if form not in {"10-K","10-Q","8-K","DEF 14A"}:continue
  clean=accession.replace("-","");rows.append({"instrument_id":instrument.id,"form":form,"filed_at":date,"accession_number":accession,"title":f"{form} filing","source":"SEC EDGAR","url":f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{clean}/{document}"})
  if len(rows)>=limit:break
 return rows
