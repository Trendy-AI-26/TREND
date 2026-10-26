'use client'

import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { useAdminList, useDebounced } from '@/hooks/admin/use-admin'
import type { GenerationRow } from '@/hooks/admin/types'
import { GenerationList } from './generation-list'
import { Filter, Heading, inputClass, Pagination, ResourceState, Search } from './shared'

export function GenerationsPage() {
  const t = useTranslations('adminUI'); const params = useSearchParams(); const router = useRouter(); const pathname = usePathname()
  const q = params.get('q') ?? ''
  const filters = { q: useDebounced(q), status: params.get('status') ?? '', needs_review: params.get('needs_review') === 'true' ? 'true' : '', from: params.get('from') ?? '', to: params.get('to') ?? '' }
  const list = useAdminList<GenerationRow>('generations', filters)
  function update(key: string, value: string) { const next = new URLSearchParams(params.toString()); if (value) next.set(key, value); else next.delete(key); router.replace(`${pathname}?${next}`, { scroll: false }) }
  return <><Heading title={t('generations')} /><div className="mb-5 flex flex-wrap items-center gap-3"><Search value={q} onChange={value => update('q', value)} /><Filter label={t('status')} value={filters.status} onChange={value => update('status', value)} options={['pending', 'processing', 'succeeded', 'failed']} /><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={filters.needs_review === 'true'} onChange={event => update('needs_review', event.target.checked ? 'true' : '')} />{t('needsReview')}</label>{(['from', 'to'] as const).map(key => <label key={key} className="flex items-center gap-2 text-sm">{t(key)}<input type="date" className={inputClass} value={filters[key]} max={key === 'from' ? filters.to || undefined : undefined} min={key === 'to' ? filters.from || undefined : undefined} onChange={event => update(key, event.target.value)} /></label>)}</div><ResourceState loading={list.loading} error={list.error} empty={!list.data?.items.length} retry={list.refresh} />{!!list.data?.items.length && <GenerationList items={list.data.items} />}<Pagination {...list} /></>
}
