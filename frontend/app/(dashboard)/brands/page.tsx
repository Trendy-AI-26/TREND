'use client'

import { useTranslations } from 'next-intl';
import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChevronDown, Plus, Search } from 'lucide-react'
import { useBrands } from '@/hooks/use-brands'
import { CreateBrandModal } from '@/components/brand/create-brand-modal'
import { DeleteBrandDialog } from '@/components/brand/delete-brand-dialog'
import { BrandStats, type StatusFilter } from '@/components/brand/brand-stats'
import { BrandsTable, type BrandSort } from '@/components/brand/brands-table'
import { Button } from '@/components/ui/button'
import { Brand, BrandListItem } from '@/types'

const selectClass =
  'h-10 w-full appearance-none rounded-lg border border-brand-accent/30 bg-white ps-3 pe-9 font-readex text-[14px] font-medium text-brand-headline/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/40'

export default function BrandsPage() {
  const t = useTranslations('app.(dashboard).brands.page');
  const [showCreateModal, setShowCreateModal] = useState(false)
  const { brands, loading, error, accents, addBrand, removeBrand } = useBrands()
  const router = useRouter()

  
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [sort, setSort] = useState<BrandSort>('newest')
  const [page, setPage] = useState(1)
  const [deleteTarget, setDeleteTarget] = useState<BrandListItem | null>(null)

  const handleBrandCreated = (brand: Brand) => {
    addBrand(brand)
    router.push(`/${brand.id}`)
  }

  // أعداد بطاقات الأرقام (من كل العلامات، مش من نتيجة الفلترة)
  const counts = useMemo<Record<StatusFilter, number>>(
    () => ({
      all: brands.length,
      in_progress: brands.filter((b) => b.kit_status === 'in_progress').length,
      complete: brands.filter((b) => b.kit_status === 'complete').length,
      not_started: brands.filter((b) => b.kit_status === 'not_started').length,
    }),
    [brands],
  )

 
  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    return brands
      .filter((b) => status === 'all' || b.kit_status === status)
      .filter((b) => !q || b.name.toLowerCase().includes(q))
      .sort((a, b) => {
        const diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        return sort === 'newest' ? -diff : diff
      })
  }, [brands, search, status, sort])

  // كل ما تغيّر الفلتر أو البحث أو الترتيب، بنرجع للصفحة الأولى
  const changeStatus = (next: StatusFilter) => { setStatus(next); setPage(1) }
  const changeSearch = (next: string) => { setSearch(next); setPage(1) }
  const changeSort = (next: BrandSort) => { setSort(next); setPage(1) }

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[30px] font-semibold leading-[1.16] tracking-tight">{t('brands')}</h1>
          <p className="mt-1 text-[14px] text-muted-foreground">
            {t('studio_summary', { count: brands.length })}
          </p>
        </div>
        <Button type="button" onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4" />{t('create_brand')}</Button>
      </div>

      {loading && <p className="mt-4 text-muted-foreground">{t('loading')}</p>}

      {error && <p className="mt-4 text-[13px] text-destructive">{error}</p>}

      {!loading && !error && brands.length === 0 && (
        <div className="mt-12 text-center">
          <p className="font-display text-[24px] text-muted-foreground">{t('no_studios_yet')}</p>
          <p className="mt-2 text-[14px] text-muted-foreground">{t('create_your_first_brand')}</p>
          <Button type="button" className="mt-6" onClick={() => setShowCreateModal(true)}>{t('create_brand2')}</Button>
        </div>
      )}

      {!loading && brands.length > 0 && (
        <>
          <BrandStats counts={counts} value={status} onChange={changeStatus} />

          {/* شريط البحث والفلاتر */}
          <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-brand-accent/30 bg-brand-cream p-4 shadow-xs">
            <div className="relative w-full sm:w-[288px]">
              <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-headline/40" />
              <input
                type="search"
                value={search}
                onChange={(e) => changeSearch(e.target.value)}
                placeholder={t('search_placeholder')}
                aria-label={t('search_placeholder')}
                className="h-10 w-full rounded-lg border border-brand-accent/30 bg-white ps-10 pe-3 font-readex text-[14px] text-brand-headline placeholder:text-brand-headline/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/40"
              />
            </div>
            <div className="relative w-full sm:w-auto">
              <select
                value={status}
                onChange={(e) => changeStatus(e.target.value as StatusFilter)}
                aria-label={t('all_statuses')}
                className={selectClass}
              >
                <option value="all">{t('all_statuses')}</option>
                <option value="in_progress">{t('filter_in_progress')}</option>
                <option value="complete">{t('filter_completed')}</option>
                <option value="not_started">{t('filter_pending')}</option>
              </select>
              <ChevronDown className="pointer-events-none absolute end-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-headline/50" />
            </div>
            <div className="relative w-full sm:w-auto">
              <select
                value={sort}
                onChange={(e) => changeSort(e.target.value as BrandSort)}
                aria-label={t('sort_newest')}
                className={selectClass}
              >
                <option value="newest">{t('sort_newest')}</option>
                <option value="oldest">{t('sort_oldest')}</option>
              </select>
              <ChevronDown className="pointer-events-none absolute end-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-headline/50" />
            </div>
          </div>

          {visible.length === 0 ? (
            <p className="mt-8 text-center text-[14px] text-muted-foreground">{t('no_results')}</p>
          ) : (
            <BrandsTable
              brands={visible}
              accents={accents}
              page={page}
              onPageChange={setPage}
              sort={sort}
              onToggleSort={() => changeSort(sort === 'newest' ? 'oldest' : 'newest')}
              onDelete={setDeleteTarget}
            />
          )}
        </>
      )}

      <CreateBrandModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        onBrandCreated={handleBrandCreated}
      />

      {deleteTarget && (
        <DeleteBrandDialog
          brand={deleteTarget}
          open
          onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
          onBrandDeleted={() => removeBrand(deleteTarget.id)}
        />
      )}
    </div>
  )
}