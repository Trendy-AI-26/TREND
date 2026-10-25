

'use client'

import { useTranslations } from 'next-intl';
import { useEffect, useState } from 'react'                          //  added useEffect
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { BriefCreativePreview } from '@/components/generation/brief-creative-preview'
import { usePreviewBrief } from '@/hooks/use-preview-brief'
import type { PlatformPreset } from '@/types'
import { BriefAudienceStep } from '@/components/generation/brief-audience-step'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { validateGenerationBrief } from '@/lib/validation'
import type { BriefFieldErrors } from '@/lib/validation'
import type {
    CampaignGoal,
    ContentType,
    GenerationBrief,
    VoiceTone,
} from '@/types'

export const EMPTY_GENERATION_BRIEF: GenerationBrief = {
    campaign_goal: '',
    campaign_goal_custom: null,
    content_type: '',
    content_type_custom: null,
    target_audience: {
        segments: [],
        location: null,
        age_range: null,
        gender_focus: null,
        details: null,
    },
    core_idea: '',
    voice_tone: '',
    voice_tone_custom: null,
    optional_notes: null,
    text_to_include: null,
}

export function isGenerationBriefComplete(brief: GenerationBrief) {
    return Object.keys(validateGenerationBrief(brief)).length === 0
}

interface GenerationBriefFormProps {
    value: GenerationBrief
    onChange: (value: GenerationBrief) => void
    onComplete: (brief: GenerationBrief) => void
    platformPreset: PlatformPreset
    brandId: string
    brandName: string
    disabled?: boolean
}


const goals: { value: CampaignGoal; label: string }[] = [
    { value: 'brand_awareness', label: 'Increase brand awareness' },
    { value: 'product_launch', label: 'Launch a product or service' },
    { value: 'product_showcase', label: 'Showcase a product or service' },
    { value: 'promotion_offer', label: 'Promote an offer or discount' },
    { value: 'sales_conversion', label: 'Increase sales' },
    { value: 'engagement', label: 'Increase engagement' },
    { value: 'education', label: 'Educate the audience' },
    { value: 'custom', label: 'Other goal' },
]

const contentTypes: { value: ContentType; label: string }[] = [
    { value: 'product_showcase', label: 'Product showcase' },
    { value: 'service_showcase', label: 'Service showcase' },
    { value: 'promotional_ad', label: 'Promotional ad' },
    { value: 'educational', label: 'Educational content' },
    { value: 'testimonial', label: 'Customer testimonial' },
    { value: 'brand_story', label: 'Brand story' },
    { value: 'event_promo', label: 'Event promotion' },
    { value: 'infographic', label: 'Infographic or visual explanation' },
    { value: 'custom', label: 'Other content type' },
]

const tones: { value: VoiceTone; label: string }[] = [
    { value: 'friendly', label: 'Friendly' },
    { value: 'professional', label: 'Professional' },
    { value: 'playful', label: 'Playful' },
    { value: 'bold', label: 'Bold' },
    { value: 'elegant', label: 'Elegant and premium' },
    { value: 'warm', label: 'Warm and human' },
    { value: 'educational', label: 'Educational and clear' },
    { value: 'inspirational', label: 'Inspirational' },
    { value: 'minimal', label: 'Calm and minimal' },
    { value: 'trustworthy', label: 'Trustworthy' },
    { value: 'custom', label: 'Other tone' },
]

export function GenerationBriefForm({
    value,
    onChange,
    onComplete,
    platformPreset,
    brandId,
    brandName,
    disabled = false,
}: GenerationBriefFormProps) {
  const t = useTranslations('components.generation.generation-brief-form');
  const tOpt = useTranslations('options');

    const [step, setStep] = useState(0)
    const [hasAttemptedNext, setHasAttemptedNext] = useState(false)
    const steps = ['Goal', 'Type', 'Audience', 'Idea', 'Style & notes', 'Summary']
    const audience = value.target_audience
    const allErrors = validateGenerationBrief(value)

    // call usePreviewBrief hook at TOP LEVEL (not inside any function)
    const { preview, loading, error, fetchPreview, retryPreview } = usePreviewBrief(brandId)

    const briefSerialized = JSON.stringify(value)

    // useEffect at TOP LEVEL — fetches preview when user reaches Summary (step 5)
    useEffect(() => {
        if (step === 5 && platformPreset && isGenerationBriefComplete(value)) {
            fetchPreview(value, platformPreset)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [step, platformPreset, briefSerialized, fetchPreview])

    const errors: BriefFieldErrors = hasAttemptedNext ? allErrors : {}

    function patch(next: Partial<GenerationBrief>) {
        onChange({ ...value, ...next })
    }

    // restored clean getCurrentStepErrors() without useEffect inside it
    function getCurrentStepErrors(): BriefFieldErrors {
        if (step === 0) {
            return {
                campaign_goal: allErrors.campaign_goal,
                campaign_goal_custom: allErrors.campaign_goal_custom,
            }
        }

        if (step === 1) {
            return {
                content_type: allErrors.content_type,
                content_type_custom: allErrors.content_type_custom,
            }
        }

        if (step === 2) {
            return {
                audience_segments: allErrors.audience_segments,
            }
        }

        if (step === 3) {
            return {
                core_idea: allErrors.core_idea,
            }
        }

        if (step === 4) {
            return {
                voice_tone: allErrors.voice_tone,
                voice_tone_custom: allErrors.voice_tone_custom,
                optional_notes: allErrors.optional_notes,
                text_to_include: allErrors.text_to_include,
            }
        }

        return {}   // step 5 (Summary) has no validation errors to check
    }

    function nextStep() {
        const stepErrors = getCurrentStepErrors()
        const hasErrors = Object.values(stepErrors).some(Boolean)

        if (hasErrors) {
            setHasAttemptedNext(true)
            return
        }

        setHasAttemptedNext(false)
        setStep((current) => Math.min(steps.length - 1, current + 1))
    }

    function previousStep() {
        setHasAttemptedNext(false)
        setStep((current) => Math.max(0, current - 1))
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between gap-2">
                <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-brand-accent">{t('structured_brief')}</p>
                    <p className="mt-1 text-[13px] text-muted-foreground">{t('answer_a_few_questions')}</p>
                </div>
                <span className="font-mono text-[11px] text-muted-foreground">
                    {step + 1}/{steps.length}
                </span>
            </div>

            <div className="grid grid-cols-6 gap-1" aria-label={t('generation_brief_progress')}>
                {steps.map((label, index) => (
                    <button
                        key={label}
                        type="button"
                        onClick={() => {
                            if (index <= step) {
                                setHasAttemptedNext(false)
                                setStep(index)
                            }
                        }}
                        disabled={disabled || index > step}
                        aria-label={label}
                        className={`h-1.5 rounded-full transition-colors ${index <= step ? 'bg-brand' : 'bg-border'
                            }`}
                    />
                ))}
            </div>

            {step === 0 && (
                <div className="space-y-3">
                    <ChoiceStep
                        label={t('what_is_the_campaign')}
                        value={value.campaign_goal}
                        options={goals.map((g) => ({ ...g, label: tOpt(`goal_${g.value}`) }))}
                        onChange={(next) =>
                            patch({
                                campaign_goal: next as CampaignGoal,
                                campaign_goal_custom: next === 'custom' ? value.campaign_goal_custom : null,
                            })
                        }
                        error={errors.campaign_goal}
                        disabled={disabled}
                    />

                    {value.campaign_goal === 'custom' && (
                        <TextField
                            label={t('describe_your_campaign_goal')}
                            value={value.campaign_goal_custom ?? ''}
                            onChange={(next) => patch({ campaign_goal_custom: next })}
                            error={errors.campaign_goal_custom}
                            disabled={disabled}
                        />
                    )}
                </div>
            )}

            {step === 1 && (
                <div className="space-y-3">
                    <ChoiceStep
                        label={t('what_do_you_want')}
                        value={value.content_type}
                        options={contentTypes.map((c) => ({ ...c, label: tOpt(`content_type_${c.value}`) }))}
                        onChange={(next) =>
                            patch({
                                content_type: next as ContentType,
                                content_type_custom: next === 'custom' ? value.content_type_custom : null,
                            })
                        }
                        error={errors.content_type}
                        disabled={disabled}
                    />

                    {value.content_type === 'custom' && (
                        <TextField
                            label={t('describe_your_content_type')}
                            value={value.content_type_custom ?? ''}
                            onChange={(next) => patch({ content_type_custom: next })}
                            error={errors.content_type_custom}
                            disabled={disabled}
                        />
                    )}
                </div>
            )}

            {step === 2 && (
                <BriefAudienceStep
                    audience={audience}
                    onChange={(target_audience) => patch({ target_audience })}
                    errors={{ audience_segments: errors.audience_segments }}
                    disabled={disabled}
                />
            )}

            {step === 3 && (
                <div className="space-y-2">
                    <Label htmlFor="brief-core-idea">{t('what_is_the_main')}</Label>
                    <p className="text-[12px] text-muted-foreground">{t('write_naturally_you_do')}</p>
                    <Textarea
                        id="brief-core-idea"
                        value={value.core_idea}
                        onChange={(event) => patch({ core_idea: event.target.value })}
                        disabled={disabled}
                        maxLength={1000}
                        placeholder={t('eg_show_how_our')}
                        className="min-h-[130px]"
                    />
                    <div className="flex items-center justify-between text-[11px]">
                        <span className={errors.core_idea ? 'text-destructive' : 'text-muted-foreground'}>
                            {errors.core_idea ?? 'Keep your idea clear and focused.'}
                        </span>
                        <span className="font-mono text-muted-foreground">
                            {value.core_idea.length} / 1000
                        </span>
                    </div>
                </div>
            )}

            {step === 4 && (
                <div className="space-y-4">
                    <ChoiceStep
                        label={t('how_should_the_content')}
                        value={value.voice_tone}
                        options={tones.map((tn) => ({ ...tn, label: tOpt(`tone_${tn.value}`) }))}
                        onChange={(next) =>
                            patch({
                                voice_tone: next as VoiceTone,
                                voice_tone_custom: next === 'custom' ? value.voice_tone_custom : null,
                            })
                        }
                        error={errors.voice_tone}
                        disabled={disabled}
                    />

                    {value.voice_tone === 'custom' && (
                        <TextField
                            label={t('describe_your_tone')}
                            value={value.voice_tone_custom ?? ''}
                            onChange={(next) => patch({ voice_tone_custom: next })}
                            error={errors.voice_tone_custom}
                            disabled={disabled}
                        />
                    )}

                    <div className="border-t border-border-subtle pt-3">
                        <Label htmlFor="brief-notes">{t('additional_notes_optional')}</Label>
                        <Textarea
                            id="brief-notes"
                            value={value.optional_notes ?? ''}
                            onChange={(event) =>
                                patch({ optional_notes: event.target.value || null })
                            }
                            disabled={disabled}
                            maxLength={2000}
                            placeholder={t('add_visual_direction_things')}
                            className="mt-2 min-h-[90px]"
                        />
                        <div className="flex items-center justify-between text-[11px]">
                            <span className="text-destructive">{errors.optional_notes ?? ''}</span>
                            <span className="font-mono text-muted-foreground">
                                {(value.optional_notes ?? '').length} / 2000
                            </span>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="brief-text">{t('text_to_include_in')}</Label>
                        <Input
                            id="brief-text"
                            value={value.text_to_include ?? ''}
                            onChange={(event) =>
                                patch({ text_to_include: event.target.value || null })
                            }
                            disabled={disabled}
                            maxLength={500}
                            placeholder={t('eg_20_off_this')}
                        />
                        {errors.text_to_include && (
                            <p className="text-[12px] text-destructive" role="alert">
                                {errors.text_to_include}
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* Step 5 renders a single canonical BriefCreativePreview with inline edit affordances */}
            {step === 5 && (
                <BriefCreativePreview
                    preview={preview}
                    loading={loading}
                        error={error}
                        brandName={brandName}
                        retryPreview={retryPreview}
                        onEdit={(targetStep) => {
                        setHasAttemptedNext(false)
                        setStep(targetStep)
                    }}
                />
            )}

            <div className="flex items-center justify-between border-t border-border-subtle pt-3">
                <Button
                    type="button"
                    variant="ghost"
                    onClick={previousStep}
                    disabled={disabled || step === 0}
                >
                    <ArrowLeft className="h-4 w-4" />{t('back')}</Button>

                {step < steps.length - 1 ? (
                    <Button type="button" onClick={nextStep} disabled={disabled}>{t('next')}<ArrowRight className="h-4 w-4" />
                    </Button>
                ) : (
                    <Button
                        type="button"
                        onClick={() => onComplete(value)}
                        disabled={disabled || !isGenerationBriefComplete(value)}
                    >
                        <Check className="h-4 w-4" />{t('ready_to_generate')}</Button>

                )}
            </div>
        </div>
    )
}

function ChoiceStep({
    label,
    value,
    options,
    onChange,
    error,
    disabled,
}: {
    label: string
    value: string
    options: { value: string; label: string }[]
    onChange: (value: string) => void
    error?: string
    disabled?: boolean
}) {
    return (
        <div className="space-y-2">
            <Label>{label}</Label>
            <div className="grid gap-2 sm:grid-cols-2">
                {options.map((option) => (
                    <button
                        key={option.value}
                        type="button"
                        disabled={disabled}
                        aria-pressed={value === option.value}
                        onClick={() => onChange(option.value)}
                        className={`rounded-lg border px-3 py-3 text-left text-[13px] transition-colors ${value === option.value
                            ? 'border-brand bg-brand-weaker'
                            : 'border-border bg-card hover:border-brand-border'
                            }`}
                    >
                        {option.label}
                    </button>
                ))}
            </div>
            {error && (
                <p className="text-[12px] text-destructive" role="alert">
                    {error}
                </p>
            )}
        </div>
    )
}

function TextField({
    label,
    value,
    onChange,
    error,
    disabled,
}: {
    label: string
    value: string
    onChange: (value: string) => void
    error?: string
    disabled?: boolean
}) {
    return (
        <div className="space-y-2">
            <Label>{label}</Label>
            <Input
                value={value}
                onChange={(event) => onChange(event.target.value)}
                disabled={disabled}
            />
            {error && (
                <p className="text-[12px] text-destructive" role="alert">
                    {error}
                </p>
            )}
        </div>
    )
}

