'use client';

import { useState } from 'react';
import { apiCompare } from '@/lib/api';
import { scoreColor, stripIS, fmt } from '@/lib/utils';

type Row = {
  ticker: string;
  technical_score: number | null;
  indicators: Record<string, number | null>;
  financials: Record<string, number | null> | null;
  price: { close: number | null; change_pct?: number };
};

export default function ComparePage() {
  const [input, setInput] = useState('THYAO, ASELS, GARAN');
  const [rows, setRows] = useState<Row[]>([]);
  const [aiText, setAiText] = useState('');
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState('');

  const run = async (withAi: boolean) => {
    const tickers = input.split(',').map((t) => t.trim()).filter(Boolean);
    if (tickers.length < 2) {
      setError('En az 2 hisse girin (en fazla 4).');
      return;
    }
    if (withAi) setAiLoading(true); else setLoading(true);
    setError('');
    try {
      const data = await apiCompare(tickers.slice(0, 4), withAi);
      setRows(data.rows || []);
      if (withAi) setAiText(data.ai_comparison || '');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Karşılaştırılamadı');
    } finally {
      setLoading(false);
      setAiLoading(false);
    }
  };

  const metricRows: { label: string; get: (r: Row) => string; tone?: (r: Row) => string }[] = [
    { label: 'Son fiyat', get: (r) => (r.price.close != null ? fmt(r.price.close) : '—') },
    { label: 'Değişim %', get: (r) => (r.price.change_pct != null ? `%${r.price.change_pct.toFixed(2)}` : '—'),
      tone: (r) => (r.price.change_pct ?? 0) >= 0 ? 'text-[#3DDC84]' : 'text-[#FF5C5C]' },
    { label: 'Teknik skor', get: (r) => (r.technical_score != null ? r.technical_score.toFixed(1) : '—'),
      tone: (r) => scoreColor(r.technical_score) },
    { label: 'RSI (14)', get: (r) => fmt(r.indicators.rsi) },
    { label: 'MACD Hist', get: (r) => fmt(r.indicators.macd_hist, 4) },
    { label: 'SMA 20', get: (r) => fmt(r.indicators.sma20) },
    { label: 'ADX', get: (r) => fmt(r.indicators.adx) },
    { label: 'F/K', get: (r) => fmt(r.financials?.pe_ratio) },
    { label: 'PD/DD', get: (r) => fmt(r.financials?.pb_ratio) },
    { label: 'Temettü %', get: (r) => (r.financials?.dividend_yield != null ? `%${(r.financials.dividend_yield * 100).toFixed(2)}` : '—') },
  ];

  return (
    <div className="p-4 md:p-6">
      <h1 className="text-lg text-[#8A97A3] font-[family-name:var(--font-mono)] mb-6">Hisse Karşılaştırma</h1>

      <div className="flex flex-wrap gap-2 mb-4">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="THYAO, ASELS, GARAN"
          className="flex-1 min-w-64 bg-[#161D27] border border-[#1F2933] rounded px-3 py-2 text-sm font-[family-name:var(--font-mono)] focus:outline-none focus:border-[#3DDC84]" />
        <button onClick={() => run(false)} disabled={loading}
          className="bg-[#3DDC84] text-black text-sm font-semibold px-4 py-2 rounded hover:opacity-90 disabled:opacity-50">
          {loading ? '...' : 'Karşılaştır'}
        </button>
        <button onClick={() => run(true)} disabled={aiLoading || rows.length === 0}
          className="border border-[#3DDC84] text-[#3DDC84] text-sm px-4 py-2 rounded hover:bg-[#3DDC84]/10 disabled:opacity-50">
          {aiLoading ? '...' : 'AI yorumu'}
        </button>
      </div>

      {error && <div className="border border-[#FF5C5C] text-[#FF5C5C] text-sm p-3 mb-4">{error}</div>}

      {rows.length > 0 && (
        <div className="border border-[#1F2933] overflow-x-auto mb-4">
          <table className="w-full text-sm font-[family-name:var(--font-mono)]">
            <thead>
              <tr className="border-b border-[#1F2933]">
                <th className="text-left px-4 py-2.5 text-[#8A97A3] text-xs font-medium">Metrik</th>
                {rows.map((r) => (
                  <th key={r.ticker} className="text-right px-4 py-2.5 font-semibold">{stripIS(r.ticker)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {metricRows.map((m) => (
                <tr key={m.label} className="border-b border-[#1F2933]">
                  <td className="px-4 py-2.5 text-[#8A97A3]">{m.label}</td>
                  {rows.map((r) => (
                    <td key={r.ticker} className={`text-right px-4 py-2.5 ${m.tone ? m.tone(r) : ''}`}>{m.get(r)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {aiText && (
        <section className="border border-[#1F2933] p-4">
          <h2 className="text-sm text-[#8A97A3] mb-3 font-[family-name:var(--font-mono)]">AI Karşılaştırması</h2>
          <p className="text-[#E8E6E1] leading-relaxed max-w-[70ch]">{aiText}</p>
        </section>
      )}
    </div>
  );
}
