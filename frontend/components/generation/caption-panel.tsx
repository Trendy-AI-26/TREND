'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Check, Copy, Loader2, MessageSquareText, RefreshCw, Sparkles, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Notice } from '@/components/ui/notice'
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import { useCaption } from '@/hooks/use-caption'
import type { CaptionPreferences, TextLanguage } from '@/types'

interface CaptionPanelProps {
    brandId: string
    generationId: string | null
    language: TextLanguage
    enabled: boolean
}

interface CaptionDraft {
    caption: string
    hook: string
    hashtags: string[]
}

function toDraft(caption: string, hook: string | null, hashtags: string[]): CaptionDraft {
    return { caption, hook: hook ?? '', hashtags: [...hashtags] }
}

function composeForCopy(draft: CaptionDraft): string {
    const parts = [draft.hook.trim(), draft.caption.trim()].filter(Boolean)
    if (draft.hashtags.length > 0) {
        parts.push(draft.hashtags.join(' '))
    }
    return parts.join('\n\n')
}

export function CaptionPanel({
    brandId,
    generationId,
    language,
    enabled,
}: CaptionPanelProps) {
    const t = useTranslations('components.generation.caption-panel')
    const { state, generateCaption, reset } = useCaption(brandId, generationId ?? '')

    const [open, setOpen] = useState(false)
    const [draft, setDraft] = useState<CaptionDraft | null>(null)
    const [captionLanguage, setCaptionLanguage] = useState<TextLanguage>(language)
    const [trendUsed, setTrendUsed] = useState(false)
    const [copied, setCopied] = useState(false)
    const [hashtagInput, setHashtagInput] = useState('')

    useEffect(() => {
        setOpen(false)
        setDraft(null)
        setCopied(false)
        setHashtagInput('')
        reset()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [generationId])

    useEffect(() => {
        if (state.status === 'success') {
            setDraft(toDraft(state.result.caption, state.result.hook, state.result.hashtags))
            setCaptionLanguage(state.result.language)
            setTrendUsed(state.result.trend_used)
            setCopied(false)
        }
    }, [state])

    const submitting = state.status === 'submitting'
    const hasCaption = draft !== null

    async function requestCaption(preferences?: CaptionPreferences) {
        if (!enabled || !generationId) return
        setCopied(false)
        await generateCaption({ preferences })
    }

    function updateDraft(patch: Partial<CaptionDraft>) {
        setDraft((prev) => (prev ? { ...prev, ...patch } : prev))
        setCopied(false)
    }

    function removeHashtag(tag: string) {
        if (!draft) return
        updateDraft({ hashtags: draft.hashtags.filter((h) => h !== tag) })
    }

    function addHashtag() {
        if (!draft) return
        const raw = hashtagInput.trim()
        if (!raw) return
        const normalized = raw.startsWith('#') ? raw : `#${raw}`
        if (/\s/.test(normalized)) return
        if (draft.hashtags.includes(normalized)) {
            setHashtagInput('')
            return
        }
        updateDraft({ hashtags: [...draft.hashtags, normalized] })
        setHashtagInput('')
    }

    async function handleCopy() {
        if (!draft) return
        try {
            await navigator.clipboard.writeText(composeForCopy(draft))
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            // clipboard can fail silently (permissions/insecure context)
        }
    }

    const captionDir = captionLanguage === 'ar' ? 'rtl' : 'ltr'

    return (
        <>
            <Button
                type="button"
                variant="secondary"
                className={`w-full transition-opacity ${enabled ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}
                disabled={!enabled}
                onClick={() => enabled && setOpen(true)}
            >
                {hasCaption ? <Check className="h-4 w-4" /> : <MessageSquareText className="h-4 w-4" />}
                {hasCaption ? t('view_caption') : t('generate_caption')}
            </Button>

            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
                    <DialogHeader>
                        <DialogTitle>{t('caption')}</DialogTitle>
                        <p className="text-[12px] text-muted-foreground">{t('optional_helper')}</p>
                    </DialogHeader>

                    <div className="space-y-4">
                        {!hasCaption && (
                            <Button type="button" variant="default" onClick={() => requestCaption()} disabled={submitting}>
                                {submitting ? (
                                    <><Loader2 className="h-4 w-4 animate-spin" />{t('generating')}</>
                                ) : (
                                    <><Sparkles className="h-4 w-4" />{t('generate_caption')}</>
                                )}
                            </Button>
                        )}

                        {hasCaption && (
                            <div className="flex justify-end">
                                <Button type="button" variant="secondary" size="sm" onClick={() => requestCaption()} disabled={submitting}>
                                    {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                                    {t('regenerate')}
                                </Button>
                            </div>
                        )}

                        {draft && (
                            <div className="space-y-3">
                                <div className="flex flex-wrap items-center gap-2">
                                    <Badge variant="outline">{captionLanguage === 'ar' ? t('language_ar') : t('language_en')}</Badge>
                                    <Badge variant={trendUsed ? 'success' : 'muted'}>{trendUsed ? t('trend_used') : t('trend_not_used')}</Badge>
                                </div>

                                <div>
                                    <label className="mb-1 block text-[12px] font-medium text-muted-foreground">{t('hook_label')}</label>
                                    <Input dir={captionDir} value={draft.hook} placeholder={t('hook_placeholder')} onChange={(e) => updateDraft({ hook: e.target.value })} />
                                </div>

                                <div>
                                    <label className="mb-1 block text-[12px] font-medium text-muted-foreground">{t('caption_label')}</label>
                                    <Textarea dir={captionDir} rows={5} value={draft.caption} onChange={(e) => updateDraft({ caption: e.target.value })} />
                                </div>

                                <div>
                                    <label className="mb-1 block text-[12px] font-medium text-muted-foreground">{t('hashtags_label')}</label>
                                    <div dir={captionDir} className="flex flex-wrap gap-1.5">
                                        {draft.hashtags.map((tag) => (
                                            <span key={tag} className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-[12px] text-foreground">
                                                {tag}
                                                <button type="button" onClick={() => removeHashtag(tag)} aria-label={t('remove_hashtag')} className="text-muted-foreground hover:text-foreground">
                                                    <X className="h-3 w-3" />
                                                </button>
                                            </span>
                                        ))}
                                    </div>
                                    <div className="mt-2 flex gap-2">
                                        <Input
                                            dir={captionDir}
                                            value={hashtagInput}
                                            placeholder={t('add_hashtag_placeholder')}
                                            onChange={(e) => setHashtagInput(e.target.value)}
                                            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addHashtag() } }}
                                        />
                                        <Button type="button" variant="secondary" size="sm" onClick={addHashtag}>{t('add')}</Button>
                                    </div>
                                </div>

                                {state.status === 'success' && state.result.keywords.length > 0 && (
                                    <p className="text-[12px] text-muted-foreground">{t('keywords_label')} {state.result.keywords.join(', ')}</p>
                                )}

                                <div className="flex items-center gap-2 pt-1">
                                    <Button type="button" onClick={handleCopy}>
                                        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                        {copied ? t('copied') : t('copy')}
                                    </Button>
                                </div>

                                <Notice variant="info">{t('not_published_disclaimer')}</Notice>
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </>
    )
}
