'use client';

import { useEffect, useState } from 'react';
import { apiAlerts, apiAlertCreate, apiAlertDelete, apiAlertsCheck } from '@/lib/api';
import { stripIS } from '@/lib/utils';

type Alert = {
  id: number;
  ticker: string;
  condition: string;
  target_value: number;
  is_active: boolean;
  last_value: number | null;
  triggered_at: string | null;
  created_at: string;
};

const CONDITION_LABELS: Record<string, string> = {
  price_above: 'Fiyat üstüne çıkarsa',
  price_below: 'Fiyat altına inerse',
  rsi_above: 'RSI üstüne çıkarsa',
  rsi_below: 'RSI altına inerse',
  score_above: 'Skor üstüne çıkarsa',
  score_below: 'Skor altına inerse',
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState('');
  const [ticker, setTicker] = useState('');
  const [condition, setCondition] = useState('price_above');
  const [target, setTarget] = useState('');

  const load = async () => {
    try {
      setError('');
      const data = await apiAlerts();
      setAlerts(data.alerts || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    apiAlerts()
      .then((data) => {
        if (!active) return;
        setAlerts(data.alerts || []);
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

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiAlertCreate(ticker, condition, parseFloat(target));
      setTicker(''); setTarget('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Oluşturulamadı');
    }
  };

  const remove = async (id: number) => {
    try {
      await apiAlertDelete(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Silinemedi');
    }
  };

  const checkNow = async () => {
    setChecking(true);
    try {
      const res = await apiAlertsCheck();
      setCheckResult(`${res.checked} alarm kontrol edildi, ${res.triggered_count} tetiklendi.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kontrol başarısız');
    } finally {
      setChecking(false);
    }
  };

  const active = alerts.filter((a) => a.is_active);
  const history = alerts.filter((a) => !a.is_active);

  return (
    <div className="p-4 md:p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg text-[#8A97A3] font-[family-name:var(--font-mono)]">Alarmlar</h1>
        <button onClick={checkNow} disabled={checking}
          className="text-xs font-[family-name:var(--font-mono)] border border-[#1F2933] px-3 py-1.5 rounded text-[#8A97A3] hover:text-[#E8E6E1] hover:border-[#3DDC84] disabled:opacity-50">
          {checking ? 'Kontrol ediliyor...' : 'Şimdi kontrol et'}
        </button>
      </div>

      {error && <div className="border border-[#FF5C5C] text-[#FF5C5C] text-sm p-3 mb-4">{error}</div>}
      {checkResult && <div className="border border-[#3DDC84] text-[#3DDC84] text-sm p-3 mb-4">{checkResult}</div>}

      <form onSubmit={create} className="flex flex-wrap gap-2 mb-8">
        <input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="Hisse (THYAO)"
          className="bg-[#161D27] border border-[#1F2933] rounded px-3 py-2 text-sm font-[family-name:var(--font-mono)] w-36 focus:outline-none focus:border-[#3DDC84]" />
        <select value={condition} onChange={(e) => setCondition(e.target.value)}
          className="bg-[#161D27] border border-[#1F2933] rounded px-3 py-2 text-sm font-[family-name:var(--font-mono)] focus:outline-none focus:border-[#3DDC84]">
          {Object.entries(CONDITION_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
        <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Hedef değer" type="number" step="any"
          className="bg-[#161D27] border border-[#1F2933] rounded px-3 py-2 text-sm font-[family-name:var(--font-mono)] w-32 focus:outline-none focus:border-[#3DDC84]" />
        <button type="submit" className="bg-[#3DDC84] text-black text-sm font-semibold px-4 py-2 rounded hover:opacity-90">
          Alarm kur
        </button>
      </form>

      {loading ? (
        <div className="text-[#8A97A3] text-sm">Yükleniyor...</div>
      ) : (
        <>
          <h2 className="text-sm text-[#8A97A3] font-[family-name:var(--font-mono)] mb-3">Aktif ({active.length})</h2>
          <div className="border border-[#1F2933] divide-y divide-[#1F2933] mb-6">
            {active.length === 0 && <div className="p-4 text-sm text-[#8A97A3]">Aktif alarm yok.</div>}
            {active.map((a) => (
              <div key={a.id} className="flex items-center justify-between p-3 text-sm font-[family-name:var(--font-mono)]">
                <span><span className="text-[#E8E6E1]">{stripIS(a.ticker)}</span>{' '}
                  <span className="text-[#8A97A3]">{CONDITION_LABELS[a.condition]} {a.target_value}</span></span>
                <button onClick={() => remove(a.id)} className="text-[#8A97A3] hover:text-[#FF5C5C] text-xs">Sil ✕</button>
              </div>
            ))}
          </div>

          <h2 className="text-sm text-[#8A97A3] font-[family-name:var(--font-mono)] mb-3">Tetiklenenler ({history.length})</h2>
          <div className="border border-[#1F2933] divide-y divide-[#1F2933]">
            {history.length === 0 && <div className="p-4 text-sm text-[#8A97A3]">Henüz tetiklenen yok.</div>}
            {history.map((a) => (
              <div key={a.id} className="flex items-center justify-between p-3 text-sm font-[family-name:var(--font-mono)]">
                <span><span className="text-[#3DDC84]">●</span>{' '}
                  <span className="text-[#E8E6E1]">{stripIS(a.ticker)}</span>{' '}
                  <span className="text-[#8A97A3]">{CONDITION_LABELS[a.condition]} {a.target_value}
                    {a.last_value != null && ` (gerçekleşen: ${a.last_value})`}</span></span>
                <button onClick={() => remove(a.id)} className="text-[#8A97A3] hover:text-[#FF5C5C] text-xs">Sil ✕</button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
