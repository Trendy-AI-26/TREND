'use client'

import { useTranslations } from 'next-intl';
import { AUDIENCE_SEGMENTS } from '@/lib/generation-options'
import type { BriefFieldErrors } from '@/lib/validation'
import type { TargetAudienceBrief } from '@/types/generation'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

interface BriefAudienceStepProps {
    audience: TargetAudienceBrief
    onChange: (audience: TargetAudienceBrief) => void
    errors?: Pick<BriefFieldErrors, 'audience_segments'>
    disabled?: boolean
}

const LOCATION_SUGGESTION_KEYS = [
    'location_palestine',
    'location_jordan',
    'location_egypt',
    'location_saudi_arabia',
    'location_uae',
    'location_qatar',
    'location_lebanon',
    'location_syria',
    'location_iraq',
    'location_kuwait',
    'location_bahrain',
    'location_oman',
    'location_morocco',
    'location_algeria',
    'location_tunisia',
    'location_libya',
    'location_sudan',
    'location_yemen',
    'location_united_states',
    'location_united_kingdom',
    'location_turkey',
    'location_germany',
    'location_france',
] as const

const AGE_RANGES = [
    { value: 'Under 18', labelKey: 'age_under_18' },
    { value: '18–24', labelKey: 'age_18_24' },
    { value: '25–34', labelKey: 'age_25_34' },
    { value: '35–44', labelKey: 'age_35_44' },
    { value: '45–54', labelKey: 'age_45_54' },
    { value: '55+', labelKey: 'age_55_plus' },
] as const

const GENDER_OPTIONS = [
    { value: 'all', label: 'Everyone' },
    { value: 'women', label: 'Women' },
    { value: 'men', label: 'Men' },
]

export function BriefAudienceStep({
    audience,
    onChange,
    errors,
    disabled = false,
}: BriefAudienceStepProps) {
    const t = useTranslations('components.generation.brief-audience-step');
    const tOpt = useTranslations('options');
    const availableSegments = AUDIENCE_SEGMENTS.filter(
        (segment) => segment.value !== 'custom',
    )
       const hasReachedLimit = audience.segments.length >= 3

    function update(next: Partial<TargetAudienceBrief>) {
        onChange({ ...audience, ...next })
    }

    function toggleSegment(segment: string) {
        const selected = audience.segments.includes(segment)

        if (selected) {
            update({
                segments: audience.segments.filter((item) => item !== segment),
            })
            return
        }
        if (audience.segments.length >= 3) return


        update({
            segments: [...audience.segments, segment],
        })
    }

    return (
        <div className="space-y-4">
            <div>
                <Label>{t('who_is_the_target')}</Label>
                <p className="mt-1 text-[12px] text-muted-foreground">{t('select_up_to_two')}</p>
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
                {availableSegments.map((segment) => {
                    const selected = audience.segments.includes(segment.value)
                    const unavailable = hasReachedLimit && !selected

                    return (
                        <button
                            key={segment.value}
                            type="button"
                            aria-pressed={selected}
                            disabled={disabled || unavailable}
                            onClick={() => toggleSegment(segment.value)}
                            className={`rounded-lg border px-3 py-3 text-left text-[13px] transition-colors ${selected
                                ? 'border-brand bg-brand-weaker'
                                : unavailable
                                    ? 'cursor-not-allowed border-border bg-muted/40 opacity-50'
                                    : 'border-border bg-card hover:border-brand-border'
                                }`}
                        >
                            {tOpt(`audience_${segment.value}`)}
                        </button>
                    )
                })}
            </div>

            {errors?.audience_segments && (
                <p className="text-[12px] text-destructive" role="alert">
                    {errors.audience_segments}
                </p>
            )}

            {hasReachedLimit && !errors?.audience_segments && (
                <p className="text-[12px] text-muted-foreground">{t('you_can_select_up')}</p>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                    <Label htmlFor="audience-location">{t('location_optional')}</Label>
                    <Input
                        id="audience-location"
                        role="combobox"
                        list="audience-location-suggestions"
                        value={audience.location ?? ''}
                        onChange={(event) =>
                            update({ location: event.target.value || null })
                        }
                        disabled={disabled}
                        placeholder={t('eg_palestine_jordan_egypt')}
                    />
                    <datalist id="audience-location-suggestions">
                        {LOCATION_SUGGESTION_KEYS.map((key) => (
                            <option key={key} value={tOpt(key)} />
                        ))}
                    </datalist>
                </div>

                <div className="space-y-2">
                    <Label htmlFor="audience-age">{t('age_range_optional')}</Label>
                    <select
                        id="audience-age"
                        value={audience.age_range ?? ''}
                        onChange={(event) =>
                            update({ age_range: event.target.value || null })
                        }
                        disabled={disabled}
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:border-brand focus-visible:ring-2 focus-visible:ring-brand/20"
                    >
                        <option value="">{t('select_an_age_range')}</option>
                        {AGE_RANGES.map((range) => (
                            <option key={range.value} value={range.value}>
                                {tOpt(range.labelKey)}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="audience-gender">{t('gender_focus_optional')}</Label>
                <select
                    id="audience-gender"
                    value={audience.gender_focus ?? ''}
                    onChange={(event) =>
                        update({ gender_focus: event.target.value || null })
                    }
                    disabled={disabled}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:border-brand focus-visible:ring-2 focus-visible:ring-brand/20"
                >
                    <option value="">{t('no_specific_focus')}</option>
                    {GENDER_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                            {tOpt(`gender_${option.value}`)}
                        </option>
                    ))}
                </select>
            </div>

            <div className="space-y-2">
                <Label htmlFor="audience-details">{t('tell_us_more_about')}</Label>
                <Textarea
                    id="audience-details"
                    value={audience.details ?? ''}
                    onChange={(event) =>
                        update({ details: event.target.value || null })
                    }
                    disabled={disabled}
                    maxLength={500}
                    placeholder={t('share_context_needs_preferences')}
                    className="min-h-[110px]"
                />
                <p className="text-right font-mono text-[11px] text-muted-foreground">
                    {(audience.details ?? '').length} / 500
                </p>
            </div>
        </div>
    )
}
