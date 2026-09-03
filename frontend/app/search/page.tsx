'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { stripIS } from '@/lib/utils';

type SearchResult = {
  ticker: string;
  name: string;
  sector: string;
};

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const fetchResults = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch {
      setResults([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => fetchResults(query), 300);
    return () => clearTimeout(timer);
  }, [query, fetchResults]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      router.push('/');
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Hisse kodu veya şirket adı yazın..."
          className="w-full bg-[#161D27] border border-[#1F2933] rounded px-4 py-3 text-[#E8E6E1] font-[family-name:var(--font-mono)] placeholder:text-[#8A97A3] focus:outline-none focus:border-[#3DDC84] transition"
        />
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-[#8A97A3]">
            {loading ? 'Aranıyor...' : results.length > 0 ? `${results.length} sonuç` : query.length >= 2 ? 'Sonuç yok' : 'En az 2 karakter girin'}
          </span>
          <span className="text-xs text-[#8A97A3]">
            ESC ile kapat
          </span>
        </div>
      </div>

      {!loading && results.length > 0 && (
        <div className="border border-[#1F2933] divide-y divide-[#1F2933]">
          {results.map((item, idx) => (
            <Link
              key={`${item.ticker}-${idx}`}
              href={`/stock/${item.ticker}`}
              className="flex items-center justify-between p-4 hover:bg-[#12181F] transition"
            >
              <div>
                <div className="font-[family-name:var(--font-mono)] font-medium">
                  {stripIS(item.ticker)}
                </div>
                <div className="text-sm text-[#8A97A3]">{item.name}</div>
              </div>
              <div className="text-xs text-[#8A97A3] font-[family-name:var(--font-mono)]">
                {item.sector}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
