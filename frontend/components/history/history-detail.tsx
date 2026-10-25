'use client'

import { useTranslations } from 'next-intl'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { PLATFORM_PRESETS } from '@/lib/presets'
import { providerLabel } from '@/lib/providers'
import type { GenerationDetail, LogoMode } from '@/types'
import type { DeleteGenerationOutcome } from '@/hooks/use-delete-generation'
import { HistoryDownloadButton } from './history-download-button'
import { DeleteGenerationDialog } from './delete-generation-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Notice } from '@/components/ui/notice'

interface HistoryDetailProps {
  detail: GenerationDetail
  brandId: string
  backSearch?: string
  onDelete: () => Promise<DeleteGenerationOutcome>
  onDeleted: () => void
}

const LOGO_MODE_KEYS: Record<LogoMode, string> = {
  none: 'none',
  prompt: 'in_prompt',
  watermark: 'mark',
  both: 'both',
}

export function HistoryDetail({ detail, brandId, backSearch, onDelete, onDeleted }: HistoryDetailProps) {
  const t = useTranslations('components.history.history-detail')
  const tOpt = useTranslations('options')
  const tFilters = useTranslations('components.history.history-filters')
  const tLogo = useTranslations('components.generation.logo-mode-selector')
  const preset = PLATFORM_PRESETS[detail.platform_preset]
  const backHref = `/${brandId}/history${backSearch ? `?${backSearch}` : ''}`
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [imageUnavailable, setImageUnavailable] = useState(false)
  const showImage = Boolean(detail.image_url) && !imageUnavailable
  const shouldShowUnavailable = detail.status === 'succeeded' && !showImage

  useEffect(() => {
    setImageUnavailable(false)
  }, [detail.id, detail.image_url])

  async function handleConfirmDelete() {
    setDeleting(true)
    const outcome = await onDelete()
    setDeleting(false)
    if (outcome.ok) onDeleted()
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <Link
        href={backHref}
        className="inline-flex items-center gap-1 text-[13px] text-muted-foreground no-underline hover:text-brand"
      >
        <ArrowLeft className="h-3.5 w-3.5" />{t('back_to_history')}</Link>

      {showImage && (
        <div className="overflow-hidden rounded-xl border border-[rgba(15,23,42,.10)] shadow-art">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={detail.image_url ?? undefined}
            alt={detail.prompt}
            className="w-full"
            onError={() => setImageUnavailable(true)}
          />
        </div>
      )}

      {shouldShowUnavailable && (
        <div className="flex min-h-64 items-center justify-center rounded-lg border border-dashed bg-surface-sunken p-6 text-center text-[13px] text-muted-foreground">{t('image_unavailable_the_saved')}</div>
      )}

      <div className="flex flex-col gap-4">
        <div>
          <h3 className="text-[13px] font-medium text-muted-foreground">{t('prompt')}</h3>
          <p className="mt-1 break-words text-[14px]">{detail.prompt}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge variant="muted" className="normal-case tracking-normal">{providerLabel(detail.provider)}</Badge>
          <Badge variant="muted" className="normal-case tracking-normal">{preset ? tOpt(`preset_${detail.platform_preset}`) : detail.platform_preset}</Badge>
          <Badge
            variant={detail.status === 'failed' ? 'danger' : 'success'}
            className="normal-case tracking-normal"
          >
            {tFilters(detail.status)}
          </Badge>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Meta label={t('model')} value={detail.model} />
          <Meta label={t('dimensions')} value={`${detail.width} × ${detail.height}`} mono />
          <Meta label={t('logo_mode')} value={tLogo(LOGO_MODE_KEYS[detail.logo_mode])} />
          <Meta label={t('created')} value={new Date(detail.created_at).toLocaleString()} />
          {detail.completed_at && (
            <Meta label={t('completed')} value={new Date(detail.completed_at).toLocaleString()} />
          )}
        </div>

        {detail.status === 'failed' && detail.error_code && (
          <Notice variant="danger">{detail.error_message ?? detail.error_code}</Notice>
        )}
      </div>

      <div className="flex items-start gap-3">
        <HistoryDownloadButton
          imageUrl={detail.image_url}
          downloadFilename={detail.download_filename}
          disabled={imageUnavailable}
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => setDialogOpen(true)}
          className="border-destructive/30 text-destructive hover:bg-destructive/5"
        >
          {t('delete')}
        </Button>
      </div>

      <DeleteGenerationDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onConfirm={handleConfirmDelete}
        loading={deleting}
      />
    </div>
  )
}

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <h3 className="text-[13px] font-medium text-muted-foreground">{label}</h3>
      <p className={`mt-1 text-[14px] ${mono ? 'font-mono text-[13px]' : ''}`}>{value}</p>
    </div>
  )
}
