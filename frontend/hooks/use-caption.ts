'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'
import { apiRequest, ApiError } from '@/lib/api'
import { errorMessage } from '@/lib/errors'
import type { CaptionRequest, CaptionResponse } from '@/types'

export type CaptionState =
    | { status: 'idle' }
    | { status: 'submitting' }
    | { status: 'success'; result: CaptionResponse }
    | { status: 'error'; code: string; message: string }

interface UseCaptionResult {
    state: CaptionState
    generateCaption: (body: CaptionRequest) => Promise<void>
    reset: () => void
}

export function useCaption(brandId: string, generationId: string): UseCaptionResult {
    const tt = useTranslations('toasts')
    const te = useTranslations('errors')
    const [state, setState] = useState<CaptionState>({ status: 'idle' })

    async function generateCaption(body: CaptionRequest) {
        setState({ status: 'submitting' })
        try {
            const result = await apiRequest<CaptionResponse>(
                `/brands/${brandId}/generations/${generationId}/caption`,
                { method: 'POST', body: JSON.stringify(body) },
            )
            setState({ status: 'success', result })
            toast.success(tt('captionReady'))
        } catch (err) {
            const code = err instanceof ApiError ? err.code : 'UNKNOWN'
            const message = errorMessage(err, te)
            toast.error(message)
            setState({ status: 'error', code, message })
        }
    }

    function reset() {
        setState({ status: 'idle' })
    }

    return { state, generateCaption, reset }
}