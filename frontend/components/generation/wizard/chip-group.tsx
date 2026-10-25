'use client'

import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ChipOption<T extends string> {
  value: T
  label: string
}

interface ChipGroupProps<T extends string> {
  options: ChipOption<T>[]
  value: T | ''
  onChange: (value: T) => void
  ariaLabel: string
  invalid?: boolean
}

export function ChipGroup<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
  invalid = false,
}: ChipGroupProps<T>) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className="flex flex-wrap gap-2">
      {options.map((option) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-[8px] border px-4 py-2 text-[13.5px] leading-[19px] transition-colors',
              selected
                ? 'border-brand-primary bg-brand-primary/5 font-bold text-brand-primary'
                : 'border-brand-accent/25 bg-white font-medium text-brand-headline/80 hover:border-brand-accent/50 hover:bg-brand-cream',
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