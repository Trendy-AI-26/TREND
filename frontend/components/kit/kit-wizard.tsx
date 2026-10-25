'use client'

import { useLocale, useTranslations } from 'next-intl';
import { useState, useCallback, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import type { CSSProperties } from 'react'
import { ArrowLeft, Check } from 'lucide-react'
import { saveKit } from '@/hooks/use-kit'
import { useBrands } from '@/hooks/use-brands'
import { KitAnswers, BrandKit, KitStatus } from '@/types'
import { StepName } from './steps/step-name'
import { StepLogo } from './steps/step-logo'
import { StepTagline } from './steps/step-tagline'
import { StepIndustry } from './steps/step-industry'
import { StepAudience } from './steps/step-audience'
import { StepColors } from './steps/step-colors'
import { StepAvoidWords } from './steps/step-avoid-words'
import { StepReview } from './steps/step-review'
import { isKitColor } from '@/components/brand/brand-workspace'
import { Button } from '@/components/ui/button'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { toast } from 'sonner'
import { errorMessage } from '@/lib/errors'
import { cn } from '@/lib/utils'

interface KitWizardProps {
  brandId: string
  brandName: string
  initialKit: BrandKit
}

const STEP_KEYS = [
  'step_logo',
  'step_brand',
  'step_tagline',
  'step_industry',
  'step_audience',
  'step_colors',
  'step_avoid',
  'step_review',
] as const

export function KitWizard({ brandId, brandName, initialKit }: KitWizardProps) {
  const t = useTranslations('components.kit.kit-wizard');
  const tc = useTranslations('confirm');
  const tt = useTranslations('toasts');
  const te = useTranslations('errors');
  const confirm = useConfirm()
  const locale = useLocale()
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<KitAnswers>(initialKit.answers)
  const [savedStatus, setSavedStatus] = useState<KitStatus>(initialKit.status)
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const router = useRouter()
  const { setAccent, updateBrand } = useBrands()
  const persistedColor = useRef(initialKit.answers.colors[0] ?? null)

  const handleChange = useCallback((partial: Partial<KitAnswers>) => {
    setAnswers(prev => ({ ...prev, ...partial }))
    setIsDirty(true)
  }, [])

  useEffect(() => {
    const next = answers.colors[0]
    if (next && isKitColor(next)) setAccent(brandId, next)
  }, [answers.colors, brandId, setAccent])

  useEffect(() => {
    return () => {
      setAccent(brandId, persistedColor.current)
    }
  }, [brandId, setAccent])

  const handleSave = async () => {
    if (saving) return
    setSaving(true)
    try {
      const saved = await saveKit(brandId, {
        ...answers,
        industry: answers.industry === 'other' ? null : answers.industry,
      })
      setSavedStatus(saved.status)
      setIsDirty(false)
      persistedColor.current = saved.answers.colors[0] ?? null
      if (saved.answers.colors[0]) setAccent(brandId, saved.answers.colors[0])
      updateBrand({ id: brandId, kit_status: saved.status })
      router.refresh()
      toast.success(tt('kitSaved'))
    } catch (e) {
      toast.error(errorMessage(e, te))
    } finally {
      setSaving(false)
    }
  }

  const leavingRef = useRef(false)

  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => {
      // The custom confirm dialog already asked; do not stack the browser prompt on top.
      if (leavingRef.current) return
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])

  const isDirtyRef = useRef(isDirty)
  useEffect(() => { isDirtyRef.current = isDirty }, [isDirty])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (!isDirtyRef.current) return
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
      if (!(e.target instanceof Element)) return
      const target = e.target.closest('a') as HTMLAnchorElement | null
      if (!target) return
      const href = target.getAttribute('href')
      if (!href || href.startsWith('#') || target.target === '_blank' || target.hasAttribute('download')) return
      const url = new URL(target.href, window.location.href)
      if (
        url.origin === window.location.origin &&
        url.pathname === window.location.pathname &&
        url.search === window.location.search
      ) return
      // Stop the navigation now; the (async) confirm decides whether to resume it.
      e.preventDefault()
      e.stopPropagation()
      void confirm({
        title: tc('unsavedTitle'),
        description: t('unsaved_changes_confirm'),
        confirmLabel: tc('leave'),
        cancelLabel: tc('stay'),
        tone: 'danger',
      }).then((confirmed) => {
        if (!confirmed) return
        if (url.origin === window.location.origin) {
          router.push(`${url.pathname}${url.search}${url.hash}`)
        } else {
          leavingRef.current = true
          window.location.assign(url.href)
        }
      })
    }
    document.addEventListener('click', handleClick, true)
    return () => document.removeEventListener('click', handleClick, true)
  }, [t, tc, confirm, router])

  const last = step === STEP_KEYS.length - 1
  const colorsInvalid = answers.colors.some((color) => !isKitColor(color))
  const requiredItems = [
    { key: 'step_industry', complete: Boolean(answers.industry?.trim() && answers.industry !== 'other') },
    { key: 'step_audience', complete: Boolean(answers.audience?.trim() && answers.audience.trim().length >= 2) },
    { key: 'step_colors', complete: answers.colors.some((color) => isKitColor(color)) },
  ] as const
  const requiredComplete = requiredItems.filter((item) => item.complete).length

  return (
    <div
      className="mx-auto flex min-h-[calc(100vh-150px)] w-full max-w-[1120px] flex-col gap-5 pb-5"
      style={{ '--brand': '#7A1521', '--on-brand': '#FFFFFF' } as CSSProperties}
    >
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div dir="auto" className="min-w-0">
          <h1 className="font-el-messiri text-[26px] font-semibold leading-tight text-brand-headline sm:text-[30px]">{t('brand_kit')}</h1>
          <p className="mt-1 font-tajawal text-[13px] text-muted-foreground">{t('interview_subtitle', { brandName })}</p>
        </div>
        <div className="w-full max-w-[420px] rounded-2xl border border-brand-accent/20 bg-white px-4 py-3 shadow-xs sm:px-4 sm:py-3.5">
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
            <p className="font-tajawal text-[12px] font-bold text-brand-headline">{t('required_elements')}</p>
            <p className="font-tajawal text-[12px] font-medium text-brand-primary">{t('required_count', { completed: requiredComplete, total: requiredItems.length })}</p>
          </div>
          <div className="mt-2.5 flex items-center gap-1.5" role="progressbar" aria-label={t('required_elements')} aria-valuemin={0} aria-valuemax={requiredItems.length} aria-valuenow={requiredComplete}>
            {requiredItems.map((item) => (
              <span key={item.key} className={cn('h-[6px] min-w-0 flex-1 rounded-full', item.complete ? 'bg-brand-primary' : 'bg-brand-bg')} />
            ))}
          </div>
          <ul className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 font-tajawal text-[11px] text-brand-headline/80">
            {requiredItems.map((item) => (
              <li key={item.key} className="inline-flex items-center gap-1.5 whitespace-nowrap">
                {item.complete
                  ? <Check className="h-3.5 w-3.5 text-brand-primary" aria-hidden="true" />
                  : <span className="h-2 w-2 rounded-full bg-brand-accent" aria-hidden="true" />}
                {t(item.key)}
              </li>
            ))}
          </ul>
        </div>
      </header>

      <ol dir={locale === 'ar' ? 'rtl' : 'ltr'} className="flex w-full overflow-x-auto rounded-xl border border-brand-accent/20 bg-white px-1 sm:px-2">
        {STEP_KEYS.map((key, index) => {
          const current = index === step
          const done = index < step
          return (
            <li key={key} className="min-w-[64px] flex-1 border-e border-brand-accent/15 last:border-e-0 sm:min-w-0">
              <button
                type="button"
                onClick={() => setStep(index)}
                aria-current={current ? 'step' : undefined}
                className={cn(
                  'relative flex h-[44px] w-full items-center justify-center gap-1 whitespace-nowrap px-1 font-tajawal text-[9px] transition-colors after:absolute after:inset-x-1 after:bottom-0 after:h-0.5 after:content-[""] sm:gap-1.5 sm:px-1.5 sm:text-[11px]',
                  current ? 'font-bold text-brand-primary after:bg-brand-primary' : 'text-muted-foreground after:bg-transparent hover:bg-brand-bg/25 hover:text-brand-primary',
                )}
              >
                {done ? (
                  <Check className="h-3 w-3 shrink-0 text-brand-primary" aria-hidden="true" />
                ) : (
                  <span className={cn(
                    'flex h-[16px] w-[16px] shrink-0 items-center justify-center rounded-full text-[9px]',
                    current ? 'bg-brand-primary font-bold text-white' : 'bg-brand-bg text-muted-foreground',
                  )}>{index + 1}</span>
                )}
                <span className="whitespace-nowrap">{t(key)}</span>
              </button>
            </li>
          )
        })}
      </ol>

      <section key={step} className="flex flex-1 justify-center py-4 animate-[TRENDY AI-reveal_250ms_ease-out]">
        <div className="w-full max-w-[1120px]">
          {step === 0 && <StepLogo brandId={brandId} brandName={brandName} productAssetId={answers.product_asset_id} onAssetChange={(id) => handleChange({ product_asset_id: id })} />}
          {step === 1 && <StepName answers={answers} onChange={handleChange} brandName={brandName} />}
          {step === 2 && <StepTagline answers={answers} onChange={handleChange} brandName={brandName} />}
          {step === 3 && <StepIndustry answers={answers} onChange={handleChange} />}
          {step === 4 && <StepAudience answers={answers} onChange={handleChange} brandName={brandName} />}
          {step === 5 && <StepColors answers={answers} onChange={handleChange} />}
          {step === 6 && <StepAvoidWords answers={answers} onChange={handleChange} brandName={brandName} />}
          {step === 7 && (
            <StepReview
              brandId={brandId}
              answers={answers}
              onChange={handleChange}
              brandName={brandName}
              savedStatus={savedStatus}
              isDirty={isDirty}
            />
          )}
        </div>
      </section>

      <div className="mt-auto flex justify-between border-y border-brand-accent/20 py-2">
        <Button
          type="button"
          variant="ghost"
          onClick={() => setStep(step - 1)}
          disabled={step === 0}
        >
          <ArrowLeft className="h-4 w-4" />{t('back')}</Button>
        {last ? (
          <Button type="button" onClick={handleSave} disabled={saving || colorsInvalid}>
            <Check className="h-4 w-4" />
            {saving ? t('saving') : t('save_brand_kit')}
          </Button>
        ) : (
          <Button type="button" onClick={() => setStep(step + 1)}>{t('continue')}</Button>
        )}
      </div>
    </div>
  )
}
