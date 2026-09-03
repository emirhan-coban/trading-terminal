const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type NewsItem = {
  title: string;
  link: string;
  published: string;
  source: string;
};

async function getNews(ticker: string): Promise<NewsItem[]> {
  try {
    const res = await fetch(`${API}/news/${encodeURIComponent(ticker)}`, { cache: 'no-store' });
    if (!res.ok) return [];
    const data = await res.json();
    return data.items || [];
  } catch {
    return [];
  }
}

export default async function NewsPanel({ ticker }: { ticker: string }) {
  const items = await getNews(ticker);
  if (items.length === 0) return null;

  return (
    <section className="border border-[#1F2933] p-4 mt-4">
      <h2 className="text-sm text-[#8A97A3] mb-3 font-[family-name:var(--font-mono)]">Haberler</h2>
      <ul className="space-y-3">
        {items.map((n, i) => (
          <li key={`${n.link}-${i}`}>
            <a href={n.link} target="_blank" rel="noreferrer" className="text-sm hover:text-[#3DDC84] transition">
              {n.title}
            </a>
            <div className="text-xs text-[#8A97A3] mt-0.5">
              {n.source}{n.published ? ` · ${n.published}` : ''}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
