'use client'

import { useTranslations } from 'next-intl'
import { useAdminList } from '@/hooks/admin/use-admin'
import type { AuditRow } from '@/hooks/admin/types'
import { Heading, Pagination, ResourceState, Table, useAdminFormat } from './shared'

export function AuditPage() {
  const t = useTranslations('adminUI'); const f = useAdminFormat(); const list = useAdminList<AuditRow>('audit-log')
  return <><Heading title={t('audit')} /><ResourceState loading={list.loading} error={list.error} empty={!list.data?.items.length} retry={list.refresh} />{!!list.data?.items.length && <Table headers={['admin', 'action', 'target', 'details', 'date'].map(key => t(key))}>{list.data.items.map(row => <tr key={row.id}><td><bdi>{row.admin_email}</bdi></td><td><code>{row.action}</code></td><td><bdi>{row.target_type}: {row.target_id}</bdi></td><td><code dir="ltr" className="block max-w-md overflow-x-auto whitespace-pre text-xs">{JSON.stringify(row.details)}</code></td><td className="whitespace-nowrap">{f.date(row.created_at)}</td></tr>)}</Table>}<Pagination {...list} /></>
}
