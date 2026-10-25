'use client'

import Link from 'next/link'
import { useLocale, useTranslations } from 'next-intl'
import {
  ArrowUpLeft,
  Bell,
  CheckCircle2,
  Clock3,
  Heart,
  ImagePlus,
  Sparkle,
  Sparkles,
} from 'lucide-react'
import { useBrand } from '@/hooks/use-brand'
import { useGenerationHistory } from '@/hooks/use-generation-history'
import { useKit } from '@/hooks/use-kit'
import { useProfile } from '@/hooks/use-profile'
import { useBrands } from '@/hooks/use-brands'

import type { GenerationHistoryItem } from '@/types'
import { useQuota } from '@/hooks/use-quota'

interface BrandDashboardProps {
  brandId: string
}

const panelClass =
  'rounded-xl border border-brand-accent/15 bg-white shadow-[0_1px_8px_rgba(0,0,0,0.035)]'

export function BrandDashboard({ brandId }: BrandDashboardProps) {
  const t = useTranslations('app.(dashboard).[brandId].page')
  const locale = useLocale()
  const { profile } = useProfile()
  const { brands } = useBrands()
  const { brand, loading: brandLoading, error: brandError } = useBrand(brandId)
  const { kit, loading: kitLoading, error: kitError } = useKit(brandId)
  const {
    items,
    loading: historyLoading,
    error: historyError,
    hasNext,
  } = useGenerationHistory(brandId)
  const { quota, loading: quotaLoading, error: quotaError, refetch: refetchQuota } = useQuota()
  const quotaUnavailable = quotaLoading || !!quotaError || !quota
  const quotaStatus = quotaLoading ? t('loading') : t('quota_load_failed')

  const answers = kit?.answers
  const completedSections = [
    Boolean(answers?.tagline?.trim()),
    Boolean(answers?.audience?.trim()),
    (answers?.colors.length ?? 0) > 0,
    Boolean(answers?.avoid_words?.trim()),
    Boolean(answers?.industry?.trim()),
    Boolean(answers?.product_asset_id),
  ].filter(Boolean).length
  const completion = Math.round((completedSections / 6) * 100)
  const latestItems = items.slice(0, 3)
  const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000
  const recentItems = items.filter((item) => new Date(item.created_at).getTime() >= thirtyDaysAgo)
  const savedRecentCount = recentItems.filter(
    (item) => item.status === 'succeeded' && Boolean(item.image_url),
  ).length
  const generationLimit = quota?.daily_generation_limit ?? 3
  const generationConsumed = quota?.daily_generation_consumed ?? 0
  const generationRemaining = quota?.daily_generation_remaining ?? 0
  const usageProgress = generationLimit > 0
    ? Math.min(100, Math.round((generationConsumed / generationLimit) * 100))
    : 0
  const usageRingCircumference = 2 * Math.PI * 43
  const userName =
    profile?.full_name?.trim() || profile?.email.split('@')[0] || t('user_name_fallback')

  function formatDate(value: string) {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value))
  }

  return (
    <div className="mx-auto w-full max-w-[1120px] space-y-5 pb-10 font-readex">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-heading text-[30px] font-bold leading-tight text-brand-headline">
            {t('welcome', { name: userName })}
          </h1>
          <p className="mt-1 text-[14px] text-brand-headline/55">
            {t('subtitle')}
          </p>
        </div>
        <span className="inline-flex h-10 items-center gap-2 rounded-lg border border-brand-accent/30 bg-white px-4 text-[13px] font-semibold text-brand-headline">
          <Clock3 className="h-4 w-4" />
          {t('recent_period')}
        </span>
      </header>

      <section className="flex flex-wrap items-center justify-between gap-5 rounded-2xl bg-gradient-to-l from-[#74151b] via-[#8b1726] to-[#a32037] px-6 py-5 text-white shadow-[0_8px_24px_rgba(122,21,33,0.16)] sm:px-8">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-amber-200" />
            <h2 className="text-[20px] font-bold">{t('banner_title')}</h2>
          </div>
          <p className="mt-1 max-w-xl text-[13px] leading-6 text-white/75">
            {t('banner_description')}
          </p>
        </div>
        <Link
          href={`/${brandId}/generate`}
          className="inline-flex h-10 shrink-0 items-center gap-2 rounded-lg bg-white px-4 text-[13px] font-bold text-[#74151b] no-underline transition-transform hover:-translate-y-0.5"
        >
          {t('create_design')}
          <ArrowUpLeft className="h-4 w-4 rtl:rotate-180" />
        </Link>
      </section>

      {(brandError || kitError || historyError || quotaError) && (
        <div
          role="alert"
          className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-[13px] text-destructive"
        >
          {[brandError, kitError, historyError, quotaError ? t('quota_load_failed') : null].filter(Boolean).join(' · ')}
          {quotaError && (
            <button type="button" onClick={refetchQuota} disabled={quotaLoading} className="ms-3 rounded-lg border border-current px-3 py-1 disabled:opacity-50">
              {t('quota_retry')}
            </button>
          )}
        </div>
      )}

      <section
        dir={locale === 'ar' ? 'rtl' : 'ltr'}
        className="grid grid-cols-1 gap-3 sm:grid-cols-3"
        aria-label={t('overview')}
      >
        <MetricCard
          icon={<Sparkle className="h-5 w-5" />}
          label={t('executed_designs')}
          value={historyLoading ? '—' : `${savedRecentCount}${hasNext ? '+' : ''}`}
          note={t('designs_ready_for_use')}
          accent="text-amber-500 bg-emerald-50"
          noteAccent="text-emerald-600"
        />
        <MetricCard
          icon={<Bell className="h-5 w-5" />}
          label={t('generated_content')}
          value={quotaUnavailable ? '—' : `${generationConsumed}/${generationLimit}`}
          note={t('content_includes_image_caption')}
          accent="text-brand-headline/70 bg-brand-bg/45"
          noteAccent="text-brand-headline/45"
        />
        <MetricCard
          icon={<Heart className="h-5 w-5" />}
          label={t('active_brands')}
          value={quotaUnavailable ? '—' : `${brands.length}/${quota.max_active_brands}`}
          note={t('active_brands_limit', { total: quota?.max_active_brands ?? 0 })}
          accent="text-purple-500 bg-purple-50"
          noteAccent="text-brand-headline/45"
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_.72fr]">
        <article className={`${panelClass} p-5 sm:p-6`}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-[16px] font-bold text-brand-headline">{t('brand_identity')}</h2>
              <p className="mt-1 text-[12px] text-brand-headline/50">{t('brand_identity_note')}</p>
            </div>
            <span
              className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold ${kit?.status === 'complete'
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-amber-50 text-amber-700'
                }`}
            >
              {kitLoading ? t('loading') : t(`kit_status.${kit?.status ?? 'not_started'}`)}
            </span>
          </div>

          <div className="mt-5 flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-brand-weaker text-[17px] font-bold text-brand-primary">
              {brand?.logo_url ? (
                <img src={brand.logo_url} alt="" className="h-full w-full object-cover" />
              ) : (
                brand?.name?.slice(0, 1) ?? 'T'
              )}
            </div>
            <div className="min-w-0">
              <p className="truncate text-[15px] font-bold text-brand-headline">
                {brandLoading ? t('loading') : brand?.name ?? 'TRENDY AI'}
              </p>
              <p className="mt-0.5 text-[12px] text-brand-headline/50">
                {t('identity_completion', { count: completedSections, total: 6 })}
              </p>
            </div>
            <Link
              href={`/${brandId}/kit`}
              className="ms-auto shrink-0 rounded-lg border border-brand-accent/25 px-3 py-2 text-[12px] font-semibold text-brand-primary no-underline hover:bg-brand-weaker"
            >
              {t('edit_identity')}
            </Link>
          </div>

          <div className="mt-5 h-2 overflow-hidden rounded-full bg-brand-bg/70">
            <div
              className="h-full rounded-full bg-brand-primary transition-[width]"
              style={{ width: `${completion}%` }}
            />
          </div>

          <div className="mt-4 flex items-center justify-between gap-3">
            <p className="text-[12px] text-brand-headline/55">{t('brand_colors')}</p>
            <div className="flex items-center gap-1.5" aria-label={t('saved_colors')}>
              {(answers?.colors ?? []).slice(0, 6).map((color, index) => (
                <span
                  key={`${color}-${index}`}
                  className="h-4 w-4 rounded-full border border-black/10"
                  style={{ backgroundColor: color }}
                  title={color}
                />
              ))}
              {!kitLoading && !answers?.colors.length && (
                <span className="text-[11px] text-brand-headline/40">{t('no_colors')}</span>
              )}
            </div>
          </div>
        </article>

        <article dir={locale === 'ar' ? 'rtl' : 'ltr'} className={`${panelClass} p-5 sm:p-6`}>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-[16px] font-bold text-brand-headline">{t('free_usage_title')}</h2>
            <span className="shrink-0 rounded-full border border-[#f4dadd] bg-[#fff5f6] px-3 py-1.5 text-[12px] font-semibold text-[#8b1726]">
              {quotaLoading || !quota
                ? '—'
                : t('free_usage_counter', {
                  used: generationConsumed,
                  total: generationLimit,
                })}
            </span>
          </div>

          <div className="mt-5 flex min-h-[132px] items-center justify-between gap-5 rounded-2xl border border-[#eee7e7] bg-[#faf8f8] px-4 py-5 sm:px-6">
            <div
              className="relative h-[88px] w-[88px] shrink-0"
              role="img"
              aria-label={
                quotaLoading || !quota
                  ? quotaStatus
                  : t('free_usage_counter', {
                    used: generationConsumed,
                    total: generationLimit,
                  })
              }
            >
              <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
                <circle cx="50" cy="50" r="43" fill="none" stroke="#f2dcde" strokeWidth="8" />
                <circle
                  cx="50"
                  cy="50"
                  r="43"
                  fill="none"
                  stroke="#8b1726"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={usageRingCircumference}
                  strokeDashoffset={
                    usageRingCircumference * (1 - usageProgress / 100)
                  }
                />
              </svg>
              <span className="absolute inset-0 flex flex-col items-center justify-center text-brand-headline">
                <span className="text-[22px] font-bold leading-none">
                  {quotaLoading || !quota
                    ? '—'
                    : generationConsumed}
                </span>
                <span className="mt-1 text-[10px] text-brand-headline/45">
                  {quotaUnavailable ? '—' : t('free_usage_total', { total: generationLimit })}
                </span>
              </span>
            </div>
            <p className="min-w-0 flex-1 text-[13px] leading-6 text-brand-headline/65">
              {quotaLoading || !quota
                ? quotaStatus
                : generationRemaining === 0
                  ? t('free_usage_exhausted', { total: generationLimit })
                  : t('free_usage_remaining', {
                    remaining: generationRemaining,
                    total: generationLimit,
                  })}
            </p>
          </div>

          <div className="mt-4 flex justify-start">
            <Link
              href="/#pricing"
              className="inline-flex h-11 items-center justify-center rounded-xl bg-[#8b1726] px-6 text-[13px] font-bold text-white no-underline transition-colors hover:bg-[#74151b]"
            >
              {t('free_usage_plans')}
            </Link>
          </div>
        </article>
      </section>

      <section>
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <h2 className="text-[17px] font-bold text-brand-headline">{t('recent_designs')}</h2>
            <p className="mt-1 text-[12px] text-brand-headline/50">{t('recent_designs_note')}</p>
          </div>
          <Link
            href={`/${brandId}/history`}
            className="text-[12px] font-semibold text-brand-primary no-underline hover:underline"
          >
            {t('view_all')}
          </Link>
        </div>

        {historyLoading ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[0, 1, 2].map((index) => (
              <div key={index} className={`${panelClass} h-[210px] animate-pulse bg-white`} />
            ))}
          </div>
        ) : latestItems.length > 0 ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {latestItems.map((item) => (
              <DesignCard key={item.id} item={item} brandId={brandId} formatDate={formatDate} t={t} />
            ))}
          </div>
        ) : (
          <div className={`${panelClass} px-5 py-8 text-center text-[13px] text-brand-headline/50`}>
            {t('no_designs')}
          </div>
        )}
      </section>

      <section className={panelClass}>
        <div className="flex items-center justify-between gap-3 border-b border-brand-accent/15 px-5 py-4">
          <div>
            <h2 className="text-[16px] font-bold text-brand-headline">{t('latest_activity')}</h2>
            <p className="mt-1 text-[12px] text-brand-headline/50">{t('latest_activity_note')}</p>
          </div>
          <Link
            href={`/${brandId}/history`}
            className="text-[12px] font-semibold text-brand-primary no-underline hover:underline"
          >
            {t('view_library')}
          </Link>
        </div>
        {historyLoading ? (
          <p className="py-8 text-center text-[13px] text-brand-headline/45">{t('loading')}</p>
        ) : latestItems.length > 0 ? (
          <div className="divide-y divide-brand-accent/15 px-5">
            {latestItems.map((item) => (
              <ActivityRow key={item.id} item={item} brandId={brandId} formatDate={formatDate} t={t} />
            ))}
          </div>
        ) : (
          <div className="px-5 py-6 text-center">
            <p className="text-[13px] text-brand-headline/55">{t('no_activity')}</p>
            <Link
              href={`/${brandId}/generate`}
              className="mt-3 inline-flex text-[12px] font-bold text-brand-primary no-underline hover:underline"
            >
              {t('create_first_design')}
            </Link>
          </div>
        )}
      </section>
    </div>
  )
}

function MetricCard({
  icon,
  label,
  value,
  note,
  accent,
  noteAccent,
}: {
  icon: React.ReactNode
  label: string
  value: string
  note: string
  accent: string
  noteAccent: string
}) {
  return (
    <article className={`${panelClass} relative min-h-[116px] rounded-2xl p-4`}>
      <div className="min-w-0 ps-14 pt-1 text-start">
        <p className="truncate text-[14px] leading-5 text-brand-headline/55">{label}</p>
        <p className="mt-1 text-[30px] font-bold leading-none text-brand-headline">{value}</p>
      </div>
      <span className={`absolute start-4 top-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl ${accent}`}>
        {icon}
      </span>
      <p className={`mt-2 text-start text-[12px] ${noteAccent}`}>{note}</p>
    </article>
  )
}

function ActivityRow({
  item,
  brandId,
  formatDate,
  t,
}: {
  item: GenerationHistoryItem
  brandId: string
  formatDate: (date: string) => string
  t: ReturnType<typeof useTranslations<'app.(dashboard).[brandId].page'>>
}) {
  const succeeded = item.status === 'succeeded'
  return (
    <Link
      href={`/${brandId}/history/${item.id}`}
      className="flex items-center gap-3 py-3 text-brand-headline no-underline hover:bg-brand-cream/50"
    >
      <span
        className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${succeeded ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'
          }`}
      >
        {succeeded ? <CheckCircle2 className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[12px] font-semibold">{item.prompt_excerpt}</span>
        <span className="mt-1 block text-[10px] text-brand-headline/45">{formatDate(item.created_at)}</span>
      </span>
      <span className="shrink-0 text-[10px] text-brand-headline/50">
        {succeeded ? t('status.succeeded') : t('status.failed')}
      </span>
    </Link>
  )
}

function DesignCard({
  item,
  brandId,
  formatDate,
  t,
}: {
  item: GenerationHistoryItem
  brandId: string
  formatDate: (date: string) => string
  t: ReturnType<typeof useTranslations<'app.(dashboard).[brandId].page'>>
}) {
  return (
    <Link
      href={`/${brandId}/history/${item.id}`}
      className={`${panelClass} group overflow-hidden text-brand-headline no-underline transition-shadow hover:shadow-md`}
    >
      <div className="relative aspect-[1.7/1] overflow-hidden bg-neutral-100">
        {item.image_url ? (
          <img
            src={item.image_url}
            alt={item.prompt_excerpt}
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-brand-primary/50">
            <ImagePlus className="h-8 w-8" />
          </div>
        )}
        <span
          className={`absolute start-3 top-3 rounded-full px-2 py-1 text-[10px] font-bold ${item.status === 'succeeded'
            ? 'bg-white/90 text-emerald-700'
            : 'bg-white/90 text-amber-700'
            }`}
        >
          {item.status === 'succeeded' ? t('status.succeeded') : t('status.failed')}
        </span>
      </div>
      <div className="p-3.5">
        <p className="line-clamp-2 min-h-10 text-[12px] font-bold leading-5">{item.prompt_excerpt}</p>
        <p className="mt-2 text-[10px] text-brand-headline/45">{formatDate(item.created_at)}</p>
      </div>
    </Link>
  )
}
