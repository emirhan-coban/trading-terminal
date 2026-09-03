import { supabase } from '@/lib/supabase';
import { scoreColor, stripIS, fmt } from '@/lib/utils';
import ConfigWarning from '@/components/ConfigWarning';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

type WatchlistRow = {
  ticker: string;
  display_name: string | null;
};

type ScoreRow = {
  ticker: string;
  technical_score: number | null;
  reasoning: string | null;
  calculated_at: string;
  indicators: string | null;
};

type PriceRow = {
  ticker: string;
  close: number;
  volume: number;
  date: string;
};

async function getWatchlistData() {
  const { data: watchlist } = await supabase
    .from('watchlist')
    .select('ticker,display_name')
    .returns<WatchlistRow[]>();

  const { data: scores } = await supabase
    .from('scores')
    .select('ticker,technical_score,reasoning,calculated_at,indicators')
    .eq('horizon', 'short')
    .order('calculated_at', { ascending: false })
    .returns<ScoreRow[]>();

  const latestScoreByTicker = new Map<string, ScoreRow>();
  for (const row of scores ?? []) {
    if (!latestScoreByTicker.has(row.ticker)) {
      latestScoreByTicker.set(row.ticker, row);
    }
  }

  // Watchlist tablosunda aynı ticker birden fazla kez olabilir —
  // React key çakışmasını önlemek için ticker bazında tekilleştir.
  const seen = new Set<string>();
  const uniqueWatchlist = (watchlist ?? []).filter((w) => {
    if (seen.has(w.ticker)) return false;
    seen.add(w.ticker);
    return true;
  });

  const tickers = uniqueWatchlist.map((w) => w.ticker);
  const priceMap = new Map<string, { close: number; prev_close: number; volume: number }>();

  if (tickers.length > 0) {
    const { data: prices } = await supabase
      .from('price_history')
      .select('ticker,close,volume,date')
      .in('ticker', tickers)
      .order('date', { ascending: false })
      .limit(tickers.length * 2);

    if (prices) {
      const byTicker = new Map<string, PriceRow[]>();
      for (const p of prices) {
        if (!byTicker.has(p.ticker)) byTicker.set(p.ticker, []);
        byTicker.get(p.ticker)!.push(p as PriceRow);
      }
      for (const [ticker, pRows] of byTicker) {
        if (pRows.length >= 2) {
          priceMap.set(ticker, {
            close: pRows[0].close,
            prev_close: pRows[1].close,
            volume: pRows[0].volume,
          });
        } else if (pRows.length === 1) {
          priceMap.set(ticker, { close: pRows[0].close, prev_close: pRows[0].close, volume: pRows[0].volume });
        }
      }
    }
  }

  return uniqueWatchlist.map((w) => {
    const score = latestScoreByTicker.get(w.ticker);
    const price = priceMap.get(w.ticker);
    const change_pct = price && price.prev_close
      ? ((price.close - price.prev_close) / price.prev_close) * 100
      : null;

    return {
      ...w,
      score: score ?? null,
      price: price?.close ?? null,
      change_pct,
      volume: price?.volume ?? null,
    };
  });
}

export default async function Home() {
  const items = await getWatchlistData();

  return (
    <div className="p-4 md:p-6">
      <ConfigWarning />
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg text-[#8A97A3] font-[family-name:var(--font-mono)]">
          İzleme Listesi
        </h1>
        <div className="text-xs text-[#8A97A3] font-[family-name:var(--font-mono)]">
          {items.length} hisse
        </div>
      </div>

      {items.length === 0 && (
        <div className="text-center py-16 text-[#8A97A3]">
          <p className="text-lg mb-2">Watchlist boş</p>
          <p className="text-sm">
            <Link href="/search" className="text-[#3DDC84] hover:underline">Hisse ara</Link>
            {' '}ile hisse ekleyin veya backend API&apos;sinden ekleyin.
          </p>
        </div>
      )}

      {items.length > 0 && (
        <div className="border border-[#1F2933] overflow-x-auto">
          <table className="w-full text-sm font-[family-name:var(--font-mono)]">
            <thead>
              <tr className="border-b border-[#1F2933] text-[#8A97A3] text-xs">
                <th className="text-left px-4 py-2.5 font-medium">Hisse</th>
                <th className="text-right px-4 py-2.5 font-medium">Son</th>
                <th className="text-right px-4 py-2.5 font-medium">Değişim %</th>
                <th className="text-right px-4 py-2.5 font-medium">Hacim</th>
                <th className="text-right px-4 py-2.5 font-medium">Skor</th>
                <th className="text-left px-4 py-2.5 font-medium hidden md:table-cell">Analiz</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const changePositive = (item.change_pct ?? 0) >= 0;
                return (
                  <tr
                    key={item.ticker}
                    className="border-b border-[#1F2933] hover:bg-[#12181F] transition cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <Link href={`/stock/${item.ticker}`} className="block">
                        <div className="font-medium text-[#E8E6E1]">{stripIS(item.ticker)}</div>
                        <div className="text-xs text-[#8A97A3] mt-0.5">{item.display_name}</div>
                      </Link>
                    </td>
                    <td className="text-right px-4 py-3">
                      <Link href={`/stock/${item.ticker}`} className="block">
                        {fmt(item.price)}
                      </Link>
                    </td>
                    <td className="text-right px-4 py-3">
                      <Link href={`/stock/${item.ticker}`} className="block">
                        <span className={changePositive ? 'text-[#3DDC84]' : 'text-[#FF5C5C]'}>
                          {item.change_pct != null ? `${changePositive ? '+' : ''}${item.change_pct.toFixed(2)}%` : '—'}
                        </span>
                      </Link>
                    </td>
                    <td className="text-right px-4 py-3 text-[#8A97A3]">
                      <Link href={`/stock/${item.ticker}`} className="block">
                        {item.volume != null ? item.volume.toLocaleString('tr-TR') : '—'}
                      </Link>
                    </td>
                    <td className="text-right px-4 py-3">
                      <Link href={`/stock/${item.ticker}`} className="block">
                        <span className={`font-semibold ${scoreColor(item.score?.technical_score)}`}>
                          {item.score?.technical_score ?? '—'}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <Link href={`/stock/${item.ticker}`} className="block">
                        {item.score?.reasoning && (
                          <p className="text-xs text-[#8A97A3] line-clamp-1 max-w-[40ch]">
                            {item.score.reasoning}
                          </p>
                        )}
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
