'use client'

import { useTranslations } from 'next-intl';
import Image from 'next/image'
import { KitQuestion } from '@/components/kit/kit-question'
import { KitAnswers } from '@/types'

interface StepProps {
  answers: KitAnswers
  onChange: (partial: Partial<KitAnswers>) => void
  brandName: string
  logoUrl?: string | null
}

export function StepName({ brandName, logoUrl }: StepProps) {
  const t = useTranslations('components.kit.steps.step-name');
  return (
    <div className="space-y-7">
      <KitQuestion
        align="center"
        before={t('this_is_prefix')}
        emphasis={brandName}
        after="."
        helper={t('registered_name_help')}
      />
      <div className="mx-auto flex min-h-[220px] w-full max-w-[440px] flex-col items-center justify-center gap-3 rounded-xl border border-brand-accent/15 bg-white px-6 py-8 shadow-xs sm:min-h-[260px]">
        {logoUrl ? (
          <Image src={logoUrl} alt="" width={64} height={64} className="h-16 w-16 rounded-xl border border-brand-accent/15 bg-brand-cream object-contain p-2" />
        ) : (
          <span className="flex h-16 w-16 items-center justify-center rounded-xl border border-brand-accent/20 bg-brand-cream font-el-messiri text-2xl font-bold text-brand-primary">{brandName.slice(0, 1).toUpperCase()}</span>
        )}
        <p className="break-words text-center font-el-messiri text-[22px] font-bold text-brand-headline">{brandName}</p>
      </div>
    </div>
  )
}