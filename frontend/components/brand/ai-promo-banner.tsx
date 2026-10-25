'use client'

import { useState } from 'react'
import { ArrowLeft, Sparkles, X } from 'lucide-react'
import { useTranslations } from 'next-intl'

interface AiPromoBannerProps {
  brandName?: string
  onStart?: () => void
}

export function AiPromoBanner({ brandName, onStart }: AiPromoBannerProps) {
  const t = useTranslations('components.brand.ai-promo-banner')
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  return (
    <div className="fixed bottom-4 start-4 end-4 z-30 md:start-[248px] md:end-8">
      <div className="flex flex-col gap-3 rounded-2xl bg-gradient-to-l from-brand-primary to-[#2a0a10] p-4 text-white shadow-lg sm:flex-row sm:items-center sm:gap-4 sm:p-5">
        <span className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/10 sm:flex">
          <Sparkles className="h-5 w-5 text-brand-accent" />
        </span>

        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-bold uppercase tracking-wide text-brand-accent">{t('eyebrow')}</p>
          <h3 className="mt-0.5 truncate text-[15px] font-bold leading-snug sm:text-[16px]">
            {brandName ? t('heading_with_brand', { brand: brandName }) : t('heading')}
          </h3>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={onStart}
            className="flex items-center gap-1.5 rounded-lg bg-brand-accent px-4 py-2 text-[13px] font-bold text-brand-headline transition-opacity duration-fast hover:opacity-90"
          >
            {t('cta')}
            <ArrowLeft className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => setDismissed(true)}
            aria-label={t('close')}
            className="flex h-8 w-8 items-center justify-center rounded-full text-white/70 transition-colors duration-fast hover:bg-white/10 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}