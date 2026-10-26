'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'
import { apiRequest } from '@/lib/api'
import { errorMessage } from '@/lib/errors'
import { isValidTrendSlug, suggestTrendSlug } from '@/lib/admin/trend-slug'
import { useAdminList, useDebounced } from '@/hooks/admin/use-admin'
import { tagFields, type Trend } from '@/hooks/admin/types'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { TagInput } from './tag-input'
import { Filter, Heading, inputClass, Pagination, ResourceState, Search, Status, Table, useAdminFormat } from './shared'

const emptyTrend = { name: '', slug: '', description: '', category: '', status: 'active' as const, popularity_score: 0, growth_score: 0, relevance_score: 0, observed_at: '', expires_at: '', source: '', industry: [], region: [], platform: [], audience: [], visual_style: [], content_patterns: [], keywords: [], avoid_patterns: [] }
type TrendForm = Omit<Trend, 'id' | 'created_at' | 'updated_at' | 'observed_at' | 'expires_at'> & { observed_at: string; expires_at: string }
function localDate(value: string | null) { if (!value) return ''; const date = new Date(value); if (Number.isNaN(date.getTime())) return ''; return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16) }
function TrendEditor({ trend, onClose, onSaved }: { trend: Trend | null; onClose: () => void; onSaved: () => void }) {
  const t = useTranslations('adminUI'); const errors = useTranslations('errors')
  const [form, setForm] = useState<TrendForm>(() => trend ? { ...trend, observed_at: localDate(trend.observed_at), expires_at: localDate(trend.expires_at) } : { ...emptyTrend })
  const [slugEdited, setSlugEdited] = useState(!!trend); const [busy, setBusy] = useState(false); const [validation, setValidation] = useState('')
  function update<K extends keyof TrendForm>(key: K, value: TrendForm[K]) { setForm(current => ({ ...current, [key]: value })) }
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setValidation('')
    if (!isValidTrendSlug(form.slug)) { setValidation(t('invalidSlug')); return }
    if (form.observed_at && form.expires_at && form.expires_at < form.observed_at) { setValidation(t('invalidDates')); return }
    setBusy(true)
    const body = Object.fromEntries(Object.keys(emptyTrend).map(key => [key, key === 'observed_at' || key === 'expires_at' ? (form[key] ? new Date(form[key]).toISOString() : null) : form[key as keyof TrendForm]]))
    try { await apiRequest(trend ? `/admin/trends/${encodeURIComponent(trend.id)}` : '/admin/trends', { method: trend ? 'PATCH' : 'POST', body: JSON.stringify(body) }); toast.success(t('saved')); onSaved(); onClose() } catch (err) { toast.error(errorMessage(err, errors)) } finally { setBusy(false) }
  }
  return <Dialog open onOpenChange={open => { if (!open && !busy) onClose() }}><DialogContent closeLabel={t('close')} aria-describedby={undefined} className="max-h-[90dvh] max-w-3xl overflow-y-auto text-start"><DialogTitle>{t(trend ? 'editTrend' : 'createTrend')}</DialogTitle><form className="space-y-4" onSubmit={submit}><fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2"><label className="text-sm">{t('name')}<input required className={inputClass} value={form.name} onChange={event => { const name = event.target.value; setForm(current => ({ ...current, name, ...(!slugEdited ? { slug: suggestTrendSlug(name) } : {}) })) }} /></label><label className="text-sm">{t('slug')}<input required dir="ltr" pattern="[a-z0-9]+(-[a-z0-9]+)*" className={inputClass} value={form.slug} onChange={event => { setSlugEdited(true); update('slug', event.target.value) }} /><span className="text-xs text-muted-foreground">{t('slugHint')}</span></label><label className="text-sm sm:col-span-2">{t('description')}<textarea className={`${inputClass} h-24 py-2`} value={form.description} onChange={event => update('description', event.target.value)} /></label><label className="text-sm">{t('category')}<input className={inputClass} value={form.category} onChange={event => update('category', event.target.value)} /></label><label className="text-sm">{t('status')}<select className={inputClass} value={form.status} onChange={event => update('status', event.target.value as Trend['status'])}>{['active', 'inactive', 'expired'].map(status => <option key={status} value={status}>{t(`statuses.${status}`)}</option>)}</select></label>{(['popularity_score', 'growth_score', 'relevance_score'] as const).map(key => <label key={key} className="text-sm">{t(key)}<input required type="number" min="0" max="100" step="1" className={inputClass} value={form[key]} onChange={event => update(key, Number(event.target.value))} /></label>)}{(['observed_at', 'expires_at'] as const).map(key => <label key={key} className="text-sm">{t(key)}<input type="datetime-local" className={inputClass} value={form[key]} onChange={event => update(key, event.target.value)} /></label>)}<label className="text-sm">{t('source')}<input className={inputClass} value={form.source} onChange={event => update('source', event.target.value)} /></label>{tagFields.map(key => <TagInput key={key} label={t(key)} value={form[key]} onChange={value => update(key, value)} />)}</fieldset>{validation && <p role="alert" className="text-sm text-destructive">{validation}</p>}<div className="flex justify-end gap-2"><Button type="button" variant="outline" disabled={busy} onClick={onClose}>{t('cancel')}</Button><Button type="submit" disabled={busy}>{t(busy ? 'saving' : 'save')}</Button></div></form></DialogContent></Dialog>
}
export function TrendsPage() {
  const t = useTranslations('adminUI'); const errors = useTranslations('errors'); const f = useAdminFormat(); const confirm = useConfirm()
  const [q, setQ] = useState(''); const [status, setStatus] = useState(''); const [editing, setEditing] = useState<Trend | null | undefined>(undefined); const [busy, setBusy] = useState(false)
  const list = useAdminList<Trend>('trends', { q: useDebounced(q), status })
  async function remove(trend: Trend) {
    setBusy(true)
    try { if (!await confirm({ title: t('deleteTrend'), description: t('confirmTrendDelete', { name: trend.name }), tone: 'danger' })) return; await apiRequest(`/admin/trends/${encodeURIComponent(trend.id)}`, { method: 'DELETE' }); toast.success(t('deleted')); list.refresh() } catch (err) { toast.error(errorMessage(err, errors)) } finally { setBusy(false) }
  }
  return <><Heading title={t('trends')}><Button onClick={() => setEditing(null)}>{t('createTrend')}</Button></Heading><div className="mb-5 flex flex-wrap gap-3"><Search value={q} onChange={setQ} /><Filter label={t('status')} value={status} onChange={setStatus} options={['active', 'inactive', 'expired']} /></div><ResourceState loading={list.loading} error={list.error} empty={!list.data?.items.length} retry={list.refresh} />{!!list.data?.items.length && <Table headers={['name', 'category', 'status', 'popularity_score', 'growth_score', 'relevance_score', 'expires_at', 'actionsTitle'].map(key => t(key))}>{list.data.items.map(trend => <tr key={trend.id}><td className="max-w-xs"><p className="font-semibold">{trend.name}</p><code className="text-xs">{trend.slug}</code><p className="line-clamp-2 text-xs text-muted-foreground">{trend.description}</p></td><td>{trend.category}</td><td><Status value={trend.status} /></td><td>{f.number(trend.popularity_score)}</td><td>{f.number(trend.growth_score)}</td><td>{f.number(trend.relevance_score)}</td><td>{f.date(trend.expires_at)}</td><td><div className="flex gap-2"><Button variant="outline" disabled={busy} onClick={() => setEditing(trend)}>{t('edit')}</Button><Button variant="destructive" disabled={busy} onClick={() => remove(trend)}>{t('actions.delete')}</Button></div></td></tr>)}</Table>}<Pagination {...list} />{editing !== undefined && <TrendEditor trend={editing} onClose={() => setEditing(undefined)} onSaved={list.refresh} />}</>
}
