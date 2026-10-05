'use client'

import { useLocale, useTranslations } from 'next-intl';
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { KitQuestion } from '@/components/kit/kit-question'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { KitAnswers } from '@/types'

interface StepProps {
  answers: KitAnswers
  onChange: (partial: Partial<KitAnswers>) => void
  brandName: string
}

export function StepAudience({ answers, onChange, brandName }: StepProps) {
  const t = useTranslations('components.kit.steps.step-audience');
  const locale = useLocale()
  const audienceSuggestions = ['founders', 'small_businesses', 'professionals', 'families', 'local_customers', 'enthusiasts'] as const
  const audienceValues = answers.audience?.split('\n').filter(Boolean) ?? []

  function toggleAudience(value: string) {
    const nextValues = audienceValues.includes(value)
      ? audienceValues.filter((item) => item !== value)
      : [...audienceValues, value]
    onChange({ audience: nextValues.length ? nextValues.join('\n') : null })
  }
  return (
    <div className="space-y-6">
      <KitQuestion
        align="center"
        before={t('who_is_it_prefix')}
        emphasis={brandName}
        after={t('audience_suffix')}
        helper={t('audience_help')}
      />
      <div className="mx-auto w-full max-w-[760px] rounded-2xl border border-brand-accent/15 bg-white p-4 shadow-xs sm:p-6">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="kit-audience" className="font-tajawal text-[12px] font-semibold text-brand-headline">{t('audience')}</Label>
              <span className="font-tajawal text-[10px] font-medium text-brand-primary">{t('required_badge')}</span>
            </div>
            <span className="font-mono text-[10px] text-muted-foreground">{answers.audience?.length ?? 0}/150</span>
          </div>
          <Textarea
            id="kit-audience"
            value={answers.audience ?? ''}
            maxLength={150}
            onChange={(e) => onChange({ audience: e.target.value || null })}
            placeholder={t('describe_your_target_audience')}
            rows={4}
            className={`min-h-[110px] resize-y border-brand-accent/15 bg-brand-cream/25 font-tajawal text-[12px] leading-6 ${locale === 'ar' ? 'text-right' : 'text-left'}`}
            dir={locale === 'ar' ? 'rtl' : 'ltr'}
          />
          <div className="flex items-center justify-between gap-2 pt-1">
            <h3 className="font-tajawal text-[11px] font-semibold text-brand-headline">{t('quick_suggestions')}</h3>
            <span className="font-tajawal text-[10px] text-muted-foreground">{t('select_multiple_hint')}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {audienceSuggestions.map((suggestion) => {
              const value = t(`suggestion_${suggestion}`)
              const selected = audienceValues.includes(value)
              return (
                <button
                  key={suggestion}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => toggleAudience(value)}
                  className={cn(
                    'flex min-h-9 items-center justify-between gap-1.5 rounded-full border px-2.5 py-1.5 text-start font-tajawal text-[10px] leading-4 transition-colors sm:px-3 sm:text-[11px]',
                    selected ? 'border-brand-primary bg-brand-weaker font-semibold text-brand-primary' : 'border-brand-accent/20 bg-white text-brand-headline/70 hover:border-brand-primary/50',
                  )}
                >
                  <span>{value}</span>
                  {selected && <Check className="h-3 w-3 shrink-0" aria-hidden="true" />}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
