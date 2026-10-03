'use client'

import { useTranslations } from 'next-intl'
import { Check, Loader2, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

interface GenerationLoadingProps {
  stage: 'uploading' | 'generating'
  hasProductImage: boolean
}

export function GenerationLoading({ stage, hasProductImage }: GenerationLoadingProps) {
  const t = useTranslations('components.generation.wizard')

  const steps = [
    ...(hasProductImage ? [{ key: 'uploading', label: t('loading_uploading') }] : []),
    { key: 'generating', label: t('loading_generating') },
  ]
  const currentIndex = steps.findIndex((s) => s.key === stage)

  return (
    <section
      aria-live="polite"
      aria-busy="true"
      className="flex flex-col items-center rounded-[16px] border border-brand-accent/20 bg-white px-6 py-14 text-center shadow-[0_1px_8px_rgba(0,0,0,0.04)]"
    >
      <span className="relative flex h-16 w-16 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-brand-primary/10" />
        <span className="relative flex h-16 w-16 items-center justify-center rounded-full bg-brand-primary/10 text-brand-primary">
          <Sparkles className="h-7 w-7" />
        </span>
      </span>

      <h2 className="mt-6 font-el-messiri text-[22px] font-semibold text-brand-headline">{t('loading_title')}</h2>
      <p className="mt-1 text-[14px] font-bold text-brand-primary">{t('loading_subtitle')}</p>
      <p className="mt-2 max-w-[380px] text-[12.5px] leading-[20px] text-brand-headline/50">{t('loading_text')}</p>

      <ol className="mt-7 w-full max-w-[280px] space-y-2.5 text-start">
        {steps.map((step, index) => {
          const done = index < currentIndex
          const active = index === currentIndex
          return (
            <li key={step.key} className="flex items-center gap-2.5 text-[13px]">
              <span
                className={cn(
                  'flex h-5 w-5 shrink-0 items-center justify-center rounded-full',
                  done && 'bg-brand-primary text-white',
                  active && 'text-brand-primary',
                  !done && !active && 'bg-brand-bg',
                )}
              >
                {done ? (
                  <Check className="h-3 w-3" strokeWidth={3} />
                ) : active ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : null}
              </span>
              <span className={cn(active ? 'font-bold text-brand-headline' : 'text-brand-headline/50')}>
                {step.label}
              </span>
            </li>
          )
        })}
      </ol>
    </section>
  )
}