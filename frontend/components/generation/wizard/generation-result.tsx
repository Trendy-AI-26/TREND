'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { CheckCircle2, Download, Loader2, Pencil, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { downloadImageFile } from '@/lib/download'
import { aspectRatioLabel } from '@/lib/presets'
import type { CaptionPreferences, GenerationResponse } from '@/types'
import { ResultCaption } from './result-caption'

interface GenerationResultProps {
  brandId: string
  result: GenerationResponse
  platformLabel: string
  withCaption: boolean
  captionPreferences: CaptionPreferences
  /** خيارات المستخدم الأساسية نعرضها كشارات صغيرة */
  basedOn: string[]
  onRegenerate: () => void
  onEditAnswers: () => void
}

export function GenerationResult({
  brandId,
  result,
  platformLabel,
  withCaption,
  captionPreferences,
  basedOn,
  onRegenerate,
  onEditAnswers,
}: GenerationResultProps) {
  const t = useTranslations('components.generation.wizard')
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  async function handleDownload() {
    if (!result.image_url) return
    setDownloading(true)
    setDownloadError(null)
    try {
      await downloadImageFile(result.image_url, result.download_filename ?? `trendy-${result.id}.png`)
    } catch {
      setDownloadError(t('download_failed'))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* شريط النجاح + الأزرار */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 rounded-[12px] bg-brand-primary/5 px-4 py-2.5">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-brand-primary" />
          <div>
            <p className="text-[13.5px] font-bold text-brand-headline">{t('result_success')}</p>
            <p className="text-[11.5px] text-brand-headline/50">
              {t('result_meta', { platform: platformLabel, width: result.width, height: result.height })}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={onEditAnswers}
            className="h-9 rounded-[9px] border-brand-accent/30 bg-white px-3.5 text-[12.5px] font-semibold text-brand-headline/80"
          >
            <Pencil />
            {t('edit_answers')}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={onRegenerate}
            className="h-9 rounded-[9px] border-brand-accent/30 bg-white px-3.5 text-[12.5px] font-semibold text-brand-headline/80"
          >
            <RefreshCw />
            {t('regenerate')}
          </Button>
        </div>
      </div>

      <div className={withCaption ? 'grid items-start gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]' : ''}>
        {/* بطاقة التصميم */}
        <section className="rounded-[16px] border border-brand-accent/20 bg-white p-5 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <h3 className="text-[15px] font-bold text-brand-headline">{t('result_design')}</h3>
              <span dir="ltr" className="rounded-full bg-brand-primary/10 px-2 py-0.5 text-[10.5px] font-bold text-brand-primary">
                {aspectRatioLabel(result.width, result.height)}
              </span>
            </div>
            <span className="text-[11.5px] text-brand-headline/40">{t('result_ready')}</span>
          </div>

          <div className="mt-4 flex items-center justify-center rounded-[12px] bg-brand-cream/70 p-3">
            {result.image_url && (
              // eslint-disable-next-line @next/next/no-img-element -- رابط موقّع مؤقت من التخزين
              <img
                src={result.image_url}
                alt={t('image_alt')}
                width={result.width}
                height={result.height}
                className="h-auto max-h-[560px] w-auto max-w-full rounded-[8px] shadow-[0_4px_20px_rgba(0,0,0,0.08)]"
              />
            )}
          </div>

          <Button
            type="button"
            onClick={handleDownload}
            disabled={downloading || !result.image_url}
            className="mt-4 h-11 w-full rounded-[10px] bg-brand-primary text-[13.5px] font-bold text-white hover:bg-brand-primary/90"
          >
            {downloading ? <Loader2 className="animate-spin" /> : <Download />}
            {downloading ? t('downloading') : t('download_png')}
          </Button>
          {downloadError && (
            <p role="alert" className="mt-2 text-[11.5px] text-destructive">
              {downloadError}
            </p>
          )}

          {basedOn.length > 0 && (
            <div className="mt-5 border-t border-brand-accent/15 pt-4">
              <p className="text-[11.5px] font-semibold text-brand-headline/50">{t('based_on')}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {basedOn.map((label) => (
                  <span
                    key={label}
                    className="rounded-full border border-brand-accent/25 bg-brand-cream px-2.5 py-1 text-[11.5px] font-medium text-brand-headline/80"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* بطاقة الكابشن */}
        {withCaption && (
          <ResultCaption
            key={result.id}
            brandId={brandId}
            generationId={result.id}
            preferences={captionPreferences}
          />
        )}
      </div>
    </div>
  )
}