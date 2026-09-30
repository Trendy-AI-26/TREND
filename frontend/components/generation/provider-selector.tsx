'use client'

import { useTranslations } from 'next-intl'
import { NoKeyNotice } from '@/components/generation/no-key-notice'
import { Eyebrow } from '@/components/ui/eyebrow'

interface ProviderSelectorProps {
  disabled?: boolean
}

export function ProviderSelector({ disabled }: ProviderSelectorProps) {
  const t = useTranslations('components.generation.provider-selector')

  return (
    <div className={`flex flex-col gap-2${disabled ? ' opacity-70' : ''}`}>
      <Eyebrow>{t('provider2')}</Eyebrow>
      <div className="flex h-10 items-center rounded-md border border-border-subtle bg-muted/30 px-3 text-sm text-foreground">
        OpenAI (server-managed)
      </div>
      <NoKeyNotice />
    </div>
  )
}
