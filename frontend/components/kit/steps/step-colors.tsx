'use client'

import { useTranslations } from 'next-intl';
import { Check, Sparkles } from 'lucide-react'
import { BrandDot } from '@/components/brand/brand-dot'
import { BrandWorkspace, TRENDY_AI_ACCENT, formatHex, normalizeHex, onBrandTextColor } from '@/components/brand/brand-workspace'
import { ColorSlot } from '@/components/kit/color-slot'
import { KitQuestion } from '@/components/kit/kit-question'
import { Button } from '@/components/ui/button'
import { KitAnswers } from '@/types'

interface StepProps {
  answers: KitAnswers
  onChange: (partial: Partial<KitAnswers>) => void
  brandName: string
}

// الألوان المقترحة مع اسم كل لون (متل الفيجما)، بس كمربعات بدل مستطيلات
const CURATED: { hex: string; nameKey: string }[] = [
  { hex: '#7A1521', nameKey: 'color_maroon' },
  { hex: '#DB2777', nameKey: 'color_pink' },
  { hex: '#7C3AED', nameKey: 'color_purple' },
  { hex: '#2563EB', nameKey: 'color_blue' },
  { hex: '#0F172A', nameKey: 'color_navy' },
  { hex: '#0891B2', nameKey: 'color_cyan' },
  { hex: '#57534E', nameKey: 'color_gray' },
  { hex: '#0369A1', nameKey: 'color_sky' },
  { hex: '#16A34A', nameKey: 'color_green' },
  { hex: '#CA8A04', nameKey: 'color_gold' },
  { hex: '#EA580C', nameKey: 'color_orange' },
  { hex: '#DC2626', nameKey: 'color_red' },
]

export function StepColors({ answers, onChange }: StepProps) {
  const t = useTranslations('components.kit.steps.step-colors');
  const colors = answers.colors
  const primary = colors[0] && normalizeHex(colors[0]) ? formatHex(colors[0]) : TRENDY_AI_ACCENT

  const handleColorChange = (index: number, hex: string) => {
    const updated = [...colors]
    updated[index] = hex
    onChange({ colors: updated })
  }

  const handleColorRemove = (index: number) => {
    if (colors.length <= 1) return
    onChange({ colors: colors.filter((_, i) => i !== index) })
  }

  const handleAddColor = (hex = '#334155') => {
    if (colors.length >= 3) return
    if (colors.some((c) => normalizeHex(c) === normalizeHex(hex))) return
    onChange({ colors: [...colors, hex] })
  }

  const handleMakePrimary = (index: number) => {
    if (index === 0) return
    const next = [...colors]
    const [picked] = next.splice(index, 1)
    next.unshift(picked)
    onChange({ colors: next })
  }

  return (
    <div className="space-y-6">
      <KitQuestion
        before={t('your_prefix')}
        emphasis={t('colors_word')}
        after="."
        helper={t('colors_help')}
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_244px]">
        <div className="space-y-2">
          {colors.map((color, index) => (
            <ColorSlot
              key={index}
              value={color}
              isPrimary={index === 0}
              canRemove={colors.length > 1}
              onChange={(hex) => handleColorChange(index, hex)}
              onRemove={() => handleColorRemove(index)}
              onMakePrimary={() => handleMakePrimary(index)}
            />
          ))}
          {colors.length === 0 && (
            <p className="text-[13px] text-muted-foreground">{t('add_a_color_to')}</p>
          )}
          <button
            type="button"
            onClick={() => handleAddColor()}
            disabled={colors.length >= 3}
            className="mt-2 w-full rounded-md border border-dashed border-border px-3 py-2 text-[13px] text-muted-foreground hover:border-brand hover:text-brand disabled:opacity-50"
          >
            {t('add_color')}
          </button>
          
          <p className="text-[12px] font-medium text-brand-headline/60">{t('curated_palette')}</p>
          <div className="grid max-w-[404px] grid-cols-6 gap-2">
            {CURATED.map(({ hex, nameKey }) => {
              const picked = colors.some((c) => normalizeHex(c) === normalizeHex(hex))
              const onColor = onBrandTextColor(hex)
              return (
                <button
                  key={hex}
                  type="button"
                  title={t(nameKey)}
                  aria-label={t(nameKey)}
                  aria-pressed={picked}
                  onClick={() => {
                    if (colors.length === 0) onChange({ colors: [hex] })
                    else handleAddColor(hex)
                  }}
                  className="group relative flex aspect-square w-full flex-col items-center justify-end overflow-hidden rounded-xl border border-black/10 transition-transform hover:scale-[1.03] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
                  style={{ background: hex }}
                >
                  {picked && (
                    <span
                      className="absolute end-1 top-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-white/90 shadow-xs"
                    >
                      <Check className="h-[10px] w-[10px]" style={{ color: hex }} />
                    </span>
                  )}
                
                  <span
                    className="w-full truncate bg-black/25 px-1 pb-[3px] pt-[5px] text-center text-[10px] font-medium leading-none backdrop-blur-[1px]"
                    style={{ color: onColor }}
                  >
                    {t(nameKey)}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <BrandWorkspace color={primary} syncRoot={false}>
          <div className="rounded-lg border border-border bg-card p-[18px] shadow-xs">
            <p className="text-micro font-semibold uppercase tracking-[0.09em] text-muted-foreground">{t('live_preview')}</p>
            <div className="mt-4 flex flex-col items-start gap-3">
              <Button size="sm">
                <Sparkles className="h-3.5 w-3.5" />{t('generate')}</Button>
              <BrandDot color={primary} selected />
              <div className="h-1 w-full overflow-hidden rounded-full bg-brand-weak">
                <div className="h-full w-2/3 rounded-full bg-brand" />
              </div>
              <p className="font-mono text-[11px] text-muted-foreground">
                {primary} · text {onBrandTextColor(primary) === '#FFFFFF' ? t('text_white') : t('text_ink')}
              </p>
            </div>
          </div>
        </BrandWorkspace>
      </div>
    </div>
  )
}