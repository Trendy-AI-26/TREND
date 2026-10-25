'use client'

import { useLocale, useTranslations } from 'next-intl';
import { Check, Eye, Plus, Sparkles } from 'lucide-react'
import { BrandDot } from '@/components/brand/brand-dot'
import { BrandWorkspace, TRENDY_AI_ACCENT, formatHex, normalizeHex } from '@/components/brand/brand-workspace'
import { ColorSlot } from '@/components/kit/color-slot'
import { KitQuestion } from '@/components/kit/kit-question'
import { Button } from '@/components/ui/button'
import { KitAnswers } from '@/types'

interface StepProps {
  answers: KitAnswers
  onChange: (partial: Partial<KitAnswers>) => void
}

const CURATED: { hex: string; nameKey: string }[] = [
  { hex: '#7A1521', nameKey: 'color_maroon' },
  { hex: '#D63384', nameKey: 'color_pink' },
  { hex: '#9333EA', nameKey: 'color_purple' },
  { hex: '#3B82F6', nameKey: 'color_blue' },
  { hex: '#1E1B2E', nameKey: 'color_navy' },
  { hex: '#06B6D4', nameKey: 'color_cyan' },
  { hex: '#64748B', nameKey: 'color_gray' },
  { hex: '#2563EB', nameKey: 'color_sky' },
  { hex: '#10B981', nameKey: 'color_green' },
  { hex: '#C9A26B', nameKey: 'color_gold' },
  { hex: '#F97316', nameKey: 'color_orange' },
  { hex: '#EF4444', nameKey: 'color_red' },
]

export function StepColors({ answers, onChange }: StepProps) {
  const t = useTranslations('components.kit.steps.step-colors');
  const locale = useLocale()
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
    if (colors.length >= 4) return
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
        align="center"
        before={t('your_prefix')}
        emphasis={t('colors_word')}
        after="."
        helper={t('colors_help')}
      />
      <div dir={locale === 'ar' ? 'rtl' : 'ltr'} className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_180px]">
        <div className="space-y-2">
          <div className="space-y-2 rounded-2xl border border-brand-accent/15 bg-white p-3 shadow-xs sm:p-4">
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
              <p className="font-tajawal text-[12px] text-muted-foreground">{t('add_a_color_to')}</p>
            )}
            <button
              type="button"
              onClick={() => handleAddColor()}
              disabled={colors.length >= 4}
              className="flex h-9 w-full items-center justify-center gap-2 border-y border-dashed border-brand-accent/20 font-tajawal text-[11px] text-muted-foreground transition-colors hover:text-brand-primary disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" />{t('add_color')}
            </button>
          </div>

          <div className="rounded-2xl border border-brand-accent/15 bg-white p-3 shadow-xs sm:p-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="font-tajawal text-[11px] font-semibold text-brand-headline">{t('curated_palette')}</p>
              <span className="font-tajawal text-[10px] text-muted-foreground">{t('choose_quick_color')}</span>
            </div>
            <div className="grid grid-cols-6 gap-2">
              {CURATED.map(({ hex, nameKey }) => {
                const picked = colors.some((c) => normalizeHex(c) === normalizeHex(hex))
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
                    className="group relative h-10 w-full overflow-hidden rounded-lg border border-black/10 transition-transform hover:scale-[1.03] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
                    style={{ background: hex }}
                  >
                    {picked && (
                      <span className="absolute end-1 top-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-white/90 shadow-xs">
                        <Check className="h-[10px] w-[10px]" style={{ color: hex }} />
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        <BrandWorkspace color={primary} syncRoot={false}>
          <aside className="flex min-h-[250px] flex-col self-start rounded-2xl border border-brand-accent/15 bg-white p-4 shadow-xs lg:sticky lg:top-4">
            <div className="flex items-center justify-between">
              <p className="font-tajawal text-[12px] font-semibold text-brand-headline">{t('live_preview')}</p>
              <Eye className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            </div>
            <Button size="sm" className="mt-4 self-center rounded-full px-4">
              <Sparkles className="h-3.5 w-3.5" />{t('generate')}
            </Button>
            <div className="my-4 flex flex-1 flex-col items-center justify-center gap-3 text-center">
              <BrandDot color={primary} selected size={48} />
              <span className="font-mono text-[12px] font-semibold text-brand-headline">{primary}</span>
              <p className="font-tajawal text-[11px] leading-5 text-muted-foreground">{t('preview_description')}</p>
            </div>
          </aside>
        </BrandWorkspace>
      </div>
    </div>
  )
}
