'use client'

import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Check, Copy, Loader2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useCaption } from '@/hooks/use-caption'
import type { CaptionPreferences } from '@/types'

interface ResultCaptionProps {
    brandId: string
    generationId: string
    preferences: CaptionPreferences
}

export function ResultCaption({ brandId, generationId, preferences }: ResultCaptionProps) {
    const t = useTranslations('components.generation.wizard')
    const { state, generateCaption } = useCaption(brandId, generationId)
    const [text, setText] = useState('')
    const [copied, setCopied] = useState(false)

    // نطلب الكابشن مرة وحدة بس أول ما تظهر النتيجة
    const requested = useRef(false)
    useEffect(() => {
        if (requested.current) return
        requested.current = true
        void generateCaption({ preferences })
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // لما يوصل الكابشن نجمّعه بنص واحد قابل للتعديل
    useEffect(() => {
        if (state.status !== 'success') return
        const { hook, caption, hashtags } = state.result
        const parts = [hook?.trim(), caption.trim(), hashtags.join(' ')].filter(Boolean)
        setText(parts.join('\n\n'))
        setCopied(false)
    }, [state])

    async function handleCopy() {
        try {
            await navigator.clipboard.writeText(text)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            // النسخ ممكن يفشل إذا المتصفح ما سمح
        }
    }

    const dir = state.status === 'success' && state.result.language === 'en' ? 'ltr' : 'rtl'

    return (
        <section className="flex flex-col rounded-[16px] border border-brand-accent/20 bg-white p-5 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <h3 className="text-[15px] font-bold text-brand-headline">{t('caption_title')}</h3>
                    <p className="mt-0.5 text-[11.5px] text-brand-headline/50">{t('caption_subtitle')}</p>
                </div>
                {state.status === 'success' && (
                    <button
                        type="button"
                        onClick={() => void generateCaption({ preferences })}
                        aria-label={t('caption_regenerate')}
                        title={t('caption_regenerate')}
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] border border-brand-accent/25 text-brand-headline/60 transition-colors hover:bg-brand-cream"
                    >
                        <RefreshCw className="h-3.5 w-3.5" />
                    </button>
                )}
            </div>

            <div className="mt-4 flex-1">
                {state.status === 'submitting' || state.status === 'idle' ? (
                    <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 rounded-[10px] border border-dashed border-brand-accent/30 text-[12.5px] text-brand-headline/50">
                        <Loader2 className="h-5 w-5 animate-spin text-brand-primary" />
                        {t('caption_loading')}
                    </div>
                ) : state.status === 'error' ? (
                    <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 rounded-[10px] border border-dashed border-destructive/30 px-4 text-center">
                        <p className="text-[12.5px] text-destructive">{t('caption_error')}</p>
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => void generateCaption({ preferences })}
                            className="border-brand-accent/30"
                        >
                            {t('caption_retry')}
                        </Button>
                    </div>
                ) : (
                    <Textarea
                        dir={dir}
                        value={text}
                        onChange={(e) => {
                            setText(e.target.value)
                            setCopied(false)
                        }}
                        aria-label={t('caption_title')}
                        className="min-h-[260px] resize-y rounded-[10px] border-brand-accent/25 bg-white px-4 py-3 text-[13.5px] leading-[24px] text-brand-headline"
                    />
                )}
            </div>

            {state.status === 'success' && (
                <div className="mt-3 flex items-center justify-between gap-3">
                    <span className="text-[11.5px] tabular-nums text-brand-headline/40">
                        {t('caption_count', { count: text.length })}
                    </span>
                    <Button
                        type="button"
                        variant="outline"
                        onClick={handleCopy}
                        className="h-9 rounded-[9px] border-brand-primary px-4 text-[12.5px] font-bold text-brand-primary hover:bg-brand-primary/5"
                    >
                        {copied ? <Check /> : <Copy />}
                        {copied ? t('caption_copied') : t('caption_copy')}
                    </Button>
                </div>
            )}
        </section>
    )
}