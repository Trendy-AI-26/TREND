'use client'

import { useTranslations } from 'next-intl';
import type { LogoMode } from '@/types'
import { Eyebrow } from '@/components/ui/eyebrow'
import { Notice } from '@/components/ui/notice'
import { SegmentedControl } from '@/components/ui/segmented-control'
import Link from 'next/link'

interface LogoModeSelectorProps {
  value: LogoMode
  onChange: (value: LogoMode) => void
  brandHasLogo: boolean
  brandId?: string
  disabled?: boolean
}

export function LogoModeSelector({
  value, onChange, brandHasLogo, brandId, disabled,
}: LogoModeSelectorProps) {
  const t = useTranslations('components.generation.logo-mode-selector');
  const noLogoTitle = 'Upload a logo in Settings'

  return (
    <div className="flex flex-col gap-2">
      <Eyebrow>{t('logo')}</Eyebrow>
      <SegmentedControl
        aria-label={t('logo_mode')}
        value={value}
        onChange={onChange}
        disabled={disabled}
        options={[
          { value: 'none', label: t('none') },
          { value: 'prompt', label: t('in_prompt') },
          {
            value: 'watermark',
            label: t('mark'),
            disabled: !brandHasLogo,
            title: brandHasLogo ? undefined : noLogoTitle,
          },
          {
            value: 'both',
            label: t('both'),
            disabled: !brandHasLogo,
            title: brandHasLogo ? undefined : noLogoTitle,
          },
        ]}
      />
      {!brandHasLogo && (
        <Notice variant="info">
          Watermark modes need a brand logo. Add one in{' '}
          {brandId ? (
            <Link href={`/${brandId}/settings`} className="font-medium text-brand underline underline-offset-2">{t('settings')}</Link>
          ) : (
            <strong>{t('settings2')}</strong>
          )}
          .
        </Notice>
      )}
    </div>
  )
}
