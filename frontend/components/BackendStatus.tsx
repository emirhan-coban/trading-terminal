'use client';
import {useEffect,useState} from 'react';

const BASE=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';

/** Free hosting tiers sleep when idle; tell visitors the API is waking up instead of showing an empty terminal. */
export default function BackendStatus(){
 const [ready,setReady]=useState(true);
 useEffect(()=>{
  let cancelled=false,timer:ReturnType<typeof setTimeout>;
  async function ping(){
   try{
    const r=await fetch(`${BASE}/health`,{cache:'no-store'});
    if(!r.ok)throw new Error('down');
    if(!cancelled)setReady(true)
   }catch{
    if(cancelled)return;
    setReady(false);timer=setTimeout(ping,4000)
   }
  }
  const first=setTimeout(()=>{if(!cancelled)ping()},0);
  return()=>{cancelled=true;clearTimeout(first);clearTimeout(timer)}
 },[]);
 if(ready)return null;
 return <div role="status" style={{position:'fixed',top:0,left:0,right:0,zIndex:50,padding:'6px 12px',background:'#e5b657',color:'#1a1a1a',font:'12px ui-monospace,monospace',textAlign:'center'}}>API sunucusu uyanıyor (ücretsiz barındırma, ~1 dakika sürebilir)… / Backend is waking up, this can take up to ~1 minute.</div>
}
