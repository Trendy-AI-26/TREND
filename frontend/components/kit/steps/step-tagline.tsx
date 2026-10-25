'use client'

import { useTranslations } from 'next-intl';
import { KitQuestion } from '@/components/kit/kit-question'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { KitAnswers } from '@/types'

interface StepProps {
  answers: KitAnswers
  onChange: (partial: Partial<KitAnswers>) => void
  brandName: string
}

export function StepTagline({ answers, onChange, brandName }: StepProps) {
  const t = useTranslations('components.kit.steps.step-tagline');
  const examples = [
    t('example_seen_clearly', { brandName }),
    t('example_made_to_be_remembered'),
    t('example_quietly_distinctive'),
  ]

  return (
    <div className="space-y-7">
      <KitQuestion
        align="center"
        before={t('whats_prefix')}
        emphasis={brandName}
        after={t('tagline_suffix')}
        helper={t('tagline_help')}
      />
      <div className="mx-auto w-full max-w-[760px] space-y-4 rounded-xl border border-brand-accent/15 bg-white p-5 sm:p-7">
        <div className="space-y-2">
          <Label htmlFor="kit-tagline" className="font-tajawal text-[13px]">{t('tagline')}</Label>
          <Input
            id="kit-tagline"
            type="text"
            value={answers.tagline ?? ''}
            maxLength={160}
            onChange={(e) => onChange({ tagline: e.target.value || null })}
            placeholder={t('enter_a_tagline')}
            className="font-tajawal text-[13px]"
          />
          <p className="text-[12px] text-muted-foreground">
            {answers.tagline?.length ?? 0}/160
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {examples.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => onChange({ tagline: example })}
              className={cn(
                'rounded-full border px-3 py-1.5 font-tajawal text-[12px] transition-colors duration-fast',
                answers.tagline === example
                  ? 'border-brand bg-brand-weak text-foreground'
                  : 'border-border hover:border-brand-border',
              )}
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
