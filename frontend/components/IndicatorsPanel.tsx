import { fmt } from '@/lib/utils';

type Props = {
  indicators: Record<string, number | null> | null;
};

function Row({ label, value, highlight }: { label: string; value: string; highlight?: 'bullish' | 'bearish' }) {
  const color = highlight === 'bullish' ? 'text-[#3DDC84]' : highlight === 'bearish' ? 'text-[#FF5C5C]' : '';
  return (
    <div className="flex justify-between py-1.5">
      <dt className="text-[#8A97A3]">{label}</dt>
      <dd className={color}>{value}</dd>
    </div>
  );
}

export default function IndicatorsPanel({ indicators }: Props) {
  if (!indicators) {
    return (
      <section className="border border-[#1F2933] p-4">
        <h2 className="text-sm text-[#8A97A3] mb-3 font-[family-name:var(--font-mono)]">Teknik Göstergeler</h2>
        <p className="text-sm text-[#8A97A3]">Henüz veri yok.</p>
      </section>
    );
  }

  const rsiHighlight = indicators.rsi != null ? (indicators.rsi > 70 ? 'bearish' : indicators.rsi < 30 ? 'bullish' : undefined) : undefined;
  const adxHighlight = indicators.adx != null ? (indicators.adx > 25 ? 'bullish' : undefined) : undefined;

  return (
    <section className="border border-[#1F2933] p-4">
      <h2 className="text-sm text-[#8A97A3] mb-3 font-[family-name:var(--font-mono)]">Teknik Göstergeler</h2>
      <dl className="font-[family-name:var(--font-mono)] text-sm divide-y divide-[#1F2933]">
        <Row label="RSI (14)" value={fmt(indicators.rsi)} highlight={rsiHighlight} />
        <Row label="MACD" value={fmt(indicators.macd, 4)} />
        <Row label="MACD Sinyal" value={fmt(indicators.macd_signal, 4)} />
        <Row label="MACD Hist" value={fmt(indicators.macd_hist, 4)} highlight={indicators.macd_hist != null ? (indicators.macd_hist > 0 ? 'bullish' : 'bearish') : undefined} />
        <Row label="SMA 20" value={fmt(indicators.sma20)} />
        <Row label="SMA 50" value={fmt(indicators.sma50)} />
        <Row label="SMA 200" value={fmt(indicators.sma200)} />
        <Row label="EMA 20" value={fmt(indicators.ema20)} />
        <Row label="EMA 50" value={fmt(indicators.ema50)} />
        <Row label="ATR (14)" value={fmt(indicators.atr)} />
        <Row label="BB Üst" value={fmt(indicators.bb_upper)} />
        <Row label="BB Orta" value={fmt(indicators.bb_middle)} />
        <Row label="BB Alt" value={fmt(indicators.bb_lower)} />
        <Row label="BB Genişlik" value={fmt(indicators.bb_width, 4)} />
        <Row label="Stoch %K" value={fmt(indicators.stoch_k)} />
        <Row label="Stoch %D" value={fmt(indicators.stoch_d)} />
        <Row label="ADX" value={fmt(indicators.adx)} highlight={adxHighlight} />
        <Row label="CCI" value={fmt(indicators.cci)} highlight={indicators.cci != null ? (indicators.cci > 100 ? 'bullish' : indicators.cci < -100 ? 'bearish' : undefined) : undefined} />
        <Row label="Williams %R" value={fmt(indicators.williams_r)} highlight={indicators.williams_r != null ? (indicators.williams_r > -20 ? 'bearish' : indicators.williams_r < -80 ? 'bullish' : undefined) : undefined} />
        <Row label="OBV" value={indicators.obv != null ? indicators.obv.toLocaleString('tr-TR') : '—'} />
        <Row label="VWAP" value={fmt(indicators.vwap)} />
      </dl>
    </section>
  );
}
