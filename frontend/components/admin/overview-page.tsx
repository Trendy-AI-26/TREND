'use client'

import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { useAdminResource } from '@/hooks/admin/use-admin'
import type { Overview } from '@/hooks/admin/types'
import { DailyChart } from './daily-chart'
import { Thumbnail } from './generation-list'
import { Heading, panelClass, ResourceState, Status, useAdminFormat } from './shared'

export function OverviewPage() {
  const t = useTranslations('adminUI'); const f = useAdminFormat()
  const { data, loading, error, refresh } = useAdminResource<Overview>('/admin/overview')
  return <><Heading title={t('overview')} /><ResourceState loading={loading} error={error} retry={refresh} />{data && <>
    <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">{[
      ['users', f.number(data.users.total), t('verifiedCount', { count: f.number(data.users.verified) })],
      ['brands', f.number(data.brands.total), t('completeCount', { count: f.number(data.brands.kits_complete) })],
      ['generations', f.number(data.generations.total), t('todayCount', { count: f.number(data.generations.today) })],
      ['successRate', f.percent(data.generations.success_rate_30d), t('last30Days')],
      ['cost', f.number(data.cost.credits_charged_30d), t('providerEstimate', { amount: f.number(data.cost.estimated_provider_cost_30d) })],
    ].map(([key, value, note]) => <section key={key} className={panelClass}><p className="text-sm text-muted-foreground">{t(key)}</p><p className="my-2 text-3xl font-semibold tabular-nums">{value}</p><p className="text-xs text-muted-foreground">{note}</p></section>)}</div>
    <section className={panelClass}><DailyChart daily={data.daily} /></section>
    <section className="mt-6"><h2 className="mb-4 text-lg font-semibold">{t('attention')}</h2><div className="grid gap-5 xl:grid-cols-2">{(['needs_review', 'recent_failures'] as const).map(key => <section key={key} className={panelClass}><div className="mb-4 flex items-center justify-between gap-2"><h3 className="font-semibold">{t(key === 'needs_review' ? 'needsReview' : 'recentFailures')}</h3><Link className="text-sm text-brand-primary" href={`/admin/generations?${key === 'needs_review' ? 'needs_review=true' : 'status=failed'}`}>{t('viewAll')}</Link></div>{!data.attention[key].length && <p className="py-8 text-center text-muted-foreground">{t('empty')}</p>}<ul className="divide-y divide-brand-accent/20">{data.attention[key].map(row => <li key={row.id} className="flex gap-3 py-4"><Thumbnail row={row} /><div className="min-w-0 flex-1 space-y-1 text-sm"><p className="truncate"><bdi>{row.user.email}</bdi></p><p>{row.brand.name} · {row.platform_preset}</p><Status value={row.status} /><p className="break-words text-xs text-destructive">{row.error_message || '—'}</p><time dateTime={row.created_at} title={f.date(row.created_at)} className="text-xs text-muted-foreground">{f.relative(row.created_at)}</time></div></li>)}</ul></section>)}</div></section>
  </>}</>
}
