'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';

const navItems = [
  { href: '/', label: 'Watchlist', icon: '≡' },
  { href: '/market', label: 'Piyasa', icon: '◉' },
  { href: '/sectors', label: 'Sektörler', icon: '▦' },
  { href: '/portfolio', label: 'Portföy', icon: '◈' },
  { href: '/alerts', label: 'Alarmlar', icon: '◎' },
  { href: '/compare', label: 'Karşılaştır', icon: '⇄' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 bg-[#0D1117] border-r border-[#1F2933] flex flex-col shrink-0">
      <div className="p-4 border-b border-[#1F2933]">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-[#3DDC84] text-xl font-bold">◆</span>
          <span className="font-[family-name:var(--font-mono)] font-semibold text-sm">
            BORSA TERMINALI
          </span>
        </Link>
      </div>

      <nav className="flex-1 p-2">
        {navItems.map((item) => {
          const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded text-sm transition ${
                active
                  ? 'bg-[#1F2933] text-[#E8E6E1]'
                  : 'text-[#8A97A3] hover:bg-[#161D27] hover:text-[#E8E6E1]'
              }`}
            >
              <span className="text-base w-5 text-center">{item.icon}</span>
              <span className="font-[family-name:var(--font-mono)]">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-[#1F2933]">
        <SearchBox />
      </div>

      <div className="p-3 border-t border-[#1F2933]">
        <AuthBox />
      </div>

      <div className="p-3 border-t border-[#1F2933] text-xs text-[#8A97A3] font-[family-name:var(--font-mono)]">
        <div>v2.1.0</div>
        <div className="mt-1">BIST Analiz Terminali</div>
      </div>
    </aside>
  );
}

function AuthBox() {
  const { user, loading, configured, signOut } = useAuth();

  if (loading) {
    return <div className="text-xs text-[#8A97A3] font-[family-name:var(--font-mono)]">...</div>;
  }
  if (!configured) {
    return (
      <Link href="/login" className="block text-xs font-[family-name:var(--font-mono)] text-[#FFB020] hover:underline">
        ⚠ Supabase kurulu değil
      </Link>
    );
  }
  if (!user) {
    return (
      <Link href="/login" className="block text-center text-xs font-[family-name:var(--font-mono)] border border-[#1F2933] rounded px-3 py-2 text-[#8A97A3] hover:text-[#E8E6E1] hover:border-[#3DDC84] transition">
        Giriş Yap
      </Link>
    );
  }
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs font-[family-name:var(--font-mono)] text-[#8A97A3] truncate" title={user.email}>
        {user.email}
      </span>
      <button onClick={signOut} className="text-xs font-[family-name:var(--font-mono)] text-[#8A97A3] hover:text-[#FF5C5C]">
        Çıkış
      </button>
    </div>
  );
}

function SearchBox() {
  return (
    <Link
      href="/search"
      className="flex items-center gap-2 px-3 py-2 bg-[#161D27] border border-[#1F2933] rounded text-sm text-[#8A97A3] hover:border-[#3DDC84] transition"
    >
      <span>⌕</span>
      <span className="font-[family-name:var(--font-mono)] text-xs">Hisse Ara...</span>
      <span className="ml-auto text-[10px] bg-[#1F2933] px-1.5 py-0.5 rounded">⌘K</span>
    </Link>
  );
}
