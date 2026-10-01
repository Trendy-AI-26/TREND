'use client'

import { useLocale, useTranslations } from 'next-intl'
import { BriefcaseBusiness, Check, CheckCircle2, Coffee, Gem, Heart, House, Pencil, Shirt, Sparkles, Store, WandSparkles, Wrench, X, Zap } from 'lucide-react'
import { KitQuestion } from '@/components/kit/kit-question'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import type { KitAnswers } from '@/types'

const INDUSTRIES = [
    { value: 'beauty', label: 'beauty', icon: Sparkles },
    { value: 'fashion', label: 'fashion', icon: Shirt },
    { value: 'perfume', label: 'perfume', icon: Heart },
    { value: 'food', label: 'food', icon: Coffee },
    { value: 'retail', label: 'retail', icon: Store },
    { value: 'home', label: 'home', icon: House },
    { value: 'services', label: 'services', icon: Wrench },
    { value: 'jewelry', label: 'jewelry', icon: Gem },
    { value: 'other', label: 'other', icon: BriefcaseBusiness },
] as const

interface StepIndustryProps {
    answers: KitAnswers
    onChange: (partial: Partial<KitAnswers>) => void
}

export function StepIndustry({ answers, onChange }: StepIndustryProps) {
    const t = useTranslations('components.kit.steps.step-industry')
    const locale = useLocale()
    const fixedIndustry = INDUSTRIES.some(({ value }) => value === answers.industry)
    const otherSelected = answers.industry === 'other' || Boolean(answers.industry && !fixedIndustry)
    const otherValue = answers.industry && answers.industry !== 'other' && !fixedIndustry ? answers.industry : ''

    return (
        <div className="space-y-7">
            <KitQuestion
                align="center"
                before={t('question_before')}
                emphasis={t('question_emphasis')}
                after={t('question_after')}
                helper={t('helper')}
            />
            <div className="mx-auto grid w-full max-w-[760px] grid-cols-2 gap-3 sm:grid-cols-3">
                {INDUSTRIES.map(({ value, label, icon: Icon }) => {
                    const selected = value === 'other' ? otherSelected : answers.industry === value
                    return (
                        <button
                            key={value}
                            type="button"
                            aria-pressed={selected}
                            onClick={() => onChange({ industry: selected ? null : value })}
                            className={cn(
                                'flex min-h-[100px] flex-col items-center justify-center gap-3 rounded-lg border bg-white px-3 py-4 font-tajawal text-[13px] font-medium text-brand-headline transition-colors',
                                selected ? 'border-brand-primary bg-brand-weaker text-brand-primary' : 'border-brand-accent/20 hover:border-brand-primary/50',
                            )}
                        >
                            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-bg/45">
                                <Icon className="h-4 w-4" />
                            </span>
                            {t(label)}
                        </button>
                    )
                })}
            </div>
            {otherSelected && (
                <div className="mx-auto w-full max-w-[760px] space-y-4 rounded-2xl border border-brand-accent/20 bg-white p-3 shadow-xs sm:p-4">
                    <div dir="auto" className="flex items-center justify-between gap-3 px-1 py-1">
                        <label htmlFor="kit-industry-other" className="font-tajawal text-[13px] font-semibold text-brand-headline">{t('other_label')}</label>
                        <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-brand-primary/15 bg-brand-weaker px-2.5 py-1 font-tajawal text-[10px] font-medium text-brand-primary">
                            <WandSparkles className="h-3 w-3" aria-hidden="true" />
                            {t('ai_supported')}
                        </span>
                    </div>
                    <div className="relative">
                        <Input
                            id="kit-industry-other"
                            value={otherValue}
                            maxLength={120}
                            onChange={(event) => onChange({ industry: event.target.value || 'other' })}
                            placeholder={t('other_placeholder')}
                            autoFocus
                            dir="auto"
                            className="h-[58px] rounded-2xl border-2 border-brand-primary px-11 font-tajawal text-[15px] focus-visible:ring-0"
                        />
                        <Pencil className={`pointer-events-none absolute ${locale === 'ar' ? 'right-4' : 'left-4'} top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground`} aria-hidden="true" />
                        <button
                            type="button"
                            aria-label={t('clear_other')}
                            onClick={() => onChange({ industry: 'other' })}
                            className={`absolute ${locale === 'ar' ? 'left-3' : 'right-3'} top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full bg-brand-bg text-muted-foreground hover:bg-brand-bg/70`}
                        >
                            <X className="h-3.5 w-3.5" />
                        </button>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-2 px-1 font-tajawal text-[10px] text-muted-foreground">
                        <span>{t('other_hint')}</span>
                        {otherValue.trim().length >= 2 && (
                            <span className="inline-flex items-center gap-1 text-emerald-700">
                                <CheckCircle2 className="h-3 w-3" />{t('recognized')}
                            </span>
                        )}
                    </div>
                    {otherValue.trim().length >= 2 && (
                        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-brand-primary/10 bg-brand-weaker/60 px-4 py-3.5">
                            <div className="min-w-0">
                                <p className="font-tajawal text-[10px] text-muted-foreground">{t('selected_field')}</p>
                                <p className="mt-0.5 break-words font-el-messiri text-[17px] font-semibold text-brand-headline">{otherValue}</p>
                            </div>
                            <span className="inline-flex items-center gap-2 rounded-full border border-brand-primary/20 bg-white px-3 py-1.5 font-tajawal text-[11px] font-semibold text-brand-primary">
                                {t('ready_for_identity')}
                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-primary text-white"><Check className="h-3.5 w-3.5" /></span>
                            </span>
                        </div>
                    )}
                </div>
            )}
            {otherSelected && otherValue.trim().length >= 2 && (
                <p className="mx-auto flex w-full max-w-[760px] items-center gap-1.5 px-1 font-tajawal text-[11px] font-medium text-brand-primary">
                    <Zap className="h-3.5 w-3.5 fill-current" />{t('ready_next_step')}
                </p>
            )}
        </div>
    )
}