'use client'

import { useTranslations } from 'next-intl';
import { KitQuestion } from '@/components/kit/kit-question'
import { KitAnswers } from '@/types'

interface StepProps {
  answers: KitAnswers
  onChange: (partial: Partial<KitAnswers>) => void
  brandName: string
}

export function StepName({ brandName }: StepProps) {
  const t = useTranslations('components.kit.steps.step-name');
  return (
    <div className="space-y-10">
     
      <KitQuestion
        align="center"
        before={t('this_is_prefix')}
        emphasis={brandName}
        after="."
        helper={t('registered_name_help')}
      />
      <div className="mx-auto flex min-h-[90px] w-full max-w-[408px] items-center justify-center rounded-2xl border border-brand-accent/30 bg-white px-6 py-4 shadow-xs">
        <p className="break-words text-center text-[22px] font-bold text-brand-headline">
          {brandName}
        </p>
      </div>
    </div>
  )
}