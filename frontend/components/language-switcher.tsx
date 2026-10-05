"use client"

import { useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { Globe } from 'lucide-react'

interface LanguageSwitcherProps {

  variant?: 'pill' | 'compact'
}

export default function LanguageSwitcher({ variant = 'pill' }: LanguageSwitcherProps) {
  const locale = useLocale() as 'ar' | 'en'
  const t = useTranslations('langToggle')
  const router = useRouter()
  const [pending, startTransition] = useTransition()
  const next = locale === 'ar' ? 'en' : 'ar'

  function switchLanguage() {
    const nextDir = next === 'ar' ? 'rtl' : 'ltr'
    document.cookie = `NEXT_LOCALE=${next};path=/;max-age=31536000;sameSite=lax`
    if (typeof document !== 'undefined') {
      document.documentElement.dir = nextDir
      document.documentElement.lang = next
    }
    startTransition(() => router.refresh())
  }

  if (variant === 'compact') {

    return (
      <button
        type="button"
        onClick={switchLanguage}
        disabled={pending}
        aria-label={t('ariaLabel')}
        title={t('switchTo')}
        className="inline-flex h-8 w-8 items-center justify-center rounded-full text-brand-headline transition-colors hover:bg-brand-bg/60 disabled:opacity-50"
      >
        <Globe className="h-[18px] w-[18px]" />
      </button>
    )
  }
  return (
    <button type="button" onClick={switchLanguage} disabled={pending}
      aria-label={t('ariaLabel')}
      className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold transition-colors">
      <Globe className="h-3.5 w-3.5" />
      <span>{t('switchTo')}</span>
    </button>
  )
}