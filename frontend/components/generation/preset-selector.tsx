'use client'

import { useTranslations } from 'next-intl';
import { PresetFrame } from '@/components/generation/preset-frame'
import { Eyebrow } from '@/components/ui/eyebrow'
import { PLATFORM_PRESETS, PRESETS_BY_PLATFORM } from '@/lib/presets'
import type { PlatformPreset } from '@/types'

interface PresetSelectorProps {
  value: PlatformPreset
  onChange: (value: PlatformPreset) => void
  disabled?: boolean
}

export function PresetSelector({ value, onChange, disabled }: PresetSelectorProps) {
  const t = useTranslations('components.generation.preset-selector');
  return (
    <div className="flex flex-col gap-2">
      <Eyebrow>{t('platform2')}</Eyebrow>
      <div role="radiogroup" aria-label={t('platform')} className="flex flex-wrap gap-2">
        {Object.entries(PRESETS_BY_PLATFORM).flatMap(([platform, presets]) =>
          presets.map((presetId) => (
            <PresetFrame
              key={presetId}
              preset={PLATFORM_PRESETS[presetId]}
              platform={platform}
              selected={value === presetId}
              disabled={disabled}
              onSelect={() => onChange(presetId)}
            />
          )),
        )}
      </div>
    </div>
  )
}
