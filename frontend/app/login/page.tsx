'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';

export default function LoginPage() {
  const { signIn, signUp, configured } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'in' | 'up'>('in');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    const err = mode === 'in' ? await signIn(email, password) : await signUp(email, password);
    setBusy(false);
    if (err) {
      setError(err);
    } else {
      router.push('/');
    }
  };

  const inputCls =
    'w-full bg-[#161D27] border border-[#1F2933] rounded px-4 py-2.5 text-sm font-[family-name:var(--font-mono)] focus:outline-none focus:border-[#3DDC84]';

  return (
    <div className="p-4 md:p-6 max-w-sm mx-auto pt-16">
      <h1 className="text-lg text-[#8A97A3] font-[family-name:var(--font-mono)] mb-6 text-center">
        {mode === 'in' ? 'Giriş Yap' : 'Kayıt Ol'}
      </h1>

      {!configured && (
        <div className="border border-[#FFB020] text-[#FFB020] text-xs p-3 mb-4">
          Supabase `anon` anahtarı yapılandırılmamış — giriş çalışmaz. Önce `frontend/.env.local` dosyasını doldurun.
        </div>
      )}

      {error && <div className="border border-[#FF5C5C] text-[#FF5C5C] text-sm p-3 mb-4">{error}</div>}

      <form onSubmit={submit} className="space-y-3">
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="E-posta" className={inputCls} />
        <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder="Şifre" className={inputCls} />
        <button type="submit" disabled={busy || !configured}
          className="w-full bg-[#3DDC84] text-black text-sm font-semibold px-4 py-2.5 rounded hover:opacity-90 disabled:opacity-50">
          {busy ? '...' : mode === 'in' ? 'Giriş Yap' : 'Kayıt Ol'}
        </button>
      </form>

      <button onClick={() => setMode(mode === 'in' ? 'up' : 'in')}
        className="w-full text-center text-xs text-[#8A97A3] hover:text-[#E8E6E1] mt-4">
        {mode === 'in' ? 'Hesabın yok mu? Kayıt ol' : 'Zaten hesabın var mı? Giriş yap'}
      </button>
    </div>
  );
}
