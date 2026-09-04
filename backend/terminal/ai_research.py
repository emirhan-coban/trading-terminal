import asyncio,json,os
def fallback(i,f,s):
 parts=[f"Trend skoru {s.get('trend_score','—')}, RSI {s.get('rsi','—')} ve 20 dönemlik momentum %{s.get('momentum_20d','—')}." if s else "Teknik veri mevcut değil."]
 if f and f.get("trailing_pe") is not None:parts.append(f"F/K {f['trailing_pe']:.2f}; tek başına değerleme kararı değildir.")
 elif f and f.get("market_cap") is not None:parts.append(f"Raporlanan piyasa değeri {f['market_cap']:.0f} {f.get('currency') or ''}.")
 parts.append("Gözlemsel araştırmadır; kesin AL/SAT sinyali değildir.");return " ".join(parts)
async def summarize(i,f,s):
 key=os.getenv("GEMINI_API_KEY","")
 if not key:return {"text":fallback(i,f,s),"model":"deterministic","ai":False}
 try:
  import google.generativeai as genai;genai.configure(api_key=key);model=genai.GenerativeModel("gemini-2.5-flash");payload={"instrument":{"id":i.id,"name":i.name,"asset_class":i.asset_class.value},"fundamentals":f,"technical":s};prompt="Yalnız JSON verisini kullanarak Türkçe 4 cümlelik dengeli özet yaz. Veri uydurma, kesin AL/SAT deme.\n"+json.dumps(payload,default=str);response=await asyncio.to_thread(model.generate_content,prompt);return {"text":response.text.strip(),"model":"gemini-2.5-flash","ai":True}
 except Exception:return {"text":fallback(i,f,s),"model":"deterministic-fallback","ai":False}
