'use client'

import { useCallback, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { AlertCircle, Check, ChevronDown, Download, Eye, Loader2, Plus, Trash2 } from 'lucide-react'
import { useGenerationHistory } from '@/hooks/use-generation-history'
import { useDeleteGeneration } from '@/hooks/use-delete-generation'
import { useBrand } from '@/hooks/use-brand'
import { DeleteGenerationDialog } from '@/components/history/delete-generation-dialog'
import { Button } from '@/components/ui/button'
import type { GenerationHistoryItem } from '@/types'

interface LibraryViewProps { brandId: string }

export function LibraryView({ brandId }: LibraryViewProps) {
    const t = useTranslations('app.(dashboard).[brandId].history.page')
    const tf = useTranslations('components.history.history-filters')
    const tl = useTranslations('components.history.history-list')
    const router = useRouter()
    const searchParams = useSearchParams()
    const { brand } = useBrand(brandId)
    const status = searchParams.get('status') ?? undefined
    const cursor = searchParams.get('cursor') ?? undefined
    const { items, loading, loadingMore, error, hasNext, loadMore, removeItem } = useGenerationHistory(brandId, undefined, status, cursor)
    const { deleteGeneration } = useDeleteGeneration(brandId)
    const visibleItems = useMemo(() => items, [items])
    const updateStatus = useCallback((next: string) => {
        const params = new URLSearchParams()
        if (next !== 'all') params.set('status', next)
        router.push(`/${brandId}/history${params.toString() ? `?${params}` : ''}`)
    }, [brandId, router])
    const handleLoadMore = useCallback(async () => {
        const loadedCursor = await loadMore()
        if (!loadedCursor) return
        const params = new URLSearchParams()
        if (status) params.set('status', status)
        params.set('cursor', loadedCursor)
        window.history.replaceState(null, '', `/${brandId}/history?${params}`)
    }, [brandId, loadMore, status])
    const handleDelete = useCallback(async (id: string) => {
        const outcome = await deleteGeneration(id)
        if (outcome.ok) removeItem(id)
        return outcome
    }, [deleteGeneration, removeItem])

    return (
        <div className="mx-auto w-full max-w-[1120px] space-y-7 pb-10 font-readex">
            <header className="flex flex-wrap items-end justify-between gap-5">
                <div>
                    <p className="mb-1 text-[13px] font-medium text-brand-primary">{brand?.name ?? 'TRENDY AI'}</p>
                    <h1 className="font-heading text-[38px] font-bold leading-tight text-brand-headline">{t('library_title')}</h1>
                    <p className="mt-2 text-[14px] text-brand-headline/55">{t('library_subtitle')}</p>
                </div>
                <Button type="button" onClick={() => router.push(`/${brandId}/generate`)} className="h-11 rounded-xl bg-brand-primary px-5 text-[14px] font-bold text-white shadow-sm hover:bg-[#74151b]"><Plus className="h-4 w-4" />{t('new_design')}</Button>
            </header>

            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-brand-accent/20 pb-3">
                <div className="flex items-end gap-8">
                    <div className="border-b-2 border-brand-primary pb-3 text-[15px] font-bold text-brand-primary"><span>{t('generation_log')}</span><span className="ms-2 text-[12px] text-brand-primary/70">{items.length}{hasNext ? '+' : ''}</span></div>
                </div>
                <label className="relative block"><span className="sr-only">{tf('status')}</span><select value={status ?? 'all'} onChange={(e) => updateStatus(e.target.value)} className="h-10 min-w-[130px] appearance-none rounded-lg border border-brand-accent/25 bg-white px-4 pe-9 text-[13px] text-brand-headline/75 shadow-xs focus:outline-none focus:ring-2 focus:ring-brand-primary/20"><option value="all">{t('all_statuses')}</option><option value="succeeded">{tf('succeeded')}</option><option value="failed">{tf('failed')}</option></select><ChevronDown className="pointer-events-none absolute end-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-headline/50" /></label>
            </div>

            {loading && <div className="flex justify-center py-24"><Loader2 className="h-7 w-7 animate-spin text-brand-primary" /></div>}
            {!loading && error && <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-5 text-center text-sm text-destructive">{error}</div>}
            {!loading && !error && visibleItems.length === 0 && <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-brand-accent/30 bg-white/60 py-24 text-center"><p className="text-[15px] text-brand-headline/60">{status ? tl('no_history_match_filters') : tl('no_history_yet')}</p><Button type="button" onClick={() => router.push(`/${brandId}/generate`)} variant="outline" className="rounded-lg">{t('new_design')}</Button></div>}
            {!loading && !error && visibleItems.length > 0 && <div className="overflow-hidden rounded-2xl border border-brand-accent/20 bg-white shadow-sm">{visibleItems.map((item) => <LibraryRow key={item.id} item={item} brandId={brandId} onDelete={handleDelete} />)}</div>}
            {hasNext && <div className="flex justify-center"><Button type="button" variant="outline" onClick={handleLoadMore} disabled={loadingMore} className="rounded-lg">{loadingMore ? tl('loading') : tl('load_more')}</Button></div>}
        </div>
    )
}

function LibraryRow({ item, brandId, onDelete }: { item: GenerationHistoryItem; brandId: string; onDelete: (id: string) => Promise<{ ok: boolean; message?: string }> }) {
    const t = useTranslations('app.(dashboard).[brandId].history.page')
    const tc = useTranslations('components.history.history-card')
    const tf = useTranslations('components.history.history-filters')
    const [dialogOpen, setDialogOpen] = useState(false)
    const [deleting, setDeleting] = useState(false)
    const [deleteError, setDeleteError] = useState<string | null>(null)
    const success = item.status === 'succeeded' && Boolean(item.image_url)
    async function confirmDelete() {
        setDeleting(true); setDeleteError(null)
        const result = await onDelete(item.id)
        if (result.ok) setDialogOpen(false)
        else setDeleteError(result.message ?? tc('failed_to_delete_try_again'))
        setDeleting(false)
    }
    return <>
        <article className="group flex min-h-[164px] items-center gap-5 border-b border-brand-accent/10 p-4 last:border-b-0 md:p-5">
            <Link href={`/${brandId}/history/${item.id}`} className="relative h-[96px] w-[96px] shrink-0 overflow-hidden rounded-xl bg-brand-cream no-underline md:h-[108px] md:w-[108px]">
                {item.image_url ? <img src={item.image_url} alt={item.prompt_excerpt} className="h-full w-full object-cover" /> : <div className="flex h-full w-full items-center justify-center text-brand-primary"><AlertCircle className="h-6 w-6" /></div>}
            </Link>
            <div className="min-w-0 flex-1 text-start">
                <h2 className="truncate text-[16px] font-bold text-brand-headline">{item.prompt_excerpt}</h2>
                <p className="mt-2 text-[12px] text-brand-headline/45">{item.platform_preset} · {new Date(item.created_at).toLocaleDateString()}</p>
                <div className="mt-3 flex items-center gap-2"><span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${success ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'}`}>{success ? <Check className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}{tf(item.status)}</span>{item.error_message && <span className="max-w-[260px] truncate text-[11px] text-red-500">{item.error_message}</span>}</div>
            </div>
            <div className="flex shrink-0 flex-col items-stretch gap-2 md:flex-row md:items-center">
                <Link href={`/${brandId}/history/${item.id}`} className="inline-flex h-9 items-center justify-center gap-1.5 rounded-lg border border-brand-accent/25 px-3 text-[12px] text-brand-headline/70 no-underline hover:border-brand-primary hover:text-brand-primary"><Eye className="h-3.5 w-3.5" />{t('view_details')}</Link>
                {success && <a href={item.image_url ?? undefined} download={`trendy-${item.id}.png`} className="inline-flex h-9 items-center justify-center gap-1.5 rounded-lg border border-brand-accent/25 px-3 text-[12px] text-brand-headline/70 no-underline hover:border-brand-primary hover:text-brand-primary"><Download className="h-3.5 w-3.5" />{t('download')}</a>}
                {!success && <Link href={`/${brandId}/generate`} className="inline-flex h-9 items-center justify-center rounded-lg border border-brand-accent/25 px-3 text-[12px] text-brand-headline/70 no-underline hover:border-brand-primary hover:text-brand-primary">{t('retry')}</Link>}
                <button type="button" onClick={() => setDialogOpen(true)} aria-label={tc('delete')} className="inline-flex h-9 items-center justify-center rounded-lg border border-brand-accent/25 px-3 text-[12px] text-brand-headline/60 hover:border-red-300 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /><span className="sr-only">{tc('delete')}</span></button>
            </div>
        </article>
        <DeleteGenerationDialog open={dialogOpen} onOpenChange={setDialogOpen} onConfirm={confirmDelete} loading={deleting} error={deleteError} />
    </>
}
