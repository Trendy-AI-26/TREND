'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { apiRequest, ApiError } from '@/lib/api'
import type { CreativeDirection, GenerationBrief, PlatformPreset } from '@/types'

interface UsePreviewBriefResult {
    preview: CreativeDirection | null
    loading: boolean
    error: string | null
    fetchPreview: (brief: GenerationBrief, platformPreset: PlatformPreset) => Promise<void>
    retryPreview: () => Promise<void>
}

type PreviewRequest = {
    brief: GenerationBrief
    platformPreset: PlatformPreset
}

function buildPreviewRequestKey(
    brandId: string,
    brief: GenerationBrief,
    platformPreset: PlatformPreset,
) {
    return `${brandId}:${platformPreset}:${JSON.stringify(brief)}`
}

export function usePreviewBrief(brandId: string): UsePreviewBriefResult {
    const [preview, setPreview] = useState<CreativeDirection | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const lastRequestKey = useRef<string | null>(null)
    const activeRequestKey = useRef<string | null>(null)
    const lastRequest = useRef<PreviewRequest | null>(null)
    const abortController = useRef<AbortController | null>(null)

    const runPreview = useCallback(
        async ({ brief, platformPreset }: PreviewRequest, force = false) => {
            const requestKey = buildPreviewRequestKey(brandId, brief, platformPreset)

            // React Strict Mode can replay effects in development. A stable request
            // key keeps that replay from creating a second preview request.
            if (!force && requestKey === lastRequestKey.current) return

            abortController.current?.abort()
            const controller = new AbortController()
            abortController.current = controller
            lastRequestKey.current = requestKey
            lastRequest.current = { brief, platformPreset }
            activeRequestKey.current = requestKey
            setLoading(true)
            setError(null)

            try {
                const result = await apiRequest<{ creative_direction: CreativeDirection; brand_name: string }>(
                    `/brands/${brandId}/preview-brief`,
                    {
                        method: 'POST',
                        body: JSON.stringify({ brief, platform_preset: platformPreset }),
                        signal: controller.signal,
                    },
                )

                if (activeRequestKey.current !== requestKey) return
                setPreview(result.creative_direction)
            } catch (err) {
                if (err instanceof DOMException && err.name === 'AbortError') return
                if (activeRequestKey.current !== requestKey) return

                const message =
                    err instanceof ApiError
                        ? err.message
                        : err instanceof Error
                            ? err.message
                            : 'Failed to load preview'
                setError(message)
            } finally {
                if (activeRequestKey.current === requestKey) {
                    setLoading(false)
                }
            }
        },
        [brandId],
    )

    const fetchPreview = useCallback(
        (brief: GenerationBrief, platformPreset: PlatformPreset) =>
            runPreview({ brief, platformPreset }),
        [runPreview],
    )

    const retryPreview = useCallback(async () => {
        if (lastRequest.current) {
            await runPreview(lastRequest.current, true)
        }
    }, [runPreview])

    useEffect(() => {
        return () => {
            abortController.current?.abort()
            activeRequestKey.current = null
        }
    }, [])

    return { preview, loading, error, fetchPreview, retryPreview }
}
