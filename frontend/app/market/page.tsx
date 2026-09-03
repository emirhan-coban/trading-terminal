import { supabase } from '@/lib/supabase';
import { scoreColor, stripIS } from '@/lib/utils';
import ConfigWarning from '@/components/ConfigWarning';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

async function getMarketData() {
  const { data: scores } = await supabase
    .from('scores')
    .select('ticker,technical_score,calculated_at')
    .eq('horizon', 'short')
    .order('calculated_at', { ascending: false })
    .limit(300);

  const latestByTicker = new Map<string, { ticker: string; technical_score: number }>();
  if (scores) {
    for (const row of scores) {
      if (!latestByTicker.has(row.ticker)) {
        latestByTicker.set(row.ticker, row);
      }
    }
  }

  const allScores = Array.from(latestByTicker.values())
    .filter((s) => s.technical_score != null)
    .sort((a, b) => b.technical_score - a.technical_score);

  const topGainers = allScores.slice(0, 10);
  // Hisse sayısı 20'den azsa dilimler çakışır — kaybedenlerden
  // kazananlarda olanları çıkar ki aynı hisse iki listede çıkmasın.
  const gainerTickers = new Set(topGainers.map((s) => s.ticker));
  const topLosers = allScores
    .filter((s) => !gainerTickers.has(s.ticker))
    .slice(-10)
    .reverse();

  const { data: watchlist } = await supabase
    .from('watchlist')
    .select('ticker,display_name');

  const watchlistSet = new Set((watchlist ?? []).map((w) => w.ticker));

  return { topGainers, topLosers, watchlistSet, totalStocks: allScores.length };
}

function ScoreBar({ score }: { score: number }) {
  const width = Math.abs(score);
  const color = score >= 0 ? '#3DDC84' : '#FF5C5C';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-1.5 bg-[#1F2933] rounded overflow-hidden">
        <div
          className="h-full rounded"
          style={{ width: `${width}%`, backgroundColor: color }}
        />
      </div>
      <span className={`text-xs font-semibold ${scoreColor(score)}`}>
        {score > 0 ? '+' : ''}{score.toFixed(1)}
      </span>
    </div>
  );
}

export default async function MarketPage() {
  const { topGainers, topLosers, totalStocks } = await getMarketData();

  return (
    <div className="p-4 md:p-6">
      <ConfigWarning />
      <h1 className="text-lg text-[#8A97A3] font-[family-name:var(--font-mono)] mb-6">
        Piyasa Geneli
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="border border-[#1F2933] p-4">
          <div className="text-xs text-[#8A97A3] font-[family-name:var(--font-mono)] mb-1">Analiz Edilen</div>
          <div className="text-2xl font-[family-name:var(--font-mono)] font-semibold">{totalStocks}</div>
          <div className="text-xs text-[#8A97A3]">hisse</div>
        </div>
        <div className="border border-[#1F2933] p-4">
          <div className="text-xs text-[#8A97A3] font-[family-name:var(--font-mono)] mb-1">Güçlü Sinyal</div>
          <div className="text-2xl font-[family-name:var(--font-mono)] font-semibold text-[#3DDC84]">
            {topGainers.filter((s) => s.technical_score > 50).length}
          </div>
          <div className="text-xs text-[#8A97A3]">hisse (skor &gt; 50)</div>
        </div>
        <div className="border border-[#1F2933] p-4">
          <div className="text-xs text-[#8A97A3] font-[family-name:var(--font-mono)] mb-1">Zayıf Sinyal</div>
          <div className="text-2xl font-[family-name:var(--font-mono)] font-semibold text-[#FF5C5C]">
            {topLosers.filter((s) => s.technical_score < -50).length}
          </div>
          <div className="text-xs text-[#8A97A3]">hisse (skor &lt; -50)</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <section>
          <h2 className="text-sm text-[#3DDC84] font-[family-name:var(--font-mono)] mb-3 flex items-center gap-2">
            <span>▲</span> En Güçlü Sinyaller
          </h2>
          <div className="border border-[#1F2933] divide-y divide-[#1F2933]">
            {topGainers.map((item) => (
              <Link
                key={item.ticker}
                href={`/stock/${item.ticker}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-[#12181F] transition"
              >
                <div>
                  <div className="font-[family-name:var(--font-mono)] font-medium text-sm">
                    {stripIS(item.ticker)}
                  </div>
                </div>
                <ScoreBar score={item.technical_score} />
              </Link>
            ))}
            {topGainers.length === 0 && (
              <div className="px-4 py-6 text-center text-[#8A97A3] text-sm">
                Henüz veri yok
              </div>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-sm text-[#FF5C5C] font-[family-name:var(--font-mono)] mb-3 flex items-center gap-2">
            <span>▼</span> En Zayıf Sinyaller
          </h2>
          <div className="border border-[#1F2933] divide-y divide-[#1F2933]">
            {topLosers.map((item) => (
              <Link
                key={item.ticker}
                href={`/stock/${item.ticker}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-[#12181F] transition"
              >
                <div>
                  <div className="font-[family-name:var(--font-mono)] font-medium text-sm">
                    {stripIS(item.ticker)}
                  </div>
                </div>
                <ScoreBar score={item.technical_score} />
              </Link>
            ))}
            {topLosers.length === 0 && (
              <div className="px-4 py-6 text-center text-[#8A97A3] text-sm">
                Henüz veri yok
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
