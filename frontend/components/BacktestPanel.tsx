import { fmt } from '@/lib/utils';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getBacktest(ticker: string) {
  try {
    const res = await fetch(`${API}/backtest/${encodeURIComponent(ticker)}?strategy=ma_cross`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function BacktestPanel({ ticker }: { ticker: string }) {
  const bt = await getBacktest(ticker);
  if (!bt) return null;

  const stratPositive = (bt.strategy_return_pct ?? 0) >= 0;

  return (
    <section className="border border-[#1F2933] p-4 mt-4">
      <h2 className="text-sm text-[#8A97A3] mb-3 font-[family-name:var(--font-mono)]">
        Backtest — MA Kesişimi ({bt.params?.fast}/{bt.params?.slow}) · {bt.period?.start} → {bt.period?.end}
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-[family-name:var(--font-mono)] text-sm">
        <div>
          <div className="text-xs text-[#8A97A3]">Strateji getirisi</div>
          <div className={`text-lg font-semibold ${stratPositive ? 'text-[#3DDC84]' : 'text-[#FF5C5C]'}`}>
            %{bt.strategy_return_pct}
          </div>
        </div>
        <div>
          <div className="text-xs text-[#8A97A3]">Al-tut getirisi</div>
          <div className="text-lg font-semibold">%{bt.buy_hold_return_pct}</div>
        </div>
        <div>
          <div className="text-xs text-[#8A97A3]">İşlem sayısı</div>
          <div className="text-lg font-semibold">{bt.trades_count}</div>
        </div>
        <div>
          <div className="text-xs text-[#8A97A3]">Son değer (100K ₺)</div>
          <div className="text-lg font-semibold">{fmt(bt.final_value)} ₺</div>
        </div>
      </div>
      <p className="text-xs text-[#8A97A3] mt-3">{bt.note}</p>
    </section>
  );
}
