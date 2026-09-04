'use client';
import {useEffect} from 'react';

const EN:Record<string,string>={'Piyasalar':'Markets','Tarayıcı':'Screener','Alarmlar':'Alerts','Portföy':'Portfolio','Araştırma':'Research','Ayarlar':'Settings','İZLEME':'WATCHLIST','Karma':'Mixed','Kripto':'Crypto','Hisse':'Stocks','Göstergeler':'Indicators','Kaynak:':'Source:','SEANS VERİSİ':'SESSION DATA','Son:':'Last:','EMİR BİLETİ':'ORDER TICKET','ALIŞ':'BUY','SATIŞ':'SELL','Emir türü':'Order type','Piyasa':'Market','Miktar':'Quantity','Limit fiyatı':'Limit price','Stop fiyatı':'Stop price','Kâr al':'Take profit','Zarar durdur':'Stop loss','Alış':'Bid','Satış':'Ask','Tahmini değer':'Estimated value','Komisyon':'Commission','PAPER EMİR GÖNDER':'SUBMIT PAPER ORDER','POZİSYONLAR':'POSITIONS','Açık pozisyon yok':'No open positions','PİYASA AKIŞI':'MARKET FLOW','Çalışma Alanı ve Veri Kalitesi':'Workspace & Data Quality','Çalışma alanı':'Workspace','Türkçe':'Turkish','SAĞLIKLI':'HEALTHY','KISMİ KESİNTİ':'DEGRADED','KONTROL EDİLİYOR':'CHECKING','Sembol, şirket veya kripto ara':'Search symbol, company or crypto','Gerçek piyasa verisi bekleniyor':'Waiting for market data','Order book mevcut değil':'Order book unavailable'};
const TR=Object.fromEntries(Object.entries(EN).map(([a,b])=>[b,a]));

export default function LocaleTranslator(){
 useEffect(()=>{
  function apply(locale:string){
   const map=locale==='en'?EN:TR,walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let node:Node|null;
   while((node=walker.nextNode())){const text=node as Text,trim=text.data.trim(),translated=map[trim];if(translated)text.data=text.data.replace(trim,translated)}
   if(document.documentElement.lang!==locale)document.documentElement.lang=locale;
  }
  const handler=((event:CustomEvent<string>)=>apply(event.detail)) as EventListener;
  window.addEventListener('nexus-locale-change',handler);apply(localStorage.getItem('nexus-locale')||'tr');
  const observer=new MutationObserver(()=>apply(localStorage.getItem('nexus-locale')||'tr'));observer.observe(document.body,{subtree:true,childList:true,attributes:true});
  return()=>{observer.disconnect();window.removeEventListener('nexus-locale-change',handler)};
 },[]);return null;
}
