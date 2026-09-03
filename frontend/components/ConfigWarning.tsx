const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? '';
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '';

export function isSupabaseConfigured(): boolean {
  if (!url || !anonKey) return false;
  if (anonKey.includes('YOUR_SUPABASE_ANON_KEY_HERE')) return false;
  if (anonKey.startsWith('sb_secret_')) return false;
  return true;
}

export default function ConfigWarning() {
  if (isSupabaseConfigured()) return null;
  return (
    <div className="border border-[#FFB020] bg-[#FFB020]/10 text-[#FFB020] text-sm p-4 mb-4 font-[family-name:var(--font-mono)]">
      Supabase bağlantısı yapılandırılmamış. `frontend/.env.local` dosyasına Dashboard → Settings → API
      altındaki `anon public` anahtarını girin (bkz. `.env.example`). Backend durumu için{' '}
      <a href="http://localhost:8000/health" className="underline" target="_blank" rel="noreferrer">
        /health
      </a>{' '}
      endpoint&apos;ini kontrol edin.
    </div>
  );
}
