'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { useAdminList, useDebounced } from '@/hooks/admin/use-admin'
import type { AdminBrand } from '@/hooks/admin/types'
import { Filter, Heading, Pagination, ResourceState, Search, Status, Table, useAdminFormat } from './shared'

export function BrandsPage() {
  const t = useTranslations('adminUI'); const f = useAdminFormat(); const [q, setQ] = useState(''); const [kit, setKit] = useState('')
  const list = useAdminList<AdminBrand>('brands', { q: useDebounced(q), kit_status: kit })
  return <><Heading title={t('brands')} /><div className="mb-5 flex flex-wrap gap-3"><Search value={q} onChange={setQ} /><Filter label={t('kitStatus')} value={kit} onChange={setKit} options={['not_started', 'in_progress', 'complete']} /></div><ResourceState loading={list.loading} error={list.error} empty={!list.data?.items.length} retry={list.refresh} />{list.data?.items.length ? <Table headers={['name', 'owner', 'kitStatus', 'colors', 'logo', 'generations', 'created'].map(key => t(key))}>{list.data.items.map(row => <tr key={row.id}><td className="font-semibold">{row.name}</td><td>{row.owner.full_name}<p><bdi>{row.owner.email}</bdi></p></td><td><Status value={row.kit_status} /></td><td>{f.number(row.colors_count)}</td><td>{t(row.has_logo ? 'yes' : 'no')}</td><td>{f.number(row.generation_count)}</td><td>{f.date(row.created_at)}</td></tr>)}</Table> : null}<Pagination {...list} /></>
}
