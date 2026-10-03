'use client'

import { useTranslations } from 'next-intl'
import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ReadyToGenerateCardProps {
  completedSections: number
  totalSections: number
  onGenerate: () => void
}

export function ReadyToGenerateCard({
  completedSections,
  totalSections,
  onGenerate,
}: ReadyToGenerateCardProps) {
  const t = useTranslations('components.generation.wizard')
  const allDone = completedSections >= totalSections

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-[14px] border border-brand-accent/20 bg-white px-5 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.03)] sm:px-7">
      <div>
        <p className="text-[14px] font-bold leading-[21px] text-brand-headline">{t('ready_title')}</p>
        <p className="mt-0.5 text-[12.5px] text-brand-headline/40">
          {allDone
            ? t('ready_all_done')
            : t('ready_progress', { done: completedSections, total: totalSections })}
        </p>
      </div>

      <Button
        type="button"
        onClick={onGenerate}
        disabled={!allDone}
        className="h-12 rounded-[12px] bg-brand-primary px-7 text-[14.5px] font-extrabold text-white hover:bg-brand-primary/90 disabled:bg-brand-accent/20 disabled:text-brand-headline/40 disabled:opacity-100"
      >
        <Sparkles />
        {t('generate')}
      </Button>
    </div>
  )
}