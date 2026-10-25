'use client'

import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'
import type { KitStatus } from '@/types'

export type StatusFilter = 'all' | KitStatus

interface BrandStatsProps {
  counts: Record<StatusFilter, number>
  value: StatusFilter
  onChange: (next: StatusFilter) => void
}


const CARDS: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'total_brands' },
  { key: 'in_progress', label: 'in_progress' },
  { key: 'complete', label: 'completed' },
  { key: 'not_started', label: 'pending' },
]

export function BrandStats({ counts, value, onChange }: BrandStatsProps) {
  const t = useTranslations('components.brand.brand-stats')

  return (
    <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
      {CARDS.map((card) => {
        const selected = value === card.key
        return (
          <button
            key={card.key}
            type="button"
            onClick={() => onChange(card.key)}
            aria-pressed={selected}
            className={cn(
              'flex h-[140px] flex-col items-center justify-between rounded-2xl border-2 border-b-4 bg-brand-cream px-5 pb-6 pt-[22px] font-readex shadow-xs transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/40',
              selected
                ? 'border-brand-primary'
                : 'border-transparent hover:border-brand-accent/40',
            )}
          >
            <span className="text-[48px] font-bold leading-[48px] tracking-[-1.2px] text-brand-headline">
              {counts[card.key]}
            </span>
            <span className="text-[14px] font-medium text-brand-headline/60">{t(card.label)}</span>
          </button>
        )
      })}
    </div>
  )
}