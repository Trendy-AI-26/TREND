'use client'

import { useLocale, useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { errorMessage } from '@/lib/errors'
import type { Page } from '@/hooks/admin/types'

export const inputClass = 'h-10 w-full rounded-lg border border-brand-accent/40 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/40'
export const panelClass = 'rounded-xl border border-brand-accent/30 bg-white p-5 shadow-sm'
export function useAdminFormat() {
  const locale = useLocale()
  return {
    number: (value: number | null | undefined) => value == null ? '—' : new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value),
    percent: (value: number | null) => value == null ? '—' : new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 2 }).format(value),
    date: (value: string | null | undefined) => !value || Number.isNaN(Date.parse(value)) ? '—' : new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)),
    relative: (value: string) => { const seconds = (Date.parse(value) - Date.now()) / 1000; const unit = Math.abs(seconds) < 3600 ? 'minute' : Math.abs(seconds) < 86400 ? 'hour' : 'day'; return new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }).format(Math.round(seconds / (unit === 'minute' ? 60 : unit === 'hour' ? 3600 : 86400)), unit) },
  }
}
export function Heading({ title, children }: { title: string; children?: React.ReactNode }) {
  return <header className="mb-6 flex flex-wrap items-center justify-between gap-3"><h1 className="text-2xl font-semibold text-brand-headline">{title}</h1>{children}</header>
}
export function Status({ value }: { value: string }) {
  const t = useTranslations('adminUI')
  return <Badge variant={['succeeded', 'complete', 'active', 'verified'].includes(value) ? 'success' : 'muted'}>{t(`statuses.${value}`)}</Badge>
}
export function Search({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const t = useTranslations('adminUI')
  return <input type="search" aria-label={t('search')} placeholder={t('search')} className={`${inputClass} sm:max-w-xs`} value={value} onChange={event => onChange(event.target.value)} />
}
export function Filter({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  const t = useTranslations('adminUI')
  return <label className="flex items-center gap-2 text-sm"><span>{label}</span><select className={inputClass} value={value} onChange={event => onChange(event.target.value)}><option value="">{t('all')}</option>{options.map(option => <option key={option} value={option}>{t(`statuses.${option}`)}</option>)}</select></label>
}
export function ResourceState({ loading, error, empty, retry }: { loading: boolean; error: unknown; empty?: boolean; retry?: () => void }) {
  const t = useTranslations('adminUI'); const errors = useTranslations('errors')
  if (loading) return <div role="status" aria-label={t('loading')} className="space-y-3 py-5">{[1, 2, 3].map(i => <div key={i} className="h-12 animate-pulse rounded-lg bg-brand-accent/20" />)}<span className="sr-only">{t('loading')}</span></div>
  if (error) return <div role="alert" className="py-5 text-destructive">{errorMessage(error, errors)} {retry && <Button variant="outline" onClick={retry}>{t('retry')}</Button>}</div>
  if (empty) return <p className="py-12 text-center text-muted-foreground">{t('empty')}</p>
  return null
}
export function Pagination({ data, page, setPage, loading }: { data: Page<unknown> | null; page: number; setPage: (page: number) => void; loading: boolean }) {
  const t = useTranslations('adminUI'); const f = useAdminFormat()
  return <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm"><span>{t('pagination', { total: f.number(data?.total ?? 0), page: f.number(page), pages: f.number(Math.max(1, Math.ceil((data?.total ?? 0) / (data?.per_page ?? 24)))) })}</span><div className="flex gap-2"><Button variant="outline" disabled={loading || page <= 1} onClick={() => setPage(page - 1)}>{t('previous')}</Button><Button variant="outline" disabled={loading || !data || page * data.per_page >= data.total} onClick={() => setPage(page + 1)}>{t('next')}</Button></div></div>
}
export function Table({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return <div className="overflow-x-auto rounded-xl border border-brand-accent/30 bg-white"><table className="w-full text-start text-sm [&_th]:whitespace-nowrap [&_th]:px-4 [&_th]:py-3 [&_th]:text-start [&_td]:px-4 [&_td]:py-3"><thead className="bg-brand-cream text-brand-headline/70"><tr>{headers.map((header, i) => <th key={i}>{header}</th>)}</tr></thead><tbody className="divide-y divide-brand-accent/20">{children}</tbody></table></div>
}
