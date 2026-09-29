'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useState } from 'react'
import { ArrowRight, CheckCircle2, Mail } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import LanguageSwitcher from '@/components/language-switcher'
import { createClient } from '@/lib/supabase/client'

export default function ForgotPasswordPage() {
  const t = useTranslations('auth')
  const shell = useTranslations('components.auth.auth-shell')
  const locale = useLocale()
  const isArabic = locale === 'ar'
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    const redirectTo = `${window.location.origin}/auth/confirm?next=/reset-password`
    const { error: resetError } = await createClient().auth.resetPasswordForEmail(email, { redirectTo })
    setLoading(false)
    if (resetError) {
      setError(resetError.message)
      return
    }
    setSent(true)
  }

  return (
    <main className="forgot-page min-h-screen bg-[#fbf8f8] px-5 py-5 text-[#121827] sm:px-7 sm:py-6 lg:h-screen lg:overflow-hidden lg:px-7 lg:py-6" dir={isArabic ? 'rtl' : 'ltr'}>
      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] w-full max-w-[1225px] flex-col lg:min-h-0 lg:h-full">
        <header className="flex items-center justify-between gap-4" dir="ltr">
          <Link href="/" aria-label={shell('backToHome')} className="group inline-flex items-center gap-2.5">
            <Image src="/trendy_logo.png" alt="" width={31} height={31} className="h-8 w-8 object-contain" priority />
            <span className="font-el-messiri text-[25px] font-semibold tracking-[-0.06em] text-[#861b41]">trendy</span>
            <span className="font-tajawal text-[12px] font-medium text-[#a98d98]">AI</span>
          </Link>
          <LanguageSwitcher />
        </header>

        <section className="flex flex-1 items-center justify-center py-6 sm:py-8">
          <div className="w-full max-w-[530px] rounded-[28px] bg-white px-6 py-7 shadow-[0_16px_36px_rgba(102,43,65,0.08)] sm:px-10 sm:py-8">
            {sent ? (
              <div className="text-center">
                <CheckCircle2 className="mx-auto h-12 w-12 text-[#8b1d46]" strokeWidth={1.6} />
                <p className="mt-6 text-[12px] font-bold uppercase tracking-[0.1em] text-[#8b1d46]">{t('resetEyebrow')}</p>
                <h1 className="font-el-messiri mt-2 text-[29px] font-bold leading-tight tracking-[-0.045em] text-[#111827] sm:text-[32px]">{t('resetSentTitle')}</h1>
                <p className="font-tajawal mx-auto mt-2 max-w-[390px] text-[14px] leading-5 text-[#777b82]">{t('resetSentDescription')} <strong className="font-semibold text-[#4d5158]">{email}</strong>.</p>
                <Link href="/login" className="mt-6 inline-flex items-center gap-2 font-tajawal text-[13px] font-bold text-[#861b41] hover:underline">
                  {t('backToLogin')} <ArrowRight className="h-4 w-4 rtl-flip-chevron" strokeWidth={2} />
                </Link>
              </div>
            ) : (
              <>
                <p className="text-[12px] font-bold uppercase tracking-[0.1em] text-[#8b1d46]">{t('resetEyebrow')}</p>
                <h1 className="font-el-messiri mt-2 text-[29px] font-bold leading-tight tracking-[-0.045em] text-[#111827] sm:text-[32px]">{t('resetTitle')}</h1>
                <p className="font-tajawal mt-2 text-[14px] leading-5 text-[#777b82]">{t('resetDescription')}</p>

                <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                  {error && <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-[#7A1521]">{error}</div>}
                  <div>
                    <label htmlFor="reset-email" className="mb-2 block text-[12px] font-bold uppercase tracking-[0.04em] text-[#3e444f]">{t('email')}</label>
                    <div className="relative">
                      <input id="reset-email" type="email" placeholder={t('resetEmailPlaceholder')} value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" dir="ltr" className="forgot-input h-12 w-full rounded-2xl border px-4 pe-12 text-sm outline-none transition placeholder:text-[#b0b2b6]" />
                      <Mail className="pointer-events-none absolute end-4 top-1/2 h-[19px] w-[19px] -translate-y-1/2 text-[#8f969d]" strokeWidth={1.5} />
                    </div>
                  </div>
                  <button type="submit" disabled={loading} className="forgot-submit flex h-12 w-full items-center justify-center gap-3 rounded-2xl bg-[#8b1d46] text-[14px] font-bold text-white transition hover:bg-[#a42b59] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60">
                    {loading ? t('sendingReset') : t('sendReset')} <ArrowRight className="h-[19px] w-[19px] rtl-flip-chevron" strokeWidth={2} />
                  </button>
                  <p className="font-tajawal pt-1 text-center text-[12px] text-[#85878b]">{t('rememberPassword')}{' '}<Link href="/login" className="font-bold text-[#8b1d46] hover:underline">{t('signIn')}</Link></p>
                </form>
              </>
            )}
          </div>
        </section>

        <footer className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 pb-1 text-[11px] text-[#a4a5a8]" dir="ltr">
          <span>{shell('terms')}</span><span>•</span><span>{shell('privacy')}</span><span>•</span><span>{shell('copyright')}</span>
        </footer>
      </div>
    </main>
  )
}
