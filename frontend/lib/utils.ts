export function scoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'text-[#8A97A3]';
  if (score > 20) return 'text-[#3DDC84]';
  if (score < -20) return 'text-[#FF5C5C]';
  return 'text-[#FFB020]';
}

export function fmt(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? '—' : value.toFixed(digits);
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

export function normalizeTicker(raw: string): string {
  const upper = raw.trim().toUpperCase();
  return upper.endsWith('.IS') ? upper : `${upper}.IS`;
}

export function stripIS(ticker: string): string {
  return ticker.replace('.IS', '');
}
