const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function apiSearch(q: string) {
  const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error('Arama başarısız');
  return res.json();
}

export async function apiAnalyze(ticker: string, refresh = false, timeframe = '1d') {
  const params = new URLSearchParams();
  if (refresh) params.set('refresh', 'true');
  if (timeframe !== '1d') params.set('timeframe', timeframe);
  const qs = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/analyze/${encodeURIComponent(ticker)}${qs}`);
  if (!res.ok) throw new Error('Analiz başarısız');
  return res.json();
}

export async function apiMarketOverview() {
  const res = await fetch(`${API_BASE}/market`);
  if (!res.ok) throw new Error('Piyasa verisi alınamadı');
  return res.json();
}

export async function apiSectorPerformance() {
  const res = await fetch(`${API_BASE}/sectors`);
  if (!res.ok) throw new Error('Sektör verisi alınamadı');
  return res.json();
}

export async function apiWatchlist() {
  const res = await fetch(`${API_BASE}/watchlist`);
  if (!res.ok) throw new Error('Watchlist alınamadı');
  return res.json();
}

export async function apiRemoveFromWatchlist(ticker: string) {
  const res = await fetch(`${API_BASE}/watchlist/${encodeURIComponent(ticker)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Watchlist güncellenemedi');
  return res.json();
}

export function apiBase() {
  return API_BASE;
}

async function apiJson(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error((detail as { detail?: string }).detail || `API hatası (${res.status})`);
  }
  return res.json();
}

export async function apiPortfolioSummary() {
  return apiJson('/portfolio/summary');
}

export async function apiPortfolioAdd(ticker: string, quantity: number, price: number) {
  return apiJson('/portfolio', {
    method: 'POST',
    body: JSON.stringify({ ticker, quantity, price }),
  });
}

export async function apiPortfolioRemove(ticker: string, quantity?: number) {
  const qs = quantity != null ? `?quantity=${quantity}` : '';
  return apiJson(`/portfolio/${encodeURIComponent(ticker)}${qs}`, { method: 'DELETE' });
}

export async function apiAlerts(activeOnly = false) {
  return apiJson(`/alerts${activeOnly ? '?active_only=true' : ''}`);
}

export async function apiAlertCreate(ticker: string, condition: string, target_value: number) {
  return apiJson('/alerts', {
    method: 'POST',
    body: JSON.stringify({ ticker, condition, target_value }),
  });
}

export async function apiAlertDelete(id: number) {
  return apiJson(`/alerts/${id}`, { method: 'DELETE' });
}

export async function apiAlertsCheck() {
  return apiJson('/alerts/check', { method: 'POST' });
}

export async function apiCompare(tickers: string[], ai = false) {
  const params = new URLSearchParams({
    tickers: tickers.join(','),
    ...(ai ? { ai: 'true' } : {}),
  });
  return apiJson(`/compare?${params.toString()}`);
}

export async function apiBacktest(ticker: string, strategy = 'ma_cross') {
  return apiJson(`/backtest/${encodeURIComponent(ticker)}?strategy=${strategy}`);
}

export async function apiTickerNews(ticker: string) {
  return apiJson(`/news/${encodeURIComponent(ticker)}`);
}

export async function apiMarketNews() {
  return apiJson('/news');
}

export function apiExportUrl(ticker: string) {
  return `${API_BASE}/export/${encodeURIComponent(ticker)}`;
}
