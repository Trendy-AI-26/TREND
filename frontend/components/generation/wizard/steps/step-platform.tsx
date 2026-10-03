'use client'

import { useTranslations } from 'next-intl'
import { Textarea } from '@/components/ui/textarea'
import { ChipGroup, type ChipOption } from '../chip-group'
import { PlatformPicker } from '../platform-picker'
import { WizardField } from '../wizard-field'
import { WizardSwitch } from '../wizard-switch'
import {
    PLATFORM_NOTES_MAX,
    type PlatformErrors,
    type PlatformStepAnswers,
    type YesNo,
} from '../wizard-types'

const fieldClass =
    'rounded-[10px] border-brand-accent/25 bg-white text-[14px] text-brand-headline placeholder:text-brand-headline/40'

interface StepPlatformProps {
    value: PlatformStepAnswers
    onChange: (value: PlatformStepAnswers) => void
    errors: PlatformErrors
}

export function StepPlatform({ value, onChange, errors }: StepPlatformProps) {
    const t = useTranslations('components.generation.wizard')

    function patch(next: Partial<PlatformStepAnswers>) {
        onChange({ ...value, ...next })
    }

    const err = (key: keyof PlatformStepAnswers) => (errors[key] ? t(errors[key]) : undefined)

    const notesOptions: ChipOption<YesNo>[] = [
        { value: 'yes', label: t('yes') },
        { value: 'no', label: t('no') },
    ]

    return (
        <div className="space-y-[30px]">
            {/* 1. المنصة والمقاس */}
            <WizardField label={t('platform_label')} required hint={t('platform_hint')} error={err('preset')}>
                <PlatformPicker
                    ariaLabel={t('platform_label')}
                    value={value.preset}
                    onChange={(preset) => patch({ preset })}
                />
            </WizardField>

            {/* 2. الكابشن */}
            <WizardSwitch
                id="wizard-with-caption"
                label={t('caption_label')}
                description={t('caption_hint')}
                checked={value.withCaption}
                onChange={(withCaption: boolean) => patch({ withCaption })}
            />

            {/* 3. ملاحظات إضافية */}
            <WizardField
                label={t('notes_label')}
                error={err('notes')}
                counter={
                    value.hasNotes === 'yes'
                        ? t('char_counter', { count: value.notes.length, max: PLATFORM_NOTES_MAX })
                        : undefined
                }
            >
                <ChipGroup
                    ariaLabel={t('notes_label')}
                    options={notesOptions}
                    value={value.hasNotes}
                    onChange={(hasNotes) => patch({ hasNotes })}
                />
                {value.hasNotes === 'yes' && (
                    <Textarea
                        value={value.notes}
                        onChange={(e) => patch({ notes: e.target.value })}
                        maxLength={PLATFORM_NOTES_MAX}
                        rows={3}
                        placeholder={t('notes_placeholder')}
                        aria-label={t('notes_label')}
                        aria-invalid={Boolean(errors.notes)}
                        className={`${fieldClass} mt-3 min-h-[88px] resize-none px-4 py-3`}
                    />
                )}
            </WizardField>
        </div>
    )
}