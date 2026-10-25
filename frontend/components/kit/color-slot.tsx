'use client'

import { useTranslations } from 'next-intl';
import { useEffect, useState } from 'react'
import { Star, Trash2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { formatHex, isKitColor, normalizeHex } from '@/components/brand/brand-workspace'

interface ColorSlotProps {
  value: string
  isPrimary?: boolean
  canRemove?: boolean
  onChange: (hex: string) => void
  onRemove: () => void
  onMakePrimary?: () => void
}

export function ColorSlot({
  value,
  isPrimary,
  canRemove = true,
  onChange,
  onRemove,
  onMakePrimary,
}: ColorSlotProps) {
  const t = useTranslations('components.kit.color-slot');
  const [draft, setDraft] = useState(value)
  const swatch = formatHex(draft)
  const swatchReady = Boolean(normalizeHex(draft))
  const invalid = draft.length > 0 && !isKitColor(draft) && !normalizeHex(draft)

  useEffect(() => {
    setDraft(value)
  }, [value])

  function commit(raw: string) {
    const hex = normalizeHex(raw)
    if (!hex) {
      onChange(raw)
      return
    }
    const canonical = `#${hex}`
    setDraft(canonical)
    onChange(canonical)
  }

  return (
    <div
      className={cn(
        'flex min-h-[62px] items-center gap-3 rounded-xl border bg-white px-3 py-2.5',
        isPrimary ? 'border-brand-primary/25' : 'border-brand-accent/20',
      )}
    >
      <label className="relative h-[38px] w-[38px] shrink-0 cursor-pointer overflow-hidden rounded-lg border border-black/10">
        <span className="absolute inset-0" style={{ background: swatchReady ? swatch : '#CBD5E1' }} />
        <input
          type="color"
          value={swatchReady ? swatch : '#000000'}
          onChange={(e) => {
            const next = e.target.value.toUpperCase()
            setDraft(next)
            onChange(next)
          }}
          aria-label={t('color_picker')}
          className="absolute inset-0 cursor-pointer opacity-0"
        />
      </label>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className={cn('font-tajawal text-[11px] font-semibold', isPrimary ? 'text-brand-primary' : 'text-brand-headline/70')}>
          {isPrimary ? t('primary_confirmed') : t('secondary_color')}
        </span>
        <Input
          type="text"
          value={draft}
          onChange={(e) => {
            const next = e.target.value.toUpperCase()
            setDraft(next)
            onChange(next)
          }}
          onBlur={() => commit(draft)}
          maxLength={7}
          placeholder={t('rrggbb')}
          aria-label={t('hex_color_value')}
          aria-invalid={invalid}
          dir="ltr"
          className={cn(
            'h-7 w-[100px] border-0 bg-transparent p-0 font-mono text-[11px] uppercase shadow-none focus-visible:shadow-none',
            invalid && 'border-destructive',
          )}
        />
      </div>
      {!isPrimary && (
        <button
          type="button"
          onClick={onMakePrimary}
          aria-label={t('make_primary')}
          title={t('make_primary')}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-brand-weaker hover:text-brand-primary"
        >
          <Star className="h-4 w-4" />
        </button>
      )}
      <button
        type="button"
        onClick={onRemove}
        disabled={!canRemove}
        aria-label={t('remove_color')}
        className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  )
}
