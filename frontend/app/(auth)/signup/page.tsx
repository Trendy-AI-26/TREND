'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { ArrowUpRight, Eye, EyeOff, Mail, UserRound } from 'lucide-react'
import { authApi, authErrorMessage } from '@/lib/auth/client'
import { AuthShell } from '@/components/auth/auth-shell'

export default function SignUpPage() {
  const router = useRouter()
  const t = useTranslations('auth')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    let result: Awaited<ReturnType<typeof authApi.signup>>
    try {
      result = await authApi.signup({ email, password, full_name: name })
    } catch (err) {
      setLoading(false)
      setError(authErrorMessage(err, t))
      return
    }
    setLoading(false)

    // Email verification is switched off on the server: it already set the
    // session cookie, so go straight in.
    if (result.verification_required === false) {
      router.push('/dashboard')
      router.refresh()
      return
    }

    // The backend e-mails a 6-digit code; the user confirms it on /verify-code.
    router.push(`/verify-code?email=${encodeURIComponent(email)}&purpose=verify_email`)
  }

  return (
    <AuthShell eyebrow={t('signupEyebrow')} title={t('signupTitle')} subtitle={t('signupDescription')}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        <div>
          <label htmlFor="full-name" className="mb-2 block text-[12px] font-bold uppercase tracking-[0.04em] text-[#424242]">{t('fullName')}</label>
          <div className="relative">
            <input id="full-name" type="text" placeholder={t('fullNamePlaceholder')} value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" className="auth-input h-12 w-full rounded-xl border px-4 pe-11 text-sm outline-none transition placeholder:text-[#b1b1b1]" />
            <UserRound className="pointer-events-none absolute end-4 top-1/2 h-[17px] w-[17px] -translate-y-1/2 text-[#999]" strokeWidth={1.5} />
          </div>
        </div>
        <div>
          <label htmlFor="email" className="mb-2 block text-[12px] font-bold uppercase tracking-[0.04em] text-[#424242]">{t('email')}</label>
          <div className="relative">
            <input id="email" type="email" placeholder={t('emailPlaceholder')} value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" dir="ltr" className="auth-input h-12 w-full rounded-xl border px-4 pe-11 text-sm outline-none transition placeholder:text-[#b1b1b1]" />
            <Mail className="pointer-events-none absolute end-4 top-1/2 h-[17px] w-[17px] -translate-y-1/2 text-[#999]" strokeWidth={1.5} />
          </div>
        </div>
        <div>
          <label htmlFor="password" className="mb-2 block text-[12px] font-bold uppercase tracking-[0.04em] text-[#424242]">{t('password')}</label>
          <div className="relative">
            <input id="password" type={showPassword ? 'text' : 'password'} placeholder={t('passwordPlaceholder')} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" className="auth-input h-12 w-full rounded-xl border px-4 pe-11 text-sm outline-none transition placeholder:text-[#b1b1b1]" />
            <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? t('hidePassword') : t('showPassword')} className="absolute end-3 top-1/2 -translate-y-1/2 rounded p-1 text-[#999] hover:text-[#7A1521]">
              {showPassword ? <EyeOff className="h-[17px] w-[17px]" strokeWidth={1.5} /> : <Eye className="h-[17px] w-[17px]" strokeWidth={1.5} />}
            </button>
          </div>
        </div>
        <button type="submit" disabled={loading} className="auth-submit flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#7A1521] text-[15px] font-semibold text-white transition hover:bg-[#9c2a37] disabled:cursor-not-allowed disabled:opacity-60">
          {loading ? t('creatingAccount') : t('createAccount')} <ArrowUpRight className="h-[17px] w-[17px]" strokeWidth={2} />
        </button>
        <p className="pt-1 text-center text-[13px] text-[#888]">{t('hasAccount')}{' '}<Link href="/login" className="font-semibold text-[#7A1521] hover:underline">{t('loginTitle')}</Link></p>
      </form>
    </AuthShell>
  )
}
