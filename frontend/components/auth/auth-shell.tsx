'use client'

import Image from 'next/image'
import type { ReactNode } from 'react'
import { BarChart3, CalendarDays, Image as ImageIcon, MessageSquareText, Hash } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import LanguageSwitcher from '@/components/language-switcher'

interface AuthShellProps {
  eyebrow: string
  title: ReactNode
  subtitle: string
  children: ReactNode
}

const visualMarkers = [
  { icon: ImageIcon, className: 'left-[11%] top-[21%]' },
  { icon: BarChart3, className: 'right-[11%] top-[25%]' },
  { icon: MessageSquareText, className: 'right-[17%] top-[39%]' },
  { icon: CalendarDays, className: 'left-[10%] top-[43%]' },
  { icon: Hash, className: 'right-[12%] top-[51%]' },
]

export function AuthShell({ eyebrow, title, subtitle, children }: AuthShellProps) {
  const t = useTranslations('components.auth.auth-shell')
  const locale = useLocale()
  const isArabic = locale === 'ar'

  return (
    <main className="auth-page min-h-screen bg-white px-4 py-6 text-[#171717] sm:px-8 sm:py-8 lg:px-10 lg:py-12">
      <div className="mx-auto flex min-h-[calc(100vh-6rem)] w-full max-w-[1140px] flex-col">
        <div className="auth-card grid flex-1 overflow-hidden rounded-[30px] border border-[#eee] bg-white shadow-[0_24px_60px_rgba(64,36,51,0.12)] lg:grid-cols-[1fr_0.98fr]">
          <section className="auth-visual relative hidden min-h-[610px] overflow-hidden lg:block">
            <Image src="/auth-bg.jpg" alt="" fill priority sizes="50vw" className="object-cover" />
            <div className="absolute inset-0 bg-gradient-to-b from-[#451b3d]/10 via-transparent to-[#241426]/65" />
            <div className="absolute left-8 top-8 flex items-center gap-2.5 text-white" dir="ltr">
              <a href="/" aria-label={t('backToHome')}>
                <Image src="/trendy_logo.png" alt="" width={30} height={30} className="h-7 w-7 rounded-full bg-white object-contain p-1" />
              </a>
              <span className="font-el-messiri text-[27px] font-medium tracking-[-0.06em]">trendy</span>
              <span className="font-tajawal rounded-full border border-white/50 bg-white/15 px-2 py-0.5 text-[11px] font-medium backdrop-blur-sm">AI</span>
            </div>
            <span className="absolute right-9 top-16 text-sm font-semibold text-white/80">{t('brandArabic')}</span>
            {visualMarkers.map(({ icon: Icon, className }, index) => (
              <span
                key={index}
                className={`auth-floating-marker absolute flex h-12 w-12 items-center justify-center rounded-2xl border border-white/50 bg-white/20 text-white shadow-lg backdrop-blur-md ${className}`}
              >
                <Icon className="h-5 w-5" strokeWidth={1.7} />
              </span>
            ))}
            <div className={`absolute bottom-8 left-8 right-8 rounded-2xl border border-white/15 bg-[#241426]/35 p-5 text-white shadow-[0_10px_30px_rgba(20,8,25,0.18)] backdrop-blur-[3px] ${isArabic ? 'text-right' : 'text-left'}`} dir={isArabic ? 'rtl' : 'ltr'}>
              <h1 className="font-el-messiri max-w-[360px] text-[37px] font-semibold leading-[1.05] tracking-[-0.05em] drop-shadow-[0_2px_4px_rgba(0,0,0,0.35)]">{t('visualTitleBefore')} <span className="text-[#f594a8]">{t('visualTitleAccent')}</span></h1>
              <p className="font-tajawal mt-3 max-w-[390px] text-[14px] leading-6 text-white/90 drop-shadow-[0_1px_3px_rgba(0,0,0,0.45)]">{t('visualSubtitle')}</p>
            </div>
          </section>

          <section className="relative flex min-h-[610px] flex-col px-7 py-8 sm:px-12 sm:py-12 lg:px-[74px] lg:py-[58px]" dir={isArabic ? 'rtl' : 'ltr'}>
            <div className="flex justify-end">
              <LanguageSwitcher />
            </div>
            <div className="mx-auto flex w-full max-w-[448px] flex-1 flex-col justify-center py-8">
              <p className="text-[12px] font-bold uppercase tracking-[0.11em] text-[#832044]">{eyebrow}</p>
              <h2 className="font-el-messiri mt-3 text-[32px] font-semibold leading-tight tracking-[-0.045em] text-[#171717] sm:text-[34px]">{title}</h2>
              <p className="font-tajawal mt-2 text-[15px] leading-6 text-[#858585]">{subtitle}</p>
              <div className="mt-7">{children}</div>
            </div>
          </section>
        </div>
        <footer className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 px-4 pt-6 text-[11px] text-[#a1a1a1]" dir="ltr">
          <span>{t('terms')}</span><span>•</span><span>{t('privacy')}</span><span>•</span><span>{t('copyright')}</span>
        </footer>
      </div>
    </main>
  )
}