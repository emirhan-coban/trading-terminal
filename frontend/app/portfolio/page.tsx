'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiPortfolioSummary, apiPortfolioAdd, apiPortfolioRemove } from '@/lib/api';
import { stripIS, fmt } from '@/lib/utils';

type Position = {
  ticker: string;
  quantity: number;
  avg_cost: number;
  last_price: number | null;
  cost: number;
  market_value: number | null;
  pnl: number | null;
  pnl_pct: number | null;
};

type Summary = {
  positions: Position[];
  total_cost: number;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
};

export default function PortfolioPage() {
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [ticker, setTicker] = useState('');
  const [qty, setQty] = useState('');
  const [price, setPrice] = useState('');

  const load = async () => {
    try {
      setError('');
      setData(await apiPortfolioSummary());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    apiPortfolioSummary()
      .then((d) => {
        if (!active) return;
        setData(d);
        setLoading(false);
      })
      .catch((e) => {
        if (!active) return;
        setError(e instanceof Error ? e.message : 'Yüklenemedi');
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiPortfolioAdd(ticker, parseFloat(qty), parseFloat(price));
      setTicker(''); setQty(''); setPrice('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Eklenemedi');
    }
  };

  const remove = async (t: string) => {
    if (!confirm(`${t} pozisyonu kapatılsın mı?`)) return;
    try {
      await apiPortfolioRemove(t);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Silinemedi');
    }
  };

  const pnlPositive = (data?.total_pnl ?? 0) >= 0;

  return (
    <div className="p-4 md:p-6">
      <h1 className="text-lg text-[#8A97A3] font-[family-name:var(--font-mono)] mb-6">Portföy</h1>

      {error && <div className="border border-[#FF5C5C] text-[#FF5C5C] text-sm p-3 mb-4">{error}</div>}

      {loading ? (
        <div className="text-[#8A97A3] text-sm">Yükleniyor...</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Stat label="Maliyet" value={`${fmt(data?.total_cost)} ₺`} />
            <Stat label="Piyasa Değeri" value={`${fmt(data?.total_value)} ₺`} />
            <Stat label="Kâr/Zarar" value={`${data && data.total_pnl >= 0 ? '+' : ''}${fmt(data?.total_pnl)} ₺`} tone={pnlPositive ? 'up' : 'down'} />
            <Stat label="Getiri %" value={`%${fmt(data?.total_pnl_pct)}`} tone={pnlPositive ? 'up' : 'down'} />
          </div>

          <form onSubmit={add} className="flex flex-wrap gap-2 mb-6">
            <input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="Hisse (THYAO)"
              className="bg-[#161D27] border border-[#1F2933] rounded px-3 py-2 text-sm font-[family-name:var(--font-mono)] w-36 focus:outline-none focus:border-[#3DDC84]" />
            <input value={qty} onChange={(e) => setQty(e.target.value)} placeholder="Adet" type="number" step="any" min="0"
              className="bg-[#161D27] border border-[#1F2933] rounded px-3 py-2 text-sm font-[family-name:var(--font-mono)] w-28 focus:outline-none focus:border-[#3DDC84]" />
            <input value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Maliyet ₺" type="number" step="any" min="0"
              className="bg-[#161D27] border border-[#1F2933] rounded px-3 py-2 text-sm font-[family-name:var(--font-mono)] w-32 focus:outline-none focus:border-[#3DDC84]" />
            <button type="submit" className="bg-[#3DDC84] text-black text-sm font-semibold px-4 py-2 rounded hover:opacity-90">
              Ekle
            </button>
          </form>

          {(data?.positions.length ?? 0) === 0 ? (
            <p className="text-[#8A97A3] text-sm">Henüz pozisyon yok. Yukarıdan ekleyin.</p>
          ) : (
            <div className="border border-[#1F2933] overflow-x-auto">
              <table className="w-full text-sm font-[family-name:var(--font-mono)]">
                <thead>
                  <tr className="border-b border-[#1F2933] text-[#8A97A3] text-xs">
                    <th className="text-left px-4 py-2.5 font-medium">Hisse</th>
                    <th className="text-right px-4 py-2.5 font-medium">Adet</th>
                    <th className="text-right px-4 py-2.5 font-medium">Maliyet</th>
                    <th className="text-right px-4 py-2.5 font-medium">Son</th>
                    <th className="text-right px-4 py-2.5 font-medium">Değer</th>
                    <th className="text-right px-4 py-2.5 font-medium">K/Z</th>
                    <th className="px-4 py-2.5"></th>
                  </tr>
                </thead>
                <tbody>
                  {data!.positions.map((p) => (
                    <tr key={p.ticker} className="border-b border-[#1F2933] hover:bg-[#12181F]">
                      <td className="px-4 py-3">
                        <Link href={`/stock/${p.ticker}`} className="hover:text-[#3DDC84]">{stripIS(p.ticker)}</Link>
                      </td>
                      <td className="text-right px-4 py-3">{p.quantity}</td>
                      <td className="text-right px-4 py-3">{fmt(p.avg_cost)}</td>
                      <td className="text-right px-4 py-3">{p.last_price != null ? fmt(p.last_price) : '—'}</td>
                      <td className="text-right px-4 py-3">{p.market_value != null ? fmt(p.market_value) : '—'}</td>
                      <td className={`text-right px-4 py-3 ${(p.pnl ?? 0) >= 0 ? 'text-[#3DDC84]' : 'text-[#FF5C5C]'}`}>
                        {p.pnl != null ? `${p.pnl >= 0 ? '+' : ''}${fmt(p.pnl)} (%${fmt(p.pnl_pct)})` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => remove(p.ticker)} className="text-[#8A97A3] hover:text-[#FF5C5C] text-xs">Kapat ✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: 'up' | 'down' }) {
  const color = tone === 'up' ? 'text-[#3DDC84]' : tone === 'down' ? 'text-[#FF5C5C]' : 'text-[#E8E6E1]';
  return (
    <div className="border border-[#1F2933] p-4">
      <div className="text-xs text-[#8A97A3] font-[family-name:var(--font-mono)] mb-1">{label}</div>
      <div className={`text-lg font-[family-name:var(--font-mono)] font-semibold ${color}`}>{value}</div>
    </div>
  );
}
