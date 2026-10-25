'use client'

import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { Info } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { ChipGroup, type ChipOption } from '../chip-group'
import { ProductImageUpload } from '../product-image-upload'
import { WizardField } from '../wizard-field'
import {
  LIMITS,
  type Feeling,
  type LogoPlacement,
  type Occasion,
  type ProductPhotos,
  type StyleErrors,
  type StyleStepAnswers,
  type VisualStyle,
} from '../wizard-types'

const fieldClass =
  'rounded-[10px] border-brand-accent/25 bg-white text-[14px] text-brand-headline placeholder:text-brand-headline/40'

interface StepStyleProps {
  value: StyleStepAnswers
  onChange: (value: StyleStepAnswers) => void
  errors: StyleErrors
  brandId: string
  brandHasLogo: boolean
}

export function StepStyle({ value, onChange, errors, brandId, brandHasLogo }: StepStyleProps) {
  const t = useTranslations('components.generation.wizard')

  function patch(next: Partial<StyleStepAnswers>) {
    onChange({ ...value, ...next })
  }

  const err = (key: keyof StyleStepAnswers) => (errors[key] ? t(errors[key]) : undefined)

  const styleOptions: ChipOption<VisualStyle>[] = [
    { value: 'simple', label: t('style_simple') },
    { value: 'modern', label: t('style_modern') },
    { value: 'luxury', label: t('style_luxury') },
    { value: 'bold', label: t('style_bold') },
  ]

  const feelingOptions: ChipOption<Feeling>[] = [
    { value: 'trust', label: t('feeling_trust') },
    { value: 'excitement', label: t('feeling_excitement') },
    { value: 'comfort', label: t('feeling_comfort') },
    { value: 'curiosity', label: t('feeling_curiosity') },
  ]

  const logoOptions: ChipOption<LogoPlacement>[] = [
    { value: 'prominent', label: t('logo_prominent') },
    { value: 'corner', label: t('logo_corner') },
    { value: 'watermark', label: t('logo_watermark') },
    { value: 'auto', label: t('logo_auto') },
    { value: 'none', label: t('logo_none') },
  ]

  const photoOptions: ChipOption<ProductPhotos>[] = [
    { value: 'yes', label: t('photos_yes') },
    { value: 'yes_needs_edit', label: t('photos_yes_edit') },
    { value: 'no', label: t('photos_no') },
  ]

  const occasionOptions: ChipOption<Occasion>[] = [
    { value: 'none', label: t('occasion_none') },
    { value: 'ramadan', label: t('occasion_ramadan') },
    { value: 'eid', label: t('occasion_eid') },
    { value: 'national_day', label: t('occasion_national_day') },
    { value: 'white_friday', label: t('occasion_white_friday') },
    { value: 'year_end', label: t('occasion_year_end') },
    { value: 'seasonal_launch', label: t('occasion_seasonal_launch') },
    { value: 'other', label: t('occasion_other') },
  ]

  const showUpload = value.hasProductPhotos === 'yes' || value.hasProductPhotos === 'yes_needs_edit'

  return (
    <div className="space-y-[30px]">
      {/* 1. شكل المحتوى */}
      <WizardField label={t('style_label')} required error={err('visualStyle')}>
        <ChipGroup
          ariaLabel={t('style_label')}
          options={styleOptions}
          value={value.visualStyle}
          onChange={(visualStyle) => patch({ visualStyle })}
          invalid={Boolean(errors.visualStyle)}
        />
      </WizardField>

      {/* 2. الإحساس */}
      <WizardField label={t('feeling_label')} required error={err('feeling')}>
        <ChipGroup
          ariaLabel={t('feeling_label')}
          options={feelingOptions}
          value={value.feeling}
          onChange={(feeling) => patch({ feeling })}
          invalid={Boolean(errors.feeling)}
        />
      </WizardField>

      {/* 3. ظهور الشعار: إذا البراند ما عنده شعار نعرض تنبيه بدل الأسئلة */}
      <WizardField label={t('logo_label')} required={brandHasLogo} error={err('logoPlacement')}>
        {brandHasLogo ? (
          <ChipGroup
            ariaLabel={t('logo_label')}
            options={logoOptions}
            value={value.logoPlacement}
            onChange={(logoPlacement) => patch({ logoPlacement })}
            invalid={Boolean(errors.logoPlacement)}
          />
        ) : (
          <div className="flex items-start gap-2.5 rounded-[10px] border border-brand-accent/30 bg-brand-cream px-4 py-3 text-[12.5px] leading-[19px] text-brand-headline/70">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-brand-accent" />
            <p>
              {t('logo_missing')}{' '}
              <Link href={`/${brandId}/kit`} className="font-semibold text-brand-primary underline-offset-2 hover:underline">
                {t('logo_missing_link')}
              </Link>
            </p>
          </div>
        )}
      </WizardField>

      {/* 4. صور المنتج */}
      <WizardField label={t('photos_label')} required error={err('hasProductPhotos')}>
        <ChipGroup
          ariaLabel={t('photos_label')}
          options={photoOptions}
          value={value.hasProductPhotos}
          onChange={(hasProductPhotos) =>
            // إذا اختار "لا" نشيل الصورة المرفوعة
            patch({
              hasProductPhotos,
              productImage: hasProductPhotos === 'no' ? null : value.productImage,
            })
          }
          invalid={Boolean(errors.hasProductPhotos)}
        />

        {showUpload && (
          <div className="mt-4">
            <WizardField
              label={t('product_image_label')}
              optionalLabel={t('optional')}
              hint={t('product_image_hint')}
            >
              <ProductImageUpload
                file={value.productImage}
                onChange={(productImage) => patch({ productImage })}
              />
            </WizardField>
          </div>
        )}
      </WizardField>

      {/* 5. المناسبة (اختياري) */}
      <WizardField label={t('occasion_label')} hint={t('occasion_hint')} error={err('occasionCustom')}>
        <ChipGroup
          ariaLabel={t('occasion_label')}
          options={occasionOptions}
          value={value.occasion}
          onChange={(occasion) => patch({ occasion })}
        />
        {value.occasion === 'other' && (
          <Input
            value={value.occasionCustom}
            onChange={(e) => patch({ occasionCustom: e.target.value })}
            maxLength={LIMITS.custom}
            placeholder={t('occasion_other_placeholder')}
            aria-label={t('occasion_other_placeholder')}
            aria-invalid={Boolean(errors.occasionCustom)}
            className={`${fieldClass} mt-3 h-[44px] px-4`}
          />
        )}
      </WizardField>
    </div>
  )
}