'use client';
import {useEffect,useState} from 'react';
import SynchronizedCharts from '@/components/SynchronizedCharts';
import {Candle,terminalApi} from '@/lib/terminal-api';

export default function MultiChartPage(){const [rows,setRows]=useState<{name:string;rows:Candle[]}[]>([]),[timeframe,setTimeframe]=useState('15m');useEffect(()=>{Promise.all([terminalApi.candles('crypto:binance:btcusdt',timeframe),terminalApi.candles('crypto:binance:ethusdt',timeframe)]).then(([btc,eth])=>setRows([{name:'BTC/USDT',rows:btc.data},{name:'ETH/USDT',rows:eth.data}])).catch(()=>setRows([]))},[timeframe]);return <main className="multi-page"><header><h1>Senkronize Çoklu Grafik</h1><select value={timeframe} onChange={e=>setTimeframe(e.target.value)}>{['1m','5m','15m','1h','4h','1d'].map(x=><option key={x}>{x}</option>)}</select></header><SynchronizedCharts series={rows}/></main>}
