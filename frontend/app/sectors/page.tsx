import { supabase } from '@/lib/supabase';
import { scoreColor } from '@/lib/utils';
import ConfigWarning from '@/components/ConfigWarning';

export const dynamic = 'force-dynamic';

async function getSectorData() {
  const { data: scores } = await supabase
    .from('scores')
    .select('ticker,technical_score')
    .eq('horizon', 'short')
    .order('calculated_at', { ascending: false })
    .limit(500);

  const latestByTicker = new Map<string, number>();
  if (scores) {
    for (const row of scores) {
      if (!latestByTicker.has(row.ticker) && row.technical_score != null) {
        latestByTicker.set(row.ticker, row.technical_score);
      }
    }
  }

  const { data: financials } = await supabase
    .from('financials')
    .select('ticker,raw_data')
    .limit(500);

  const sectorMap = new Map<string, { scores: number[]; count: number }>();
  if (financials) {
    for (const f of financials) {
      try {
        const raw = JSON.parse(f.raw_data || '{}');
        const sector = raw.sector || 'Diğer';
        if (!sectorMap.has(sector)) sectorMap.set(sector, { scores: [], count: 0 });
        const info = sectorMap.get(sector)!;
        info.count++;
        const score = latestByTicker.get(f.ticker);
        if (score != null) info.scores.push(score);
      } catch {
        continue;
      }
    }
  }

  const sectors = Array.from(sectorMap.entries()).map(([name, data]) => ({
    name,
    count: data.count,
    avgScore: data.scores.length > 0
      ? data.scores.reduce((a, b) => a + b, 0) / data.scores.length
      : null,
    analyzedCount: data.scores.length,
  }));

  return sectors.sort((a, b) => (b.avgScore ?? -999) - (a.avgScore ?? -999));
}

export default async function SectorsPage() {
  const sectors = await getSectorData();

  return (
    <div className="p-4 md:p-6">
      <ConfigWarning />
      <h1 className="text-lg text-[#8A97A3] font-[family-name:var(--font-mono)] mb-6">
        Sektörel Performans
      </h1>

      <div className="border border-[#1F2933] overflow-x-auto">
        <table className="w-full text-sm font-[family-name:var(--font-mono)]">
          <thead>
            <tr className="border-b border-[#1F2933] text-[#8A97A3] text-xs">
              <th className="text-left px-4 py-2.5 font-medium">Sektör</th>
              <th className="text-right px-4 py-2.5 font-medium">Hisse Sayısı</th>
              <th className="text-right px-4 py-2.5 font-medium">Analiz Edilen</th>
              <th className="text-right px-4 py-2.5 font-medium">Ortalama Skor</th>
              <th className="text-left px-4 py-2.5 font-medium w-48">Skor Grafiği</th>
            </tr>
          </thead>
          <tbody>
            {sectors.map((sector) => (
              <tr
                key={sector.name}
                className="border-b border-[#1F2933] hover:bg-[#12181F] transition"
              >
                <td className="px-4 py-3 font-medium">{sector.name}</td>
                <td className="text-right px-4 py-3 text-[#8A97A3]">{sector.count}</td>
                <td className="text-right px-4 py-3 text-[#8A97A3]">{sector.analyzedCount}</td>
                <td className="text-right px-4 py-3">
                  {sector.avgScore != null ? (
                    <span className={`font-semibold ${scoreColor(sector.avgScore)}`}>
                      {sector.avgScore > 0 ? '+' : ''}{sector.avgScore.toFixed(1)}
                    </span>
                  ) : (
                    <span className="text-[#8A97A3]">—</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {sector.avgScore != null && (
                    <div className="w-full h-2 bg-[#1F2933] rounded overflow-hidden">
                      <div
                        className="h-full rounded transition-all"
                        style={{
                          width: `${Math.min(100, Math.abs(sector.avgScore))}%`,
                          backgroundColor: sector.avgScore >= 0 ? '#3DDC84' : '#FF5C5C',
                        }}
                      />
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
