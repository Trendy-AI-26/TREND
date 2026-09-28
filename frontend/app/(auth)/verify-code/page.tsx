'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { ArrowRight, Clock3 } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import LanguageSwitcher from '@/components/language-switcher'
import { createClient } from '@/lib/supabase/client'

function maskEmail(email: string) {
  const [name, domain] = email.split('@')
  if (!name || !domain) return email || 'your@email.com'
  return `${name.slice(0, 2)}***@${domain}`
}

export default function VerifyCodePage() {
  const t = useTranslations('auth')
  const shell = useTranslations('components.auth.auth-shell')
  const locale = useLocale()
  const isArabic = locale === 'ar'
  const [code, setCode] = useState(['', '', '', '', '', ''])
  const [email, setEmail] = useState('')
  const [seconds, setSeconds] = useState(9 * 60 + 44)
  const [error, setError] = useState<string | null>(null)
  const [verified, setVerified] = useState(false)
  const [loading, setLoading] = useState(false)
  const inputRefs = useRef<Array<HTMLInputElement | null>>([])

  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get('email')
    if (value) setEmail(value)
  }, [])

  useEffect(() => {
    if (seconds <= 0) return
    const timer = window.setInterval(() => setSeconds((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [seconds])

  const minutes = String(Math.floor(seconds / 60)).padStart(2, '0')
  const remainingSeconds = String(seconds % 60).padStart(2, '0')
  const isComplete = code.every(Boolean)

  function updateCode(index: number, value: string) {
    const digit = value.replace(/\D/g, '').slice(-1)
    const next = [...code]
    next[index] = digit
    setCode(next)
    setError(null)
    if (digit && index < 5) inputRefs.current[index + 1]?.focus()
  }

  function handleKeyDown(index: number, event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Backspace' && !code[index] && index > 0) inputRefs.current[index - 1]?.focus()
    if (event.key === 'ArrowLeft' && index > 0) inputRefs.current[index - 1]?.focus()
    if (event.key === 'ArrowRight' && index < 5) inputRefs.current[index + 1]?.focus()
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!isComplete) return
    setLoading(true)
    setError(null)
    const { error: verifyError } = await createClient().auth.verifyOtp({ email, token: code.join(''), type: 'recovery' })
    setLoading(false)
    if (verifyError) {
      setError(verifyError.message)
      return
    }
    setVerified(true)
  }

  function resendCode() {
    if (seconds > 0) return
    setSeconds(9 * 60 + 44)
    setCode(['', '', '', '', '', ''])
    setError(null)
    inputRefs.current[0]?.focus()
  }

  return (
    <main className="forgot-page min-h-screen bg-[#fbf8f8] px-5 py-5 text-[#121827] sm:px-7 sm:py-6 lg:h-screen lg:overflow-hidden lg:px-7 lg:py-6" dir={isArabic ? 'rtl' : 'ltr'}>
      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] w-full max-w-[1225px] flex-col lg:min-h-0 lg:h-full">
        <header className="flex items-center justify-between gap-4" dir="ltr">
          <Link href="/" aria-label={shell('backToHome')} className="inline-flex items-center gap-2.5">
            <Image src="/trendy_logo.png" alt="" width={31} height={31} className="h-8 w-8 object-contain" priority />
            <span className="font-el-messiri text-[25px] font-semibold tracking-[-0.06em] text-[#861b41]">trendy</span>
            <span className="font-tajawal text-[12px] font-medium text-[#a98d98]">AI</span>
          </Link>
          <LanguageSwitcher />
        </header>

        <section className="flex flex-1 items-center justify-center py-6 sm:py-8">
          <div className="w-full max-w-[480px] rounded-[28px] bg-white px-6 py-7 shadow-[0_16px_36px_rgba(102,43,65,0.08)] sm:px-11 sm:py-9">
            {verified ? (
              <div className="text-center">
                <p className="text-[12px] font-bold uppercase tracking-[0.1em] text-[#8b1d46]">{t('verifyEyebrow')}</p>
                <h1 className="font-el-messiri mt-2 text-[29px] font-bold leading-tight tracking-[-0.045em] text-[#111827]">{t('codeVerifiedTitle')}</h1>
                <p className="font-tajawal mt-2 text-[14px] leading-5 text-[#777b82]">{t('codeVerifiedDescription')}</p>
                <Link href="/login" className="mt-6 inline-flex items-center gap-2 font-tajawal text-[13px] font-bold text-[#861b41] hover:underline">{t('signIn')} <ArrowRight className="h-4 w-4 rtl-flip-chevron" /></Link>
              </div>
            ) : (
              <>
                <p className="text-[12px] font-bold uppercase tracking-[0.1em] text-[#8b1d46]">{t('verifyEyebrow')}</p>
                <h1 className="font-el-messiri mt-2 text-[29px] font-bold leading-tight tracking-[-0.045em] text-[#111827] sm:text-[32px]">{t('verifyTitle')}</h1>
                <p className="font-tajawal mt-2 text-[14px] leading-5 text-[#777b82]">{t('verifyDescription')} <strong className="font-semibold text-[#4d5158]">{maskEmail(email)}</strong></p>

                <form onSubmit={handleSubmit} className="mt-6">
                  {error && <div role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-[#7A1521]">{error}</div>}
                  <div className="flex justify-between gap-2 sm:gap-3" dir="ltr">
                    {code.map((digit, index) => (
                      <input
                        key={index}
                        ref={(element) => { inputRefs.current[index] = element }}
                        value={digit}
                        onChange={(event) => updateCode(index, event.target.value)}
                        onKeyDown={(event) => handleKeyDown(index, event)}
                        onPaste={(event) => {
                          const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
                          if (!pasted) return
                          event.preventDefault()
                          setCode(Array.from({ length: 6 }, (_, item) => pasted[item] || ''))
                          inputRefs.current[Math.min(pasted.length, 5)]?.focus()
                        }}
                        inputMode="numeric"
                        maxLength={1}
                        aria-label={`${t('verificationDigit')} ${index + 1}`}
                        className="forgot-input h-16 min-w-0 flex-1 rounded-xl border text-center text-[24px] font-semibold outline-none transition sm:h-[66px]"
                      />
                    ))}
                  </div>

                  <div className="font-tajawal mt-5 flex items-center justify-center gap-2 text-[13px] text-[#999b9e]">
                    <Clock3 className="h-4 w-4" strokeWidth={1.6} />
                    <span>{t('codeExpires')}</span><strong className="font-semibold text-[#4d5158]">{minutes}:{remainingSeconds}</strong>
                  </div>

                  <button type="submit" disabled={!isComplete || loading} className="forgot-submit mt-5 flex h-12 w-full items-center justify-center gap-3 rounded-2xl bg-[#8b1d46] text-[14px] font-bold text-white transition hover:bg-[#a42b59] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60">
                    {loading ? t('verifyingCode') : t('verifyCode')} <ArrowRight className="h-[19px] w-[19px] rtl-flip-chevron" strokeWidth={2} />
                  </button>

                  <p className="font-tajawal mt-6 text-center text-[13px] text-[#85878b]">{t('didNotGetCode')}{' '}<button type="button" onClick={resendCode} disabled={seconds > 0} className="font-bold text-[#8b1d46] hover:underline disabled:cursor-not-allowed disabled:text-[#999b9e]">{t('resendCode')}</button></p>
                  <p className="font-tajawal mt-2 text-center text-[13px] text-[#a2a3a6]">{t('wrongEmail')}{' '}<Link href="/forgot-password" className="font-semibold text-[#4d5158] hover:underline">{t('changeEmail')}</Link></p>
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





