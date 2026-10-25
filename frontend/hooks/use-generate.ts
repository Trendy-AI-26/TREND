'use client'

import { useMemo, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'
import { apiRequest, ApiError } from '@/lib/api'
import { errorMessage } from '@/lib/errors'
import { GenerationIntent, isDefiniteFailure } from '@/lib/generation-intent'
import type { GenerateRequest, GenerationResponse } from '@/types'

export type GenerateState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'success'; result: GenerationResponse }
  | { status: 'error'; code: string; message: string }

interface UseGenerateResult {
  state: GenerateState
  generate: (body: GenerateRequest) => Promise<void>
  reset: () => void
}

export function useGenerate(brandId: string): UseGenerateResult {
  const te = useTranslations('errors')
  const [state, setState] = useState<GenerateState>({ status: 'idle' })
  // One request at a time, and one stable Idempotency-Key per unresolved request.
  const inFlight = useRef(false)
  const intent = useMemo(() => new GenerationIntent(brandId), [brandId])

  async function generate(body: GenerateRequest) {
    if (inFlight.current) return
    inFlight.current = true
    setState({ status: 'submitting' })
    let sent = false
    try {
      if (state.status === 'success') intent.newIntent()
      const key = intent.key(body)
      sent = true
      const result = await apiRequest<GenerationResponse>(
        `/brands/${brandId}/generate`,
        {
          method: 'POST',
          body: JSON.stringify(body),
          headers: { 'Idempotency-Key': key },
        },
      )
      if (result.status !== 'succeeded' || !result.image_url) {
        throw new ApiError('Generation has not completed.', 'GENERATION_IN_PROGRESS')
      }
      intent.succeed()
      setState({ status: 'success', result })
    } catch (err) {
      // A definite server answer settles the intent; ambiguous failures keep the key.
      if (sent && isDefiniteFailure(err)) intent.abandon()
      const code = err instanceof ApiError ? err.code : 'UNKNOWN'
      const message = errorMessage(err, te)
      toast.error(message)
      setState({ status: 'error', code, message })
    } finally {
      inFlight.current = false
    }
  }

  function reset() {
    intent.editAfterSuccess()
    setState({ status: 'idle' })
  }

  return { state, generate, reset }
}
