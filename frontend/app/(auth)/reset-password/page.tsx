'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ArrowRight, Eye, EyeOff, LockKeyhole, RotateCcw } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import LanguageSwitcher from '@/components/language-switcher'
import { createClient } from '@/lib/supabase/client'

export default function ResetPasswordPage() {
  const router = useRouter()
  const t = useTranslations('auth')
  const shell = useTranslations('components.auth.auth-shell')
  const locale = useLocale()
  const isArabic = locale === 'ar'
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [updated] = useState(false)

  const rules = [
    { label: t('passwordRuleLength'), valid: password.length >= 8 },
    { label: t('passwordRuleNumber'), valid: /\d/.test(password) },
    { label: t('passwordRuleUppercase'), valid: /[A-Z]/.test(password) },
  ]
  const validPassword = rules.every((rule) => rule.valid)
  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (!validPassword) {
      setError(t('passwordRequirementsError'))
      return
    }
    if (!passwordsMatch) {
      setError(t('passwordMatchError'))
      return
    }
    setLoading(true)
    const { error: updateError } = await createClient().auth.updateUser({ password })
    setLoading(false)
    if (updateError) {
      setError(updateError.message)
      return
    }
    router.push('/reset-success')
  }

  return (
    <main className="forgot-page min-h-screen bg-[#fbf8f8] px-5 py-4 text-[#121827] sm:px-7 sm:py-5 lg:h-screen lg:overflow-hidden lg:px-7 lg:py-4" dir={isArabic ? 'rtl' : 'ltr'}>
      <div className="mx-auto flex min-h-[calc(100vh-2rem)] w-full max-w-[1225px] flex-col lg:min-h-0 lg:h-full">
        <header className="flex items-center justify-between gap-4" dir="ltr">
          <Link href="/" aria-label={shell('backToHome')} className="inline-flex items-center gap-2.5">
            <Image src="/trendy_logo.png" alt="" width={31} height={31} className="h-8 w-8 object-contain" priority />
            <span className="font-el-messiri text-[25px] font-semibold tracking-[-0.06em] text-[#861b41]">trendy</span>
            <span className="font-tajawal text-[12px] font-medium text-[#a98d98]">AI</span>
          </Link>
          <LanguageSwitcher />
        </header>

        <section className="flex flex-1 items-center justify-center py-3 sm:py-4">
          <div className="w-full max-w-[480px] rounded-[26px] bg-white px-6 py-5 shadow-[0_14px_32px_rgba(102,43,65,0.08)] sm:px-10 sm:py-6">
            {updated ? (
              <div className="text-center">
                <p className="text-[12px] font-bold uppercase tracking-[0.1em] text-[#8b1d46]">{t('resetEyebrow')}</p>
                <h1 className="font-el-messiri mt-2 text-[29px] font-bold leading-tight tracking-[-0.045em] text-[#111827]">{t('passwordUpdatedTitle')}</h1>
                <p className="font-tajawal mt-2 text-[14px] leading-5 text-[#777b82]">{t('passwordUpdatedDescription')}</p>
                <Link href="/login" className="mt-6 inline-flex items-center gap-2 font-tajawal text-[13px] font-bold text-[#861b41] hover:underline">{t('signIn')} <ArrowRight className="h-4 w-4 rtl-flip-chevron" /></Link>
              </div>
            ) : (
              <>
                <p className="text-[12px] font-bold uppercase tracking-[0.1em] text-[#8b1d46]">{t('resetEyebrow')}</p>
                <h1 className="font-el-messiri mt-1.5 text-[27px] font-bold leading-tight tracking-[-0.045em] text-[#111827] sm:text-[30px]">{t('newPasswordTitle')}</h1>
                <p className="font-tajawal mt-1.5 max-w-[390px] text-[12px] leading-4 text-[#777b82]">{t('newPasswordDescription')}</p>

                <form onSubmit={handleSubmit} className="mt-4 space-y-3">
                  {error && <div role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-[#7A1521]">{error}</div>}
                  <div>
                    <label htmlFor="new-password" className="mb-1 block text-[10px] font-bold uppercase tracking-[0.04em] text-[#3e444f]">{t('newPasswordLabel')}</label>
                    <div className="relative">
                      <LockKeyhole className="pointer-events-none absolute start-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9aa0a6]" strokeWidth={1.5} />
                      <input id="new-password" type={showPassword ? 'text' : 'password'} placeholder={t('newPasswordPlaceholder')} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" className="forgot-input h-10 w-full rounded-xl border px-10 pe-11 text-[13px] outline-none transition placeholder:text-[#b0b2b6]" />
                      <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? t('hidePassword') : t('showPassword')} className="absolute end-3 top-1/2 -translate-y-1/2 rounded p-1 text-[#999] hover:text-[#8b1d46]">
                        {showPassword ? <EyeOff className="h-4 w-4" strokeWidth={1.5} /> : <Eye className="h-4 w-4" strokeWidth={1.5} />}
                      </button>
                    </div>
                    <p className="font-tajawal mt-1 text-[10px] text-[#9b9da1]">{t('mustContain')}</p>
                    <ul className="font-tajawal mt-0.5 space-y-0 text-[10px] leading-4 text-[#a5a7aa]">
                      {rules.map((rule) => <li key={rule.label} className={rule.valid ? 'text-[#56836d]' : ''}><span className="me-1">{rule.valid ? '●' : '○'}</span>{rule.label}</li>)}
                    </ul>
                  </div>

                  <div>
                    <label htmlFor="confirm-password" className="mb-1 block text-[10px] font-bold uppercase tracking-[0.04em] text-[#3e444f]">{t('confirmPasswordLabel')}</label>
                    <div className="relative">
                      <RotateCcw className="pointer-events-none absolute start-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9aa0a6]" strokeWidth={1.5} />
                      <input id="confirm-password" type={showConfirm ? 'text' : 'password'} placeholder={t('confirmPasswordPlaceholder')} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" className="forgot-input h-10 w-full rounded-xl border px-10 pe-11 text-[13px] outline-none transition placeholder:text-[#b0b2b6]" />
                      <button type="button" onClick={() => setShowConfirm((value) => !value)} aria-label={showConfirm ? t('hidePassword') : t('showPassword')} className="absolute end-3 top-1/2 -translate-y-1/2 rounded p-1 text-[#999] hover:text-[#8b1d46]">
                        {showConfirm ? <EyeOff className="h-4 w-4" strokeWidth={1.5} /> : <Eye className="h-4 w-4" strokeWidth={1.5} />}
                      </button>
                    </div>
                  </div>

                  <button type="submit" disabled={loading || !validPassword || !passwordsMatch} className="forgot-submit flex h-10 w-full items-center justify-center gap-3 rounded-xl bg-[#8b1d46] text-[13px] font-bold text-white transition hover:bg-[#a42b59] active:scale-[0.99] disabled:cursor-not-allowed disabled:bg-[#d5a6ae] disabled:opacity-100 disabled:shadow-none">
                    {loading ? t('updatingPassword') : t('resetPassword')} <ArrowRight className="h-[18px] w-[18px] rtl-flip-chevron" strokeWidth={2} />
                  </button>
                  <p className="font-tajawal text-center text-[11px] text-[#85878b]">{t('rememberPassword')}{' '}<Link href="/login" className="font-bold text-[#8b1d46] hover:underline">{t('signIn')}</Link></p>
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

