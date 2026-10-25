'use client'

import Image from 'next/image'
import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl';
import { Check, Info } from 'lucide-react'
import { KitQuestion } from '@/components/kit/kit-question'
import { Notice } from '@/components/ui/notice'
import { apiRequest } from '@/lib/api'
import { formatHex, normalizeHex } from '@/components/brand/brand-workspace'
import type { KitAnswers, KitStatus, ProductAssetResponse } from '@/types'

interface StepReviewProps {
  brandId: string
  answers: KitAnswers
  onChange: (partial: Partial<KitAnswers>) => void
  brandName: string
  savedStatus: KitStatus
  isDirty: boolean
  logoUrl: string | null
}

export function StepReview({
  brandId,
  answers,
  brandName,
  savedStatus,
  isDirty,
  logoUrl,
}: StepReviewProps) {
  const t = useTranslations('components.kit.steps.step-review');
  const tIndustry = useTranslations('components.kit.steps.step-industry');
  const none = t('none_value')
  const industryOptions = ['beauty', 'fashion', 'perfume', 'food', 'retail', 'home', 'services', 'jewelry', 'other']

  const missingRequired: string[] = []
  if (!answers.industry?.trim() || answers.industry === 'other') missingRequired.push(t('industry'))
  if (!answers.audience || answers.audience.trim().length < 2) missingRequired.push(t('missing_audience'))
  if (!answers.colors || answers.colors.length === 0) missingRequired.push(t('missing_colors'))

  const hasSaved = !isDirty && savedStatus !== 'not_started'
  const industryLabel = answers.industry
    ? industryOptions.includes(answers.industry)
      ? tIndustry(answers.industry)
      : answers.industry
    : none
  return (
    <div className="space-y-6">
      <KitQuestion
        align="center"
        before={t('ready_to_prefix')}
        emphasis={t('save_word')}
        helper={t('review_help', { brandName })}
      />

      {missingRequired.length > 0 && (
        <Notice variant="warning">
          <p className="font-medium">{t('still_missing', { items: missingRequired.join(', ') })}</p>
          <p className="mt-1">{t('you_can_save_now')}</p>
        </Notice>
      )}

      <div className="overflow-hidden rounded-xl border border-brand-accent/20 bg-white">
        <div className="flex items-center justify-between border-b border-brand-accent/15 px-4 py-3">
          <h3 className="font-tajawal text-[13px] font-semibold text-brand-headline">{t('identity_summary')}</h3>
          <span className="font-tajawal text-[11px] text-muted-foreground">{t('required_summary', { complete: 3 - missingRequired.length, total: 3 })}</span>
        </div>
        <div className="divide-y divide-brand-accent/10">
          <ReviewRow label={t('tagline')} value={answers.tagline || none} />
          <ReviewRow label={t('industry')} value={industryLabel} required={!answers.industry?.trim() || answers.industry === 'other'} missingLabel={t('required_field_missing')} />
          <ReviewRow label={t('audience')} value={answers.audience || none} required={!answers.audience || answers.audience.trim().length < 2} missingLabel={t('required_field_missing')} />
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
            <span className="font-tajawal text-[12px] font-medium text-brand-headline">{t('colors')}</span>
            <div className="flex flex-wrap items-center gap-3">
              {answers.colors.map((color, index) => {
                const hex = normalizeHex(color) ? formatHex(color) : color
                return (
                  <span key={`${color}-${index}`} className="inline-flex items-center gap-1.5" title={hex}>
                    <span className="h-4 w-4 rounded-[4px] border border-black/10" style={{ background: hex }} />
                    <span className="font-mono text-[11px] text-brand-headline/75">{hex}</span>
                  </span>
                )
              })}
              {answers.colors.length === 0 && <span className="font-tajawal text-[12px] text-muted-foreground">{none}</span>}
            </div>
            {answers.colors.length === 0 && <MissingMark label={t('required_field_missing')} />}
          </div>
          <ReviewRow label={t('avoid')} value={answers.avoid_words || none} />
        </div>
      </div>

      <div className="rounded-lg border border-brand-accent/20 bg-white p-4">
        <p className="mb-3 font-tajawal text-[13px] font-semibold text-brand-headline">{t('brand_logo')}</p>
        {logoUrl ? (
          <Image src={logoUrl} alt={t('brand_logo_alt', { brandName })} width={160} height={120} unoptimized className="h-[120px] w-[160px] rounded-md border border-brand-accent/15 object-contain" />
        ) : (
          <p className="font-tajawal text-[12px] text-muted-foreground">{none}</p>
        )}
      </div>

      {answers.product_asset_id && (
        <div className="rounded-lg border border-brand-accent/20 bg-white p-4">
          <p className="mb-3 font-tajawal text-[13px] font-semibold text-brand-headline">{t('product_image')}</p>
          <ProductAssetPreview brandId={brandId} brandName={brandName} assetId={answers.product_asset_id} />
        </div>
      )}

      {hasSaved && savedStatus === 'complete' && (
        <Notice variant="success">{t('brand_kit_saved_complete')}</Notice>
      )}

      {hasSaved && savedStatus === 'in_progress' && (
        <Notice variant="warning">{t('brand_kit_saved_in')}</Notice>
      )}
    </div>
  )
}

function ProductAssetPreview({ brandId, brandName, assetId }: { brandId: string; brandName: string; assetId: string }) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const t = useTranslations('components.kit.steps.step-logo')

  useEffect(() => {
    let cancelled = false
    apiRequest<ProductAssetResponse>(`/brands/${brandId}/product-assets/${assetId}`)
      .then((asset) => { if (!cancelled) setImageUrl(asset.image_url) })
      .catch(() => { })
    return () => { cancelled = true }
  }, [brandId, assetId])

  if (!imageUrl) return null
  return <Image src={imageUrl} alt={t('product_image_alt', { brandName })} width={160} height={120} unoptimized className="h-[120px] w-[160px] rounded-md border border-brand-accent/15 object-contain" />
}

function ReviewRow({ label, value, required = false, missingLabel = '' }: { label: string; value: string; required?: boolean; missingLabel?: string }) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3">
      <span className="font-tajawal text-[12px] font-medium text-brand-headline">{label}</span>
      <span className="ms-auto min-w-0 break-words whitespace-pre-line text-end font-tajawal text-[12px] text-brand-headline/75">{value}</span>
      {required && <MissingMark label={missingLabel} />}
      {!required && value !== '—' && <Check className="h-3.5 w-3.5 shrink-0 text-emerald-700" aria-hidden="true" />}
    </div>
  )
}

function MissingMark({ label }: { label: string }) {
  return <span className="inline-flex shrink-0 items-center gap-1 font-tajawal text-[10px] text-amber-700"><Info className="h-3 w-3" />{label}</span>
}
