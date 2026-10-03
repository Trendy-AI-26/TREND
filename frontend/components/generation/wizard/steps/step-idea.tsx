'use client'

import { useTranslations } from 'next-intl'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ChipGroup, type ChipOption } from '../chip-group'
import { WizardField } from '../wizard-field'
import {
  LIMITS,
  type CallToAction,
  type DesignTextLanguage,
  type IdeaErrors,
  type IdeaStepAnswers,
  type Offering,
  type WizardGoal,
} from '../wizard-types'

const fieldClass =
  'rounded-[10px] border-brand-accent/25 bg-white text-[14px] text-brand-headline placeholder:text-brand-headline/40'

interface StepIdeaProps {
  value: IdeaStepAnswers
  onChange: (value: IdeaStepAnswers) => void
  errors: IdeaErrors
}

export function StepIdea({ value, onChange, errors }: StepIdeaProps) {
  const t = useTranslations('components.generation.wizard')

  // نغيّر حقل واحد ونحتفظ بالباقي كما هو
  function patch(next: Partial<IdeaStepAnswers>) {
    onChange({ ...value, ...next })
  }

  // نترجم مفتاح الخطأ إذا موجود
  const err = (key: keyof IdeaStepAnswers) => (errors[key] ? t(errors[key]) : undefined)

  const offeringOptions: ChipOption<Offering>[] = [
    { value: 'personal_project', label: t('offering_personal_project') },
    { value: 'product', label: t('offering_product') },
    { value: 'service', label: t('offering_service') },
    { value: 'other', label: t('offering_other') },
  ]

  const goalOptions: ChipOption<WizardGoal>[] = [
    { value: 'engagement', label: t('goal_engagement') },
    { value: 'brand_awareness', label: t('goal_brand_awareness') },
    { value: 'product_launch', label: t('goal_product_launch') },
    { value: 'sales_conversion', label: t('goal_sales_conversion') },
    { value: 'custom', label: t('goal_custom') },
  ]

  const ctaOptions: ChipOption<CallToAction>[] = [
    { value: 'shop_now', label: t('cta_shop_now') },
    { value: 'order_now', label: t('cta_order_now') },
    { value: 'book_now', label: t('cta_book_now') },
    { value: 'contact_us', label: t('cta_contact_us') },
    { value: 'sign_up', label: t('cta_sign_up') },
    { value: 'learn_more', label: t('cta_learn_more') },
    { value: 'none', label: t('cta_none') },
    { value: 'other', label: t('cta_other') },
  ]

  const languageOptions: ChipOption<DesignTextLanguage>[] = [
    { value: 'ar', label: t('lang_ar') },
    { value: 'en', label: t('lang_en') },
    { value: 'both', label: t('lang_both') },
    { value: 'auto', label: t('lang_auto') },
  ]

  return (
    <div className="space-y-[30px]">
      {/* 1. الفكرة الأساسية */}
      <WizardField
        label={t('idea_label')}
        htmlFor="wizard-core-idea"
        required
        hint={t('idea_hint')}
        error={err('coreIdea')}
        counter={t('char_counter', { count: value.coreIdea.length, max: LIMITS.coreIdea })}
      >
        <Textarea
          id="wizard-core-idea"
          value={value.coreIdea}
          onChange={(e) => patch({ coreIdea: e.target.value })}
          maxLength={LIMITS.coreIdea}
          rows={5}
          placeholder={t('idea_placeholder')}
          aria-invalid={Boolean(errors.coreIdea)}
          className={`${fieldClass} min-h-[156px] resize-none px-4 py-4 leading-[25px]`}
        />
      </WizardField>

      {/* 2. ماذا تقدم؟ */}
      <WizardField label={t('offering_label')} required error={err('offering')}>
        <ChipGroup
          ariaLabel={t('offering_label')}
          options={offeringOptions}
          value={value.offering}
          onChange={(offering) => patch({ offering })}
          invalid={Boolean(errors.offering)}
        />
      </WizardField>

      {/* 3. هدف المنشور */}
      <WizardField label={t('goal_label')} required error={err('goal') ?? err('goalCustom')}>
        <ChipGroup
          ariaLabel={t('goal_label')}
          options={goalOptions}
          value={value.goal}
          onChange={(goal) => patch({ goal })}
          invalid={Boolean(errors.goal)}
        />
        {value.goal === 'custom' && (
          <Input
            value={value.goalCustom}
            onChange={(e) => patch({ goalCustom: e.target.value })}
            maxLength={LIMITS.custom}
            placeholder={t('goal_custom_placeholder')}
            aria-label={t('goal_custom_placeholder')}
            aria-invalid={Boolean(errors.goalCustom)}
            className={`${fieldClass} mt-3 h-[44px] px-4`}
          />
        )}
      </WizardField>

      {/* 4. نص يظهر في الصورة (اختياري) */}
      <WizardField
        label={t('text_in_image_label')}
        htmlFor="wizard-text-in-image"
        optionalLabel={t('optional')}
        counter={t('char_counter', { count: value.textInImage.length, max: LIMITS.textInImage })}
      >
        <Input
          id="wizard-text-in-image"
          value={value.textInImage}
          onChange={(e) => patch({ textInImage: e.target.value })}
          maxLength={LIMITS.textInImage}
          placeholder={t('text_in_image_placeholder')}
          className={`${fieldClass} h-[44px] px-4`}
        />
      </WizardField>

      {/* 5. الدعوة لاتخاذ إجراء */}
      <WizardField label={t('cta_label')} required error={err('cta') ?? err('ctaCustom')}>
        <ChipGroup
          ariaLabel={t('cta_label')}
          options={ctaOptions}
          value={value.cta}
          onChange={(cta) => patch({ cta })}
          invalid={Boolean(errors.cta)}
        />
        {value.cta === 'other' && (
          <Input
            value={value.ctaCustom}
            onChange={(e) => patch({ ctaCustom: e.target.value })}
            maxLength={LIMITS.custom}
            placeholder={t('cta_custom_placeholder')}
            aria-label={t('cta_custom_placeholder')}
            aria-invalid={Boolean(errors.ctaCustom)}
            className={`${fieldClass} mt-3 h-[44px] px-4`}
          />
        )}
      </WizardField>

      {/* 6. لغة النص بالتصميم */}
      <WizardField
        label={t('text_language_label')}
        required
        hint={t('text_language_hint')}
        error={err('textLanguage')}
      >
        <ChipGroup
          ariaLabel={t('text_language_label')}
          options={languageOptions}
          value={value.textLanguage}
          onChange={(textLanguage) => patch({ textLanguage })}
          invalid={Boolean(errors.textLanguage)}
        />
      </WizardField>
    </div>
  )
}