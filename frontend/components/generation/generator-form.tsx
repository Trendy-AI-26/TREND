// D:\Level4\TREND\frontend\components\generation\generator-form.tsx

'use client'

import { useTranslations } from 'next-intl';
import { useEffect, useRef, useState } from 'react'
import { Download, Loader2, Sparkles } from 'lucide-react'
import { useGenerate } from '@/hooks/use-generate'
import { LogoModeSelector } from '@/components/generation/logo-mode-selector'
import { PresetSelector } from '@/components/generation/preset-selector'
import { ProviderSelector } from '@/components/generation/provider-selector'
import { CanvasStage } from '@/components/generation/canvas-stage'
import { ErrorMessage } from '@/components/generation/error-message'
import { Button } from '@/components/ui/button'
import { downloadImageFile } from '@/lib/download'
import { PLATFORM_PRESETS } from '@/lib/presets'
import { providerLabel } from '@/lib/providers'
import { addGenerationNotification } from '@/hooks/use-notifications'
import type { LogoMode, PlatformPreset } from '@/types'
import {
  EMPTY_GENERATION_BRIEF,
  GenerationBriefForm,
} from '@/components/generation/generation-brief-form'
import type { GenerationBrief } from '@/types/generation'
import { CaptionPanel } from '@/components/generation/caption-panel'

interface GeneratorFormProps {
  brandId: string
  brandName: string
  brandHasLogo: boolean
}

export function GeneratorForm({ brandId, brandName, brandHasLogo }: GeneratorFormProps) {
  const t = useTranslations('components.generation.generator-form');
  const tOpt = useTranslations('options');
  const tNotifications = useTranslations('notifications');
  const [brief, setBrief] = useState<GenerationBrief>(EMPTY_GENERATION_BRIEF)
  const [briefReviewed, setBriefReviewed] = useState(false)
  const [preset, setPreset] = useState<PlatformPreset>('instagram_post')
  const [logoMode, setLogoMode] = useState<LogoMode>('none')
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const { state, generate, reset } = useGenerate(brandId)
  const notifiedGenerationRef = useRef<string | null>(null)

  const submitting = state.status === 'submitting'
  const generateDisabled = submitting || !briefReviewed

  const presetInfo = PLATFORM_PRESETS[preset]
  const canvasStatus =
    state.status === 'submitting' ? 'generating' : state.status === 'success' ? 'done' : 'empty'


  function handleBriefChange(nextBrief: GenerationBrief) {
    setBrief(nextBrief)
    setBriefReviewed(false)
  }

  function handlePresetChange(next: PlatformPreset) {
    if (state.status === 'success') reset()
    setPreset(next)
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (generateDisabled) return

    setDownloadError(null)

    await generate({
      brief,
      platform_preset: preset,
      logo_mode: logoMode,
    })
  }

  async function handleDownload() {
    if (state.status !== 'success') return

    const { result } = state
    if (!result.image_url || !result.download_filename) return

    setDownloading(true)
    setDownloadError(null)

    try {
      await downloadImageFile(result.image_url, result.download_filename)
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : t('download_failed_try_again'))
    } finally {
      setDownloading(false)
    }
  }

  const result = state.status === 'success' ? state.result : null
  const canDownload = Boolean(result?.image_url && result?.download_filename)

  useEffect(() => {
    if (state.status !== 'success' || notifiedGenerationRef.current === state.result.id) return
    notifiedGenerationRef.current = state.result.id
    addGenerationNotification(
      tNotifications('items.generation.title'),
      tNotifications('items.generation.description'),
      tNotifications('justNow'),
    )
  }, [state, tNotifications])

  return (
    <div className="grid gap-[22px] xl:grid-cols-[minmax(380px,460px)_1fr] xl:items-start">
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-4"
      >
        <div>
          <h1 className="text-[30px] font-semibold leading-[1.16] tracking-tight">{t('generate')}</h1>
          <p className="mt-1 text-[14px] text-muted-foreground">
            {t('matches_brand_identity', { brandName })}
          </p>
        </div>

        <div>
          <GenerationBriefForm
            value={brief}
            onChange={handleBriefChange}
            onComplete={(completedBrief) => {
              setBrief(completedBrief)
              setBriefReviewed(true)
            }}
            platformPreset={preset}
            brandId={brandId}
            brandName={brandName}
            disabled={submitting}
          />
        </div>

        <div className="space-y-3 border-t border-border-subtle pt-3">
          <PresetSelector value={preset} onChange={handlePresetChange} disabled={submitting} />

          <div className="grid gap-3 sm:grid-cols-2">
            <ProviderSelector disabled={submitting} />
            <LogoModeSelector
              value={logoMode}
              onChange={setLogoMode}
              brandHasLogo={brandHasLogo}
              brandId={brandId}
              disabled={submitting}
            />
          </div>

          <Button type="submit" size="lg" className="w-full" disabled={generateDisabled}>
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />{t('painting')}</>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />{t('generate2')}</>
            )}
          </Button>

          {state.status === 'error' && (
            <ErrorMessage code={state.code} message={state.message} brandId={brandId} />
          )}
        </div>
      </form>

      <div className="flex min-w-0 flex-col gap-3 xl:sticky xl:top-6">
        <CanvasStage
          status={canvasStatus}
          preset={presetInfo}
          brandName={brandName}
          imageUrl={result?.image_url}
          imageAlt={result?.prompt}
        />

        <div className="flex items-center justify-between gap-3">
          <p className="font-mono text-[12px] text-muted-foreground">
            {presetInfo.width} × {presetInfo.height} · {tOpt(`preset_${preset}`)} · {providerLabel(result?.provider ?? 'openai')}
          </p>
          <Button
            type="button"
            variant={canDownload ? 'default' : 'secondary'}
            onClick={handleDownload}
            disabled={!canDownload || downloading}
          >
            <Download className="h-4 w-4" />
            {downloading ? t('downloading') : t('download')}
          </Button>
        </div>

        {downloadError && <p className="text-[12px] text-destructive">{downloadError}</p>}
        <CaptionPanel
          key={result?.id ?? 'pending'}
          brandId={brandId}
          generationId={result?.id ?? null}
          language={result?.language ?? 'en'}
          enabled={!!result}
        />
      </div>
    </div>
  )
}
