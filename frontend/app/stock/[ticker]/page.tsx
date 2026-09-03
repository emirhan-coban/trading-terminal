import { supabase } from '@/lib/supabase';
import { scoreColor, fmt, stripIS } from '@/lib/utils';
import Link from 'next/link';
import PriceChart from '@/components/PriceChart';
import TradingViewWidget from '@/components/TradingViewWidget';
import IndicatorsPanel from '@/components/IndicatorsPanel';
import FinancialsPanel from '@/components/FinancialsPanel';
import BacktestPanel from '@/components/BacktestPanel';
import NewsPanel from '@/components/NewsPanel';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const dynamic = 'force-dynamic';

async function getPriceHistory(ticker: string) {
  const { data } = await supabase
    .from('price_history')
    .select('date,open,high,low,close,volume')
    .eq('ticker', ticker)
    .order('date', { ascending: true });

  return (data ?? []).map((row) => ({
    time: row.date,
    open: row.open,
    high: row.high,
    low: row.low,
    close: row.close,
    volume: row.volume,
  }));
}

async function getStockData(ticker: string) {
  const { data: watchlistRow } = await supabase
    .from('watchlist')
    .select('ticker,display_name')
    .eq('ticker', ticker)
    .single();

  const { data: scoreRow } = await supabase
    .from('scores')
    .select('technical_score,indicators,reasoning,calculated_at')
    .eq('ticker', ticker)
    .eq('horizon', 'short')
    .order('calculated_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  const { data: financialsRow } = await supabase
    .from('financials')
    .select('pe_ratio,pb_ratio,debt_to_equity,revenue_growth,dividend_yield,market_cap,period,raw_data')
    .eq('ticker', ticker)
    .order('period', { ascending: false })
    .limit(1)
    .maybeSingle();

  return { watchlistRow, scoreRow, financialsRow };
}

function isBist(ticker: string) {
  return ticker.endsWith('.IS');
}

export default async function StockDetail({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const { watchlistRow, scoreRow, financialsRow } = await getStockData(ticker);
  const bist = isBist(ticker);
  const priceHistory = bist ? await getPriceHistory(ticker) : [];
  const indicators = (scoreRow?.indicators as Record<string, number | null>) ?? null;

  const priceChange = priceHistory.length >= 2
    ? ((priceHistory[priceHistory.length - 1].close - priceHistory[priceHistory.length - 2].close) / priceHistory[priceHistory.length - 2].close) * 100
    : null;

  const rawMeta = financialsRow?.raw_data ? JSON.parse(financialsRow.raw_data) : {};

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto">
      <Link href="/" className="text-sm text-[#8A97A3] hover:text-[#E8E6E1]">
        ← İzleme Listesi
      </Link>

      <div className="flex items-baseline justify-between mt-3 mb-4">
        <div>
          <h1 className="text-2xl font-[family-name:var(--font-mono)] font-semibold">
            {stripIS(ticker)}
          </h1>
          <p className="text-[#8A97A3] text-sm">{watchlistRow?.display_name}</p>
          {rawMeta.sector && (
            <p className="text-xs text-[#8A97A3] mt-1">{rawMeta.sector} — {rawMeta.industry}</p>
          )}
        </div>
        <div className="text-right">
          <div className={`text-3xl font-[family-name:var(--font-mono)] font-semibold ${scoreColor(scoreRow?.technical_score)}`}>
            {fmt(scoreRow?.technical_score, 1)}
          </div>
          {priceChange != null && (
            <div className={`text-sm font-[family-name:var(--font-mono)] ${priceChange >= 0 ? 'text-[#3DDC84]' : 'text-[#FF5C5C]'}`}>
              {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
            </div>
          )}
        </div>
      </div>

      <div className="mb-4">
        {bist ? <PriceChart data={priceHistory} /> : <TradingViewWidget symbol={ticker} />}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <IndicatorsPanel indicators={indicators} />
        <FinancialsPanel financials={financialsRow} rawMeta={rawMeta} />
      </div>

      {scoreRow?.reasoning && (
        <section className="border border-[#1F2933] p-4">
          <h2 className="text-sm text-[#8A97A3] mb-3 font-[family-name:var(--font-mono)]">Analist Değerlendirmesi</h2>
          <p className="text-[#E8E6E1] leading-relaxed max-w-[70ch]">
            {scoreRow.reasoning}
          </p>
          <p className="text-xs text-[#8A97A3] mt-3">
            Bu bir yatırım tavsiyesi değildir — göstergelerin gözlemsel bir özetidir.
          </p>
        </section>
      )}

      {bist && <BacktestPanel ticker={ticker} />}

      <NewsPanel ticker={ticker} />

      {bist && (
        <div className="mt-4">
          <a
            href={`${API_BASE}/export/${encodeURIComponent(ticker)}`}
            className="inline-block text-xs font-[family-name:var(--font-mono)] border border-[#1F2933] px-3 py-2 rounded text-[#8A97A3] hover:text-[#E8E6E1] hover:border-[#3DDC84] transition"
          >
            Fiyat geçmişini CSV indir ↓
          </a>
        </div>
      )}
    </div>
  );
}
