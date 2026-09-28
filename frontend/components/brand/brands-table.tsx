'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useLocale, useTranslations } from 'next-intl'
import { ArrowUpDown, ExternalLink, Pencil, Trash2 } from 'lucide-react'
import { normalizeHex, TRENDY_AI_ACCENT } from '@/components/brand/brand-workspace'
import { cn } from '@/lib/utils'
import type { BrandListItem, KitStatus } from '@/types'

/** عدد الصفوف بكل صفحة (Figma: 5) */
export const PAGE_SIZE = 5

export type BrandSort = 'newest' | 'oldest'

interface BrandsTableProps {
  /** القائمة بعد الفلترة والترتيب (الجدول بيقصّها لصفحات لحاله) */
  brands: BrandListItem[]
  accents: Record<string, string>
  page: number
  onPageChange: (page: number) => void
  sort: BrandSort
  onToggleSort: () => void
  onDelete: (brand: BrandListItem) => void
}

const STATUS_STYLES: Record<KitStatus, string> = {
  complete: 'bg-brand-primary/10 text-brand-primary',
  in_progress: 'bg-brand-accent/20 text-[#8c6d3f]',
  not_started: 'bg-brand-bg text-brand-headline/60',
}

const STATUS_LABELS: Record<KitStatus, string> = {
  complete: 'status_complete',
  in_progress: 'status_in_progress',
  not_started: 'status_pending',
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`
}

const iconButton =
  'inline-flex h-8 w-8 items-center justify-center rounded-full opacity-70 transition hover:bg-brand-bg/60 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/40'

export function BrandsTable({
  brands,
  accents,
  page,
  onPageChange,
  sort,
  onToggleSort,
  onDelete,
}: BrandsTableProps) {
  const t = useTranslations('components.brand.brands-table')
  const locale = useLocale()
  const nf = new Intl.NumberFormat(locale)

  const total = brands.length
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const current = Math.min(page, totalPages)
  const start = (current - 1) * PAGE_SIZE
  const rows = brands.slice(start, start + PAGE_SIZE)

  return (
    <div className="mt-4 overflow-hidden rounded-2xl border border-brand-accent/30 bg-brand-cream font-readex shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-start">
          <thead>
            <tr className="border-b border-brand-accent/30 bg-brand-bg/40 text-[12px] font-bold text-brand-headline">
              <th scope="col" className="px-6 py-4 text-start">{t('col_brand')}</th>
              <th scope="col" className="px-6 py-4 text-start">{t('col_actions')}</th>
              <th scope="col" className="px-6 py-4 text-center">{t('col_status')}</th>
              <th scope="col" className="px-6 py-4 text-end">
                <button
                  type="button"
                  onClick={onToggleSort}
                  aria-label={sort === 'newest' ? t('sort_newest_hint') : t('sort_oldest_hint')}
                  className="inline-flex items-center gap-1.5 font-bold hover:text-brand-primary"
                >
                  {t('col_created')}
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((brand) => {
              const hex = normalizeHex(accents[brand.id] ?? '')
              const color = hex ? `#${hex}` : TRENDY_AI_ACCENT
              return (
                <tr key={brand.id} className="border-t border-brand-accent/20 first:border-t-0">
                  {/* العلامة: مربع بحرف/شعار + الاسم + كود اللون */}
                  <td className="px-6 py-[17px]">
                    <div className="flex items-center gap-3">
                      <span
                        className="inline-flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg text-[14px] font-bold"
                        style={{
                          backgroundColor: `color-mix(in srgb, ${color} 15%, white)`,
                          color,
                        }}
                      >
                        {brand.logo_url ? (
                          <Image
                            src={brand.logo_url}
                            alt=""
                            width={36}
                            height={36}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          brand.name.trim().charAt(0).toUpperCase()
                        )}
                      </span>
                      <div className="min-w-0">
                        <Link
                          href={`/${brand.id}`}
                          className="block truncate text-[14px] font-bold text-brand-headline no-underline hover:underline"
                        >
                          {brand.name}
                        </Link>
                        <span
                          dir="ltr"
                          className="block text-start text-[12px] tracking-[0.3px] text-brand-headline/45"
                        >
                          {hex ? `#${hex}` : '—'}
                        </span>
                      </div>
                    </div>
                  </td>

                  {/* الإجراءات: فتح ← تعديل ← حذف */}
                  <td className="px-6 py-[17px]">
                    <div className="flex items-center gap-1">
                      <Link
                        href={`/${brand.id}`}
                        className={cn(iconButton, 'text-brand-headline')}
                        title={t('action_open')}
                        aria-label={t('action_open')}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Link>
                      <Link
                        href={`/${brand.id}/settings`}
                        className={cn(iconButton, 'text-brand-headline')}
                        title={t('action_edit')}
                        aria-label={t('action_edit')}
                      >
                        <Pencil className="h-4 w-4" />
                      </Link>
                      <button
                        type="button"
                        onClick={() => onDelete(brand)}
                        className={cn(iconButton, 'text-brand-primary')}
                        title={t('action_delete')}
                        aria-label={t('action_delete')}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>

                  {/* الحالة */}
                  <td className="px-6 py-[17px] text-center">
                    <span
                      className={cn(
                        'inline-flex items-center rounded-full px-3 py-1 text-[12px] font-medium',
                        STATUS_STYLES[brand.kit_status],
                      )}
                    >
                      {t(STATUS_LABELS[brand.kit_status])}
                    </span>
                  </td>

                  {/* تاريخ الإنشاء */}
                  <td className="px-6 py-[17px] text-end text-[14px] text-brand-headline/70">
                    {formatDate(brand.created_at)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

    
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-brand-accent/30 px-6 py-3">
        <p className="text-[12px] text-brand-headline/60">
          {t('showing', {
            count: total,
            from: nf.format(total === 0 ? 0 : start + 1),
            to: nf.format(start + rows.length),
            total: nf.format(total),
          })}
        </p>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onPageChange(current - 1)}
            disabled={current <= 1}
            className="rounded-lg border border-brand-accent/30 px-[11px] py-[7px] text-[12px] text-brand-headline/80 transition-colors hover:bg-brand-bg/60 disabled:opacity-40 disabled:hover:bg-transparent"
          >
            {t('prev')}
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => onPageChange(n)}
              aria-current={n === current ? 'page' : undefined}
              className={cn(
                'h-8 w-8 rounded-lg text-[12px] font-medium transition-colors',
                n === current
                  ? 'bg-brand-primary text-white'
                  : 'text-brand-headline/80 hover:bg-brand-bg/60',
              )}
            >
              {nf.format(n)}
            </button>
          ))}
          <button
            type="button"
            onClick={() => onPageChange(current + 1)}
            disabled={current >= totalPages}
            className="rounded-lg border border-brand-accent/30 px-[11px] py-[7px] text-[12px] text-brand-headline/80 transition-colors hover:bg-brand-bg/60 disabled:opacity-40 disabled:hover:bg-transparent"
          >
            {t('next')}
          </button>
        </div>
      </div>
    </div>
  )
}