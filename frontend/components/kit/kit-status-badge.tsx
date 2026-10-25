'use client'

import { useTranslations } from 'next-intl';
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { KitStatus } from '@/types'

const VARIANTS: Record<KitStatus, 'muted' | 'warning' | 'success'> = {
  not_started: 'muted',
  in_progress: 'warning',
  complete: 'success',
}

export function KitStatusBadge({
  status,
  brandId,
}: {
  status: KitStatus
  brandId?: string
}) {
  const t = useTranslations('components.kit.kit-status-badge');
  const label = t(status)

  const badge = (
    <Badge
      variant={VARIANTS[status]}
      aria-label={t('status_aria', { status: label })}
    >
      {label}
    </Badge>
  )

  if (!brandId) return badge

  return (
    <Link
      href={`/${brandId}/kit`}
      className="no-underline"
      aria-label={t('status_aria_edit', { status: label })}
    >
      {badge}
    </Link>
  )
}
