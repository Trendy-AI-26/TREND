'use client'

import { useTranslations } from 'next-intl';
import { Eyebrow } from '@/components/ui/eyebrow'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

interface PromptInputProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

const MIN = 3
const MAX = 4000

export function PromptInput({ value, onChange, disabled }: PromptInputProps) {
  const t = useTranslations('components.generation.prompt-input');
  const length = value.length
  const trimmed = value.trim().length
  const tooShort = trimmed > 0 && trimmed < MIN
  const tooLong = trimmed > MAX

  return (
    <div className="flex flex-col gap-2">
      <Eyebrow>{t('prompt')}</Eyebrow>
      <div className="relative">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={t('describe_the_image')}
          className="min-h-[128px] pb-7 text-[15px] leading-[1.5]"
          maxLength={MAX + 200}
        />
        <span
          className={cn(
            'pointer-events-none absolute bottom-2 right-3 font-mono text-[11px] tabular-nums text-muted-foreground',
            (tooShort || tooLong) && 'text-destructive',
          )}
        >
          {length} / {MAX}
        </span>
      </div>
      {tooShort && (
        <p className="text-[12px] text-muted-foreground">Minimum {MIN} characters.</p>
      )}
    </div>
  )
}
