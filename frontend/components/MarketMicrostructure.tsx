'use client';
import {useEffect,useState} from 'react';
import type {Instrument} from '@/lib/terminal-api';

type Trade={trade_id:number;price:number;quantity:number;buyer_maker:boolean};
type Depth={bids:[number,number][];asks:[number,number][]};
export default function MarketMicrostructure({instrument}:{instrument:Instrument}){
 const [trades,setTrades]=useState<Trade[]>([]),[depth,setDepth]=useState<Depth|null>(null),[tab,setTab]=useState<'trades'|'depth'>('trades');
 useEffect(()=>{if(!instrument.data_capabilities.includes('depth'))return;const base=(process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000').replace(/^http/,'ws'),ws=new WebSocket(`${base}/api/v1/ws/market/${instrument.id}`);ws.onmessage=e=>{const packet=JSON.parse(e.data),data=packet.data;if(data?.type==='trade')setTrades(rows=>[data,...rows].slice(0,30));if(packet.topic?.startsWith('depth:'))setDepth(data)};return()=>ws.close()},[instrument]);
 if(!instrument.data_capabilities.includes('depth'))return <div className="empty"><p>Order book mevcut değil</p><small>Sağlayıcı gerçek depth sunmadığı için sentetik veri gösterilmez.</small></div>;
 return <div className="micro"><div className="watch-tabs"><button className={tab==='trades'?'active':''} onClick={()=>setTab('trades')}>Time & Sales</button><button className={tab==='depth'?'active':''} onClick={()=>setTab('depth')}>Order Book</button></div>{tab==='trades'?<div className="micro-list">{trades.map(t=><div key={t.trade_id}><span className={t.buyer_maker?'down':'up'}>{t.price.toFixed(2)}</span><b>{t.quantity.toFixed(5)}</b></div>)}</div>:<div className="book"><div>{depth?.asks.slice().reverse().map(([p,q])=><div key={p}><span className="down">{p.toFixed(2)}</span><b>{q.toFixed(5)}</b></div>)}</div><hr/><div>{depth?.bids.map(([p,q])=><div key={p}><span className="up">{p.toFixed(2)}</span><b>{q.toFixed(5)}</b></div>)}</div></div>}</div>;
}
