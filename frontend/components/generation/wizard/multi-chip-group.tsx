'use client'

import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChipOption } from './chip-group'

interface MultiChipGroupProps<T extends string> {
  options: ChipOption<T>[]
  /** القيم المختارة (أكثر من واحدة) */
  value: T[]
  onChange: (value: T[]) => void
  ariaLabel: string
  /** أقصى عدد مسموح نختاره */
  max?: number
  invalid?: boolean
}

export function MultiChipGroup<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
  max,
  invalid = false,
}: MultiChipGroupProps<T>) {
  const reachedMax = max !== undefined && value.length >= max

  function toggle(option: T) {
    if (value.includes(option)) {
      // إذا كان مختار نشيله
      onChange(value.filter((item) => item !== option))
    } else if (!reachedMax) {
      // إذا مش مختار ولسا ما وصلنا للحد نضيفه
      onChange([...value, option])
    }
  }

  return (
    <div role="group" aria-label={ariaLabel} className="flex flex-wrap gap-2">
      {options.map((option) => {
        const selected = value.includes(option.value)
        const disabled = !selected && reachedMax
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected}
            disabled={disabled}
            onClick={() => toggle(option.value)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-[8px] border px-4 py-2 text-[13.5px] leading-[19px] transition-colors',
              selected
                ? 'border-brand-primary bg-brand-primary/5 font-bold text-brand-primary'
                : 'border-brand-accent/25 bg-white font-medium text-brand-headline/80 hover:border-brand-accent/50 hover:bg-brand-cream',
              disabled && 'cursor-not-allowed opacity-40 hover:border-brand-accent/25 hover:bg-white',
              invalid && !selected && 'border-destructive/40',
            )}
          >
            {selected && <Check className="h-3.5 w-3.5" strokeWidth={2.5} />}
            {option.label}
          </button>
        )
      })}
    </div>
  )
}