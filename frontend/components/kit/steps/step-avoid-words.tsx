'use client'

import { useTranslations } from 'next-intl';
import { useLocale } from 'next-intl'
import { KitQuestion } from '@/components/kit/kit-question'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { KitAnswers } from '@/types'

interface StepProps {
  answers: KitAnswers
  onChange: (partial: Partial<KitAnswers>) => void
  brandName: string
}

export function StepAvoidWords({ answers, onChange }: StepProps) {
  const t = useTranslations('components.kit.steps.step-avoid-words');
  const locale = useLocale()
  return (
    <div className="space-y-6">
      <KitQuestion
        align="center"
        before={t('anything_to_prefix')}
        emphasis={t('avoid_word')}
        helper={t('avoid_help')}
      />
      <div className="mx-auto w-full max-w-[760px] space-y-3 rounded-xl border border-brand-accent/15 bg-white p-5 sm:p-7">
        <Label htmlFor="kit-avoid" className="font-tajawal text-[12px] font-semibold">{t('avoid_label')}</Label>
        <Textarea
          id="kit-avoid"
          value={answers.avoid_words ?? ''}
          maxLength={500}
          onChange={(e) => onChange({ avoid_words: e.target.value || null })}
          placeholder={t('words_or_themes_to')}
          rows={10}
          className={`min-h-[300px] resize-y border-brand-accent/15 bg-brand-cream/20 font-tajawal text-[13px] ${locale === 'ar' ? 'text-right' : 'text-left'}`}
          dir={locale === 'ar' ? 'rtl' : 'ltr'}
        />
        <p dir="ltr" className={`text-[12px] text-muted-foreground ${locale === 'ar' ? 'text-left' : 'text-right'}`}>
          {answers.avoid_words?.length ?? 0}/500
        </p>
      </div>
    </div>
  )
}
