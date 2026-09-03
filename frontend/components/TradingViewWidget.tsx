'use client';

import { useEffect, useRef } from 'react';

// BIST dışındaki paritelerde (kripto, forex, ABD hisseleri gibi) TradingView'ın
// kendi veri akışı lisanslı olduğu için gerçek TradingView widget'ını kullanıyoruz.
// BIST bu kapsamda değil (bkz. PriceChart.tsx) — o yüzden bu component sadece
// BIST dışı semboller için çağrılıyor.
export default function TradingViewWidget({ symbol }: { symbol: string }) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;
    container.current.innerHTML = '';

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol,
      interval: 'D',
      timezone: 'Europe/Istanbul',
      theme: 'dark',
      style: '1',
      locale: 'tr',
      backgroundColor: '#0A0E12',
      gridColor: 'rgba(31, 41, 51, 0.5)',
      hide_top_toolbar: false,
      allow_symbol_change: false,
      support_host: 'https://www.tradingview.com',
    });

    container.current.appendChild(script);
  }, [symbol]);

  return (
    <div className="border border-[#1F2933]">
      <div ref={container} style={{ height: '480px' }} />
    </div>
  );
}
