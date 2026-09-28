'use client'

import Image from 'next/image'
import Link from 'next/link'
import { Check, ArrowRight } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import LanguageSwitcher from '@/components/language-switcher'

export default function ResetSuccessPage() {
  const t = useTranslations('auth')
  const shell = useTranslations('components.auth.auth-shell')
  const locale = useLocale()
  const isArabic = locale === 'ar'

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
          <div className="w-full max-w-[480px] rounded-[28px] bg-white px-6 py-8 text-center shadow-[0_16px_36px_rgba(102,43,65,0.08)] sm:px-10 sm:py-9">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#fcecef] text-[#8b1d46]">
              <Check className="h-7 w-7" strokeWidth={2.4} />
            </div>
            <p className="mt-5 text-[10px] font-bold uppercase tracking-[0.1em] text-[#8b1d46]">{t('securityUpdateComplete')}</p>
            <h1 className="font-el-messiri mt-2 text-[27px] font-bold leading-tight tracking-[-0.045em] text-[#111827] sm:text-[30px]">{t('passwordResetSuccessful')}</h1>
            <p className="font-tajawal mx-auto mt-2 max-w-[350px] text-[13px] leading-5 text-[#777b82]">{t('passwordResetSuccessfulDescription')}</p>
            <Link href="/login" className="forgot-submit mx-auto mt-6 flex h-10 w-full items-center justify-center gap-3 rounded-xl bg-[#8b1d46] text-[13px] font-bold text-white transition hover:bg-[#a42b59] active:scale-[0.99]">
              {t('signInNow')} <ArrowRight className="h-[18px] w-[18px] rtl-flip-chevron" strokeWidth={2} />
            </Link>
          </div>
        </section>

        <footer className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 pb-1 text-[11px] text-[#a4a5a8]" dir="ltr">
          <span>{shell('terms')}</span><span>•</span><span>{shell('privacy')}</span><span>•</span><span>{shell('copyright')}</span>
        </footer>
      </div>
    </main>
  )
}



