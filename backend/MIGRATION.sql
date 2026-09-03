-- Supabase Dashboard → SQL Editor'da çalıştırın.
-- IDEMPOTENT: kaç kez çalıştırırsanız çalıştırın güvenli, yarım kalmış
-- çalıştırmayı kaldığı yerden tamamlar.
-- v2.0 ile eklenen yeni kolonlar (kod, bunlar yoksa da çalışır ama
-- temettü verimi / piyasa değeri gösterilmez).

alter table public.financials
  add column if not exists dividend_yield double precision,
  add column if not exists market_cap double precision;

-- Watchlist'teki tekrar kayıtları temizle (örn. SOKM.IS iki kez)
-- ve gelecekte tekrarını unique constraint ile engelle.
delete from public.watchlist a
using public.watchlist b
where a.ctid < b.ctid
  and a.ticker = b.ticker;

-- ADD CONSTRAINT'in IF NOT EXISTS'i yok; DO bloğu ile korunur.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'watchlist_ticker_unique'
  ) then
    alter table public.watchlist
      add constraint watchlist_ticker_unique unique (ticker);
  end if;
end $$;

-- v2.1: portföy takibi
create table if not exists public.portfolio (
  ticker text primary key,
  quantity double precision not null check (quantity > 0),
  avg_cost double precision not null check (avg_cost > 0),
  updated_at timestamptz not null default now()
);

-- v2.1: fiyat alarm sistemi (koşullar: price_above/price_below,
-- rsi_above/rsi_below, score_above/score_below)
create table if not exists public.alerts (
  id bigint generated always as identity primary key,
  ticker text not null,
  condition text not null,
  target_value double precision not null,
  is_active boolean not null default true,
  last_value double precision,
  triggered_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists alerts_active_idx
  on public.alerts (is_active) where is_active = true;
