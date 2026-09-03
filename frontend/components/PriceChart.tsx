'use client';

import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts';

type PricePoint = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

export default function PriceChart({ data }: { data: PricePoint[] }) {
  const container = useRef<HTMLDivElement>(null);
  const [interval, setInterval] = useState<'daily' | 'weekly' | 'monthly'>('daily');

  useEffect(() => {
    if (!container.current || data.length === 0) return;

    const chart = createChart(container.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0A0E12' },
        textColor: '#8A97A3',
      },
      grid: {
        vertLines: { color: '#1F2933' },
        horzLines: { color: '#1F2933' },
      },
      width: container.current.clientWidth,
      height: 500,
      timeScale: { borderColor: '#1F2933', timeVisible: false },
      rightPriceScale: { borderColor: '#1F2933' },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#3DDC84',
      downColor: '#FF5C5C',
      borderVisible: false,
      wickUpColor: '#3DDC84',
      wickDownColor: '#FF5C5C',
    });

    candleSeries.setData(
      data.map((d) => ({
        time: d.time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    if (data.some((d) => d.volume)) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      });

      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      volumeSeries.setData(
        data.map((d) => ({
          time: d.time,
          value: d.volume || 0,
          color: d.close >= d.open ? 'rgba(61,220,132,0.3)' : 'rgba(255,92,92,0.3)',
        }))
      );
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (container.current) {
        chart.applyOptions({ width: container.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, interval]);

  if (data.length === 0) {
    return (
      <div className="border border-[#1F2933] p-8 text-[#8A97A3] text-sm text-center">
        Henüz fiyat verisi yok.
      </div>
    );
  }

  return (
    <div className="border border-[#1F2933]">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#1F2933]">
        {(['daily', 'weekly', 'monthly'] as const).map((tf) => (
          <button
            key={tf}
            onClick={() => setInterval(tf)}
            className={`px-2 py-1 text-xs font-[family-name:var(--font-mono)] rounded transition ${
              interval === tf
                ? 'bg-[#1F2933] text-[#E8E6E1]'
                : 'text-[#8A97A3] hover:text-[#E8E6E1]'
            }`}
          >
            {tf === 'daily' ? 'Günlük' : tf === 'weekly' ? 'Haftalık' : 'Aylık'}
          </button>
        ))}
      </div>
      <div ref={container} />
    </div>
  );
}
