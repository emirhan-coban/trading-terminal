import { describe, it, expect } from 'vitest';
import { scoreColor, fmt, formatPercent, normalizeTicker, stripIS } from './utils';

describe('scoreColor', () => {
  it('null/undefined için nötr renk', () => {
    expect(scoreColor(null)).toBe('text-[#8A97A3]');
    expect(scoreColor(undefined)).toBe('text-[#8A97A3]');
  });
  it('güçlü pozitif için yeşil', () => {
    expect(scoreColor(21)).toBe('text-[#3DDC84]');
    expect(scoreColor(100)).toBe('text-[#3DDC84]');
  });
  it('güçlü negatif için kırmızı', () => {
    expect(scoreColor(-21)).toBe('text-[#FF5C5C]');
    expect(scoreColor(-100)).toBe('text-[#FF5C5C]');
  });
  it('sınırda değerler için sarı', () => {
    expect(scoreColor(20)).toBe('text-[#FFB020]');
    expect(scoreColor(-20)).toBe('text-[#FFB020]');
    expect(scoreColor(0)).toBe('text-[#FFB020]');
  });
});

describe('fmt', () => {
  it('sayıyı formatlar', () => {
    expect(fmt(4.286)).toBe('4.29');
    expect(fmt(4.286, 1)).toBe('4.3');
  });
  it('boş değerde tire döner', () => {
    expect(fmt(null)).toBe('—');
    expect(fmt(undefined)).toBe('—');
  });
});

describe('formatPercent', () => {
  it('ondalığı yüzdeye çevirir', () => {
    expect(formatPercent(0.205)).toBe('20.5%');
  });
  it('boş değerde tire döner', () => {
    expect(formatPercent(null)).toBe('—');
  });
});

describe('ticker yardımcıları', () => {
  it('normalizeTicker .IS ekler', () => {
    expect(normalizeTicker('thyao')).toBe('THYAO.IS');
    expect(normalizeTicker('THYAO.IS')).toBe('THYAO.IS');
    expect(normalizeTicker('  garan ')).toBe('GARAN.IS');
  });
  it('stripIS .IS söker', () => {
    expect(stripIS('THYAO.IS')).toBe('THYAO');
    expect(stripIS('THYAO')).toBe('THYAO');
  });
});
