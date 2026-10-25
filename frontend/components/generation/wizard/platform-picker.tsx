'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Check, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PLATFORM_PRESETS, aspectRatioLabel } from '@/lib/presets'
import type { PlatformPreset } from '@/types'

// المنصات اللي بتظهر أول شي، والباقي ورا زر "عرض المزيد"
const FEATURED: PlatformPreset[] = [
  'instagram_post',
  'instagram_reel_cover',
  'instagram_story',
  'facebook_post',
]

const ALL: PlatformPreset[] = [
  ...FEATURED,
  'facebook_cover',
  'facebook_story',
  'twitter_post',
  'twitter_header',
  'linkedin_post',
  'linkedin_banner',
  'tiktok_video_cover',
  'youtube_thumbnail',
  'youtube_banner',
]

// اسم المنصة وشارتها الصغيرة الملونة
const PLATFORM_BADGES = {
  instagram: { name: 'Instagram', short: 'IG', className: 'bg-[#E1306C] text-white' },
  facebook: { name: 'Facebook', short: 'f', className: 'bg-[#1877F2] text-white' },
  twitter: { name: 'Twitter/X', short: 'X', className: 'bg-brand-headline text-white' },
  linkedin: { name: 'LinkedIn', short: 'in', className: 'bg-[#0A66C2] text-white' },
  tiktok: { name: 'TikTok', short: 'TT', className: 'bg-brand-headline text-white' },
  youtube: { name: 'YouTube', short: 'YT', className: 'bg-[#FF0000] text-white' },
} as const

type PlatformKey = keyof typeof PLATFORM_BADGES

// "instagram_post" ← "instagram"
function platformOf(preset: PlatformPreset): PlatformKey {
  return preset.split('_')[0] as PlatformKey
}

interface PlatformPickerProps {
  value: PlatformPreset | ''
  onChange: (value: PlatformPreset) => void
  ariaLabel: string
}

export function PlatformPicker({ value, onChange, ariaLabel }: PlatformPickerProps) {
  const t = useTranslations('components.generation.wizard')
  const tOpt = useTranslations('options')

  // إذا المختار من المنصات المخفية، نفتح القائمة كاملة من البداية
  const [expanded, setExpanded] = useState(
    value !== '' && !FEATURED.includes(value),
  )
  const visible = expanded ? ALL : FEATURED
  const hiddenCount = ALL.length - FEATURED.length

  return (
    <div>
      <div role="radiogroup" aria-label={ariaLabel} className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {visible.map((preset) => {
          const info = PLATFORM_PRESETS[preset]
          const badge = PLATFORM_BADGES[platformOf(preset)]
          const selected = preset === value

          // نرسم مستطيل صغير بنفس نسبة أبعاد المقاس
          const scale = Math.min(28 / info.width, 22 / info.height)
          const shapeWidth = Math.max(6, Math.round(info.width * scale))
          const shapeHeight = Math.max(6, Math.round(info.height * scale))

          return (
            <button
              key={preset}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(preset)}
              className={cn(
                'relative flex flex-col items-center rounded-[10px] border px-2 pb-2.5 pt-3 text-center transition-colors',
                selected
                  ? 'border-brand-primary bg-brand-primary/5'
                  : 'border-brand-accent/25 bg-white hover:border-brand-accent/50 hover:bg-brand-cream',
              )}
            >
              {selected && (
                <span className="absolute start-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-brand-primary text-white">
                  <Check className="h-2.5 w-2.5" strokeWidth={3} />
                </span>
              )}

              <span
                aria-hidden="true"
                className={cn(
                  'flex h-[18px] min-w-[18px] items-center justify-center rounded-[4px] px-1 text-[8.5px] font-bold leading-none',
                  badge.className,
                )}
              >
                {badge.short}
              </span>

              <span className="mt-2 flex h-[22px] items-center justify-center" aria-hidden="true">
                <span
                  className={cn('rounded-[2px]', selected ? 'bg-brand-primary' : 'bg-brand-headline/15')}
                  style={{ width: shapeWidth, height: shapeHeight }}
                />
              </span>

              <span
                className={cn(
                  'mt-2 text-[12.5px] leading-[18px]',
                  selected ? 'font-bold text-brand-primary' : 'font-semibold text-brand-headline',
                )}
              >
                {tOpt(`preset_short_${info.shortLabelKey}`)}
              </span>
              <span className="text-[10.5px] leading-[15px] text-brand-headline/40">{badge.name}</span>
              <span dir="ltr" className="text-[10px] leading-[14px] text-brand-headline/40">
                {aspectRatioLabel(info.width, info.height)}
              </span>
            </button>
          )
        })}
      </div>

      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        aria-expanded={expanded}
        className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-[10px] border border-brand-accent/25 bg-white py-2 text-[12.5px] font-medium text-brand-headline/70 transition-colors hover:bg-brand-cream"
      >
        <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', expanded && 'rotate-180')} />
        {expanded ? t('platforms_show_less') : t('platforms_show_more', { count: hiddenCount })}
      </button>
    </div>
  )
}