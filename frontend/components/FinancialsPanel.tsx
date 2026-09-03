import { fmt } from '@/lib/utils';

type FinancialsData = {
  pe_ratio: number | null;
  pb_ratio: number | null;
  debt_to_equity: number | null;
  revenue_growth: number | null;
  dividend_yield: number | null;
  market_cap: number | null;
  period: string | null;
};

type Props = {
  financials: FinancialsData | null;
  rawMeta: Record<string, unknown>;
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1.5">
      <dt className="text-[#8A97A3]">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export default function FinancialsPanel({ financials, rawMeta }: Props) {
  const f52High = rawMeta.fifty_two_week_high as number | undefined;
  const f52Low = rawMeta.fifty_two_week_low as number | undefined;
  const trailingEps = rawMeta.trailing_eps as number | undefined;

  return (
    <section className="border border-[#1F2933] p-4">
      <h2 className="text-sm text-[#8A97A3] mb-3 font-[family-name:var(--font-mono)]">
        Fundamental — {financials?.period ?? '—'}
      </h2>
      <dl className="font-[family-name:var(--font-mono)] text-sm divide-y divide-[#1F2933]">
        <Row label="F/K (P/E)" value={fmt(financials?.pe_ratio)} />
        <Row label="PD/DD (P/B)" value={fmt(financials?.pb_ratio)} />
        <Row label="Borç/Özsermaye" value={fmt(financials?.debt_to_equity)} />
        <Row
          label="Gelir Büyümesi"
          value={financials?.revenue_growth != null ? `%${(financials.revenue_growth * 100).toFixed(1)}` : '—'}
        />
        <Row
          label="Temettü Verimi"
          value={financials?.dividend_yield != null ? `%${(financials.dividend_yield * 100).toFixed(2)}` : '—'}
        />
        <Row
          label="Piyasa Değeri"
          value={financials?.market_cap != null ? `${(financials.market_cap / 1e9).toFixed(1)}M ₺` : '—'}
        />
        {f52High != null && <Row label="52 Hafta Yüksek" value={fmt(f52High)} />}
        {f52Low != null && <Row label="52 Hafta Düşük" value={fmt(f52Low)} />}
        {trailingEps != null && <Row label="KPS (Trailing)" value={fmt(trailingEps)} />}
      </dl>
    </section>
  );
}
