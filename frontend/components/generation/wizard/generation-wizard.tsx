'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { addGenerationNotification } from '@/hooks/use-notifications'
import { buildGenerateRequest } from './build-request'
import { GenerationLoading } from './generation-loading'
import { GenerationResult } from './generation-result'
import { JourneyBanner } from './journey-banner'
import { ReadyToGenerateCard } from './ready-to-generate-card'
import { useWizardGeneration } from './use-wizard-generation'
import { WizardStepper } from './wizard-stepper'
import { StepIdea } from './steps/step-idea'
import { StepAudience } from './steps/step-audience'
import { StepStyle } from './steps/step-style'
import { StepPlatform } from './steps/step-platform'
import {
  EMPTY_WIZARD_ANSWERS,
  validateAudienceStep,
  validateIdeaStep,
  validatePlatformStep,
  validateStyleStep,
  type WizardAnswers,
} from './wizard-types'

interface GenerationWizardProps {
  brandId: string
  brandName: string
  brandHasLogo: boolean
}

export function GenerationWizard({ brandId, brandName, brandHasLogo }: GenerationWizardProps) {
  const t = useTranslations('components.generation.wizard')
  const tOpt = useTranslations('options')
  const tNotifications = useTranslations('notifications')
  const locale = useLocale()
  const router = useRouter()

  const steps = [t('step_idea'), t('step_audience'), t('step_style'), t('step_platform')]
  const lastStep = steps.length - 1

  // الخطوة المعروضة الآن، وأبعد خطوة وصلها المستخدم
  const [step, setStep] = useState(0)
  const [furthestStep, setFurthestStep] = useState(0)

  // كل إجابات المستخدم محفوظة هنا في مكان واحد
  const [answers, setAnswers] = useState<WizardAnswers>(EMPTY_WIZARD_ANSWERS)

  // ما نعرض الأخطاء إلا بعد ما يضغط "التالي" وفي نقص
  const [showErrors, setShowErrors] = useState(false)

  // حالة التوليد: فاضي، رفع صورة، توليد، نجاح، خطأ
  const { state: generation, run, reset } = useWizardGeneration(brandId)

  const ideaErrors = validateIdeaStep(answers.idea)
  const audienceErrors = validateAudienceStep(answers.audience)
  const styleErrors = validateStyleStep(answers.style, brandHasLogo)
  const platformErrors = validatePlatformStep(answers.platform)

  // هل كل خطوة مكتملة؟ الخطوة الأخيرة لازم المستخدم يكون وصلها فعلاً
  const stepComplete = [
    Object.keys(ideaErrors).length === 0,
    Object.keys(audienceErrors).length === 0,
    Object.keys(styleErrors).length === 0,
    furthestStep >= 3 && Object.keys(platformErrors).length === 0,
  ]
  const completedSections = stepComplete.filter(Boolean).length
  const allComplete = completedSections === steps.length

  function goToStep(index: number) {
    if (index > furthestStep) return
    setShowErrors(false)
    setStep(index)
  }

  function goNext() {
    if (step >= lastStep) return
    // ما ننتقل للخطوة التالية إلا إذا الحالية مكتملة
    if (!stepComplete[step]) {
      setShowErrors(true)
      return
    }
    setShowErrors(false)
    const next = step + 1
    setStep(next)
    setFurthestStep((current) => Math.max(current, next))
  }

  function goPrevious() {
    setShowErrors(false)
    setStep((current) => Math.max(0, current - 1))
  }

  function handleGenerate() {
    if (!allComplete) return
    window.scrollTo({ top: 0, behavior: 'smooth' })
    void run(answers.style.productImage, (productAssetId) =>
      buildGenerateRequest({ answers, brandHasLogo, locale, productAssetId }),
    )
  }

  function handleEditAnswers() {
    reset()
    setStep(0)
  }

  // إشعار بعد كل توليد ناجح (مرة وحدة لكل نتيجة)
  const notifiedId = useRef<string | null>(null)
  useEffect(() => {
    if (generation.status !== 'success' || notifiedId.current === generation.result.id) return
    notifiedId.current = generation.result.id
    addGenerationNotification(
      tNotifications('items.generation.title'),
      tNotifications('items.generation.description'),
      tNotifications('justNow'),
    )
  }, [generation, tNotifications])

  // شارات "تم التوليد بناءً على"
  const { idea, style, platform } = answers
  const basedOn = [
    idea.goal === 'custom' ? idea.goalCustom.trim() : idea.goal ? t(`goal_${idea.goal}`) : '',
    style.feeling ? t(`feeling_${style.feeling}`) : '',
    platform.preset ? tOpt(`preset_${platform.preset}`) : '',
    brandHasLogo && style.logoPlacement && style.logoPlacement !== 'none'
      ? t('based_on_with_logo')
      : t('based_on_without_logo'),
  ].filter(Boolean)

  const isWorking = generation.status === 'uploading' || generation.status === 'generating'

  return (
    <div className="mx-auto w-full max-w-[700px] pb-10 font-tajawal">
      {/* العنوان */}
      <header className="mb-10 flex items-start gap-3.5">
        <button
          type="button"
          onClick={() => router.back()}
          aria-label={t('back')}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] border border-brand-accent/20 bg-white text-brand-headline/80 transition-colors hover:bg-brand-cream"
        >
          <ChevronLeft className="h-[18px] w-[18px] rtl:rotate-180" />
        </button>
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="font-el-messiri text-[26px] font-semibold leading-tight text-brand-headline">{t('title')}</h1>
            <span className="rounded-full bg-brand-primary/10 px-2.5 py-[3px] text-[10.5px] font-extrabold leading-[16px] text-brand-primary">
              {t('ai_badge')}
            </span>
          </div>
          <p className="mt-0.5 text-[12.5px] text-brand-headline/60">{t('subtitle', { brandName })}</p>
        </div>
      </header>

      {/* ===== 1. أثناء التوليد ===== */}
      {isWorking && (
        <GenerationLoading
          stage={generation.status === 'uploading' ? 'uploading' : 'generating'}
          hasProductImage={Boolean(answers.style.productImage)}
        />
      )}

      {/* ===== 2. بعد النجاح ===== */}
      {generation.status === 'success' && (
        <GenerationResult
          brandId={brandId}
          result={generation.result}
          platformLabel={tOpt(`preset_${generation.result.platform_preset}`)}
          withCaption={answers.platform.withCaption}
          captionPreferences={{ include_cta: answers.idea.cta !== 'none' }}
          basedOn={basedOn}
          onRegenerate={handleGenerate}
          onEditAnswers={handleEditAnswers}
        />
      )}

      {/* ===== 3. النموذج (قبل التوليد أو بعد خطأ) ===== */}
      {(generation.status === 'idle' || generation.status === 'error') && (
        <div className="space-y-4">
          <JourneyBanner />

          {/* بطاقة النموذج */}
          <section className="overflow-hidden rounded-[16px] border border-brand-accent/20 bg-white shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
            <WizardStepper
              steps={steps}
              currentStep={step}
              furthestStep={furthestStep}
              onStepClick={goToStep}
              ariaLabel={t('steps_navigation')}
            />

            {/* محتوى الخطوة */}
            <div className="px-5 py-7 sm:px-8">
              {step === 0 ? (
                <StepIdea
                  value={answers.idea}
                  onChange={(idea) => setAnswers((current) => ({ ...current, idea }))}
                  errors={showErrors ? ideaErrors : {}}
                />
              ) : step === 1 ? (
                <StepAudience
                  value={answers.audience}
                  onChange={(audience) => setAnswers((current) => ({ ...current, audience }))}
                  errors={showErrors ? audienceErrors : {}}
                />
              ) : step === 2 ? (
                <StepStyle
                  value={answers.style}
                  onChange={(style) => setAnswers((current) => ({ ...current, style }))}
                  errors={showErrors ? styleErrors : {}}
                  brandId={brandId}
                  brandHasLogo={brandHasLogo}
                />
              ) : (
                <StepPlatform
                  value={answers.platform}
                  onChange={(platform) => setAnswers((current) => ({ ...current, platform }))}
                  errors={platformErrors}
                />
              )}
            </div>

            {/* أزرار التنقل */}
            <div className="flex items-center justify-between border-t border-brand-accent/15 bg-brand-cream/60 px-5 py-3 sm:px-12">
              <Button
                type="button"
                variant="outline"
                onClick={goPrevious}
                disabled={step === 0}
                className="h-[38px] rounded-[9px] border-brand-accent/20 bg-white px-[18px] text-[13px] font-semibold text-brand-headline/80 disabled:text-brand-headline/30 disabled:opacity-100"
              >
                <ChevronLeft className="rtl:rotate-180" />
                {t('previous')}
              </Button>

              <div className="flex items-center gap-[5px]" aria-hidden="true">
                {steps.map((label, index) => (
                  <span
                    key={label}
                    className={cn(
                      'h-1.5 rounded-full transition-all',
                      index === step ? 'w-5 bg-brand-primary' : 'w-1.5 bg-brand-accent/20',
                    )}
                  />
                ))}
              </div>

              <Button
                type="button"
                onClick={goNext}
                className={cn(
                  'h-[38px] rounded-[9px] bg-brand-primary px-[18px] text-[13px] font-bold text-white hover:bg-brand-primary/90',
                  step === lastStep && 'invisible',
                )}
              >
                {t('next')}
                <ChevronRight className="rtl:rotate-180" />
              </Button>
            </div>
          </section>

          {/* رسالة الخطأ إذا فشل التوليد */}
          {generation.status === 'error' && (
            <div
              role="alert"
              className="flex items-start gap-3 rounded-[12px] border border-destructive/30 bg-destructive/5 px-4 py-3.5"
            >
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
              <div className="min-w-0">
                <p className="text-[13.5px] font-bold text-destructive">{t('error_title')}</p>
                <p className="mt-0.5 text-[12.5px] text-brand-headline/70">{t('error_generic')}</p>
                {generation.message && (
                  <p className="mt-1 break-words text-[11.5px] text-brand-headline/40" dir="auto">
                    {generation.message}
                  </p>
                )}
              </div>
            </div>
          )}

          <ReadyToGenerateCard
            completedSections={completedSections}
            totalSections={steps.length}
            onGenerate={handleGenerate}
          />
        </div>
      )}
    </div>
  )
}