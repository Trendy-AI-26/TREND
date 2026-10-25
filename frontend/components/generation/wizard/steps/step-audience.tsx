'use client'

import { useTranslations } from 'next-intl'
import { Input } from '@/components/ui/input'
import { ChipGroup, type ChipOption } from '../chip-group'
import { MultiChipGroup } from '../multi-chip-group'
import { WizardField } from '../wizard-field'
import {
  LIMITS,
  type AudienceErrors,
  type AudienceSegment,
  type AudienceStepAnswers,
  type ClientType,
  type GenderFocus,
  type LocationScope,
  type WizardAgeRange,
} from '../wizard-types'

const fieldClass =
  'rounded-[10px] border-brand-accent/25 bg-white text-[14px] text-brand-headline placeholder:text-brand-headline/40'

interface StepAudienceProps {
  value: AudienceStepAnswers
  onChange: (value: AudienceStepAnswers) => void
  errors: AudienceErrors
}

export function StepAudience({ value, onChange, errors }: StepAudienceProps) {
  const t = useTranslations('components.generation.wizard')

  function patch(next: Partial<AudienceStepAnswers>) {
    onChange({ ...value, ...next })
  }

  const err = (key: keyof AudienceStepAnswers) => (errors[key] ? t(errors[key]) : undefined)

  const segmentOptions: ChipOption<AudienceSegment>[] = [
    { value: 'individuals', label: t('segment_individuals') },
    { value: 'companies', label: t('segment_companies') },
    { value: 'students', label: t('segment_students') },
    { value: 'business_owners', label: t('segment_business_owners') },
    { value: 'other', label: t('segment_other') },
  ]

  const clientTypeOptions: ChipOption<ClientType>[] = [
    { value: 'b2c', label: t('client_b2c') },
    { value: 'b2b', label: t('client_b2b') },
    { value: 'both', label: t('client_both') },
  ]

  const ageOptions: ChipOption<WizardAgeRange>[] = [
    { value: 'under_18', label: t('age_under_18') },
    { value: '18_24', label: t('age_18_24') },
    { value: '25_34', label: t('age_25_34') },
    { value: '35_44', label: t('age_35_44') },
    { value: '45_plus', label: t('age_45_plus') },
  ]

  const genderOptions: ChipOption<GenderFocus>[] = [
    { value: 'men', label: t('gender_men') },
    { value: 'women', label: t('gender_women') },
    { value: 'all', label: t('gender_all') },
  ]

  const locationOptions: ChipOption<LocationScope>[] = [
    { value: 'local', label: t('location_local') },
    { value: 'country', label: t('location_country') },
    { value: 'arab_world', label: t('location_arab_world') },
    { value: 'global', label: t('location_global') },
  ]

  return (
    <div className="space-y-[30px]">
      {/* 1. شرائح الجمهور (اختيار متعدد) */}
      <WizardField
        label={t('audience_label')}
        required
        hint={t('audience_hint', { max: LIMITS.segments })}
        error={err('segments')}
      >
        <MultiChipGroup
          ariaLabel={t('audience_label')}
          options={segmentOptions}
          value={value.segments}
          onChange={(segments) => patch({ segments })}
          max={LIMITS.segments}
          invalid={Boolean(errors.segments)}
        />

        {value.segments.includes('other') && (
          <div className="mt-4">
            <WizardField
              label={t('segment_other_label')}
              htmlFor="wizard-segment-other"
              error={err('segmentOther')}
            >
              <Input
                id="wizard-segment-other"
                value={value.segmentOther}
                onChange={(e) => patch({ segmentOther: e.target.value })}
                maxLength={LIMITS.custom}
                placeholder={t('segment_other_placeholder')}
                aria-invalid={Boolean(errors.segmentOther)}
                className={`${fieldClass} h-[44px] px-4`}
              />
            </WizardField>
          </div>
        )}
      </WizardField>

      {/* 2. نوع العميل */}
      <WizardField
        label={t('client_type_label')}
        optionalLabel={t('optional')}
        hint={t('client_type_hint')}
        error={err('clientType')}
      >
        <ChipGroup
          ariaLabel={t('client_type_label')}
          options={clientTypeOptions}
          value={value.clientType}
          onChange={(clientType) => patch({ clientType })}
          invalid={Boolean(errors.clientType)}
        />
      </WizardField>

      {/* 3 + 4. العمر والجنس جنب بعض على الشاشات الكبيرة */}
      <div className="grid gap-[30px] sm:grid-cols-2 sm:gap-6">
        <WizardField label={t('age_label')} optionalLabel={t('optional')} error={err('ageRange')}>
          <ChipGroup
            ariaLabel={t('age_label')}
            options={ageOptions}
            value={value.ageRange}
            onChange={(ageRange) => patch({ ageRange })}
            invalid={Boolean(errors.ageRange)}
          />
        </WizardField>

        <WizardField label={t('gender_label')} optionalLabel={t('optional')} error={err('gender')}>
          <ChipGroup
            ariaLabel={t('gender_label')}
            options={genderOptions}
            value={value.gender}
            onChange={(gender) => patch({ gender })}
            invalid={Boolean(errors.gender)}
          />
        </WizardField>
      </div>

      {/* 5. الموقع الجغرافي */}
      <WizardField label={t('location_label')} optionalLabel={t('optional')} error={err('country')}>
        <ChipGroup
          ariaLabel={t('location_label')}
          options={locationOptions}
          value={value.location}
          onChange={(location) => patch({ location })}
          invalid={Boolean(errors.location)}
        />
        {value.location === 'country' && (
          <Input
            value={value.country}
            onChange={(e) => patch({ country: e.target.value })}
            maxLength={LIMITS.country}
            placeholder={t('country_placeholder')}
            aria-label={t('country_placeholder')}
            aria-invalid={Boolean(errors.country)}
            className={`${fieldClass} mt-3 h-[44px] px-4`}
          />
        )}
      </WizardField>
    </div>
  )
}
