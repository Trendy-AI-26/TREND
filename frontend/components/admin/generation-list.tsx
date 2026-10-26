'use client'

import Image from 'next/image'
import { useTranslations } from 'next-intl'
import { Badge } from '@/components/ui/badge'
import type { GenerationRow } from '@/hooks/admin/types'
import { Status, Table, useAdminFormat } from './shared'

export function Thumbnail({ row }: { row: GenerationRow }) {
  const t = useTranslations('adminUI')
  return row.image_url ? <Image src={row.image_url} alt={t('generationImage', { brand: row.brand.name })} width={64} height={64} unoptimized className="h-16 w-16 shrink-0 rounded-lg bg-brand-cream object-cover" /> : <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg bg-brand-cream text-xs text-muted-foreground">{t('noImage')}</span>
}
export function GenerationList({ items }: { items: GenerationRow[] }) {
  const t = useTranslations('adminUI'); const f = useAdminFormat()
  return <Table headers={['image', 'status', 'user', 'brand', 'platform', 'providerModel', 'error', 'created', 'completed'].map(key => t(key))}>{items.map(row => <tr key={row.id}><td><Thumbnail row={row} /></td><td><div className="flex flex-wrap gap-1"><Status value={row.status} />{row.needs_review && <Badge>{t('needsReview')}</Badge>}</div></td><td><bdi>{row.user.email}</bdi></td><td>{row.brand.name}</td><td>{row.platform_preset}</td><td><bdi>{row.provider} / {row.model}</bdi></td><td className="max-w-xs break-words text-destructive"><code className="text-xs">{row.error_code}</code><p>{row.error_message || '—'}</p></td><td className="whitespace-nowrap">{f.date(row.created_at)}</td><td className="whitespace-nowrap">{f.date(row.completed_at)}</td></tr>)}</Table>
}
