'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { ArrowUpRight, Eye, EyeOff, Mail } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { AuthShell } from '@/components/auth/auth-shell'

export default function LoginPage() {
  const router = useRouter()
  const t = useTranslations('auth')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    const { error: signInError } = await createClient().auth.signInWithPassword({ email, password })
    setLoading(false)

    if (signInError) {
      setError(signInError.message)
      return
    }

    router.push('/brands')
    router.refresh()
  }

  return (
    <AuthShell eyebrow={t('loginEyebrow')} title={t('loginTitle')} subtitle={t('loginDescription')}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-[#7A1521]">{error}</div>}
        <div>
          <label htmlFor="email" className="mb-2 block text-[12px] font-bold uppercase tracking-[0.04em] text-[#424242]">{t('email')}</label>
          <div className="relative">
            <input id="email" type="email" placeholder={t('emailPlaceholder')} value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" dir="ltr" className="auth-input h-12 w-full rounded-xl border px-4 pe-11 text-sm outline-none transition placeholder:text-[#b1b1b1]" />
            <Mail className="pointer-events-none absolute end-4 top-1/2 h-[17px] w-[17px] -translate-y-1/2 text-[#999]" strokeWidth={1.5} />
          </div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <label htmlFor="password" className="block text-[12px] font-bold uppercase tracking-[0.04em] text-[#424242]">{t('password')}</label>
            <Link href="/forgot-password" className="text-[12px] font-semibold text-[#7A1521] hover:underline">{t('forgotPassword')}</Link>
          </div>
          <div className="relative">
            <input id="password" type={showPassword ? 'text' : 'password'} placeholder={t('passwordPlaceholder')} value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" className="auth-input h-12 w-full rounded-xl border px-4 pe-11 text-sm outline-none transition placeholder:text-[#b1b1b1]" />
            <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? t('hidePassword') : t('showPassword')} className="absolute end-3 top-1/2 -translate-y-1/2 rounded p-1 text-[#999] hover:text-[#7A1521]">
              {showPassword ? <EyeOff className="h-[17px] w-[17px]" strokeWidth={1.5} /> : <Eye className="h-[17px] w-[17px]" strokeWidth={1.5} />}
            </button>
          </div>
        </div>
        <button type="submit" disabled={loading} className="auth-submit flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#7A1521] text-[15px] font-semibold text-white transition hover:bg-[#9c2a37] disabled:cursor-not-allowed disabled:opacity-60">
          {loading ? t('loggingIn') : t('loginTitle')} <ArrowUpRight className="h-[17px] w-[17px]" strokeWidth={2} />
        </button>
        <p className="pt-1 text-center text-[13px] text-[#888]">{t('noAccount')}{' '}<Link href="/signup" className="font-semibold text-[#7A1521] hover:underline">{t('signUp')}</Link></p>
      </form>
    </AuthShell>
  )
}
