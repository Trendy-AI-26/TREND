'use client'

import { useMemo, useRef, useState } from 'react'
import { GenerationIntent } from '@/lib/generation-intent'
import { apiRequest, ApiError } from '@/lib/api'
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
  const [state, setState] = useState<GenerateState>({ status: 'idle' })
  const inFlight = useRef(false)
  const intent = useMemo(() => new GenerationIntent(brandId), [brandId])

  async function generate(body: GenerateRequest) {
    if (inFlight.current) return
    inFlight.current = true
    setState({ status: 'submitting' })
    try {
      if (state.status === 'success') intent.newIntent()
      const result = await apiRequest<GenerationResponse>(
        `/brands/${brandId}/generate`,
        { method: 'POST', body: JSON.stringify(body),
          headers: { 'Idempotency-Key': intent.key(body) } },
      )
      if (result.status !== 'succeeded' || !result.image_url) {
        throw new ApiError('Generation has not completed.', 'GENERATION_IN_PROGRESS')
      }
      intent.succeed()
      setState({ status: 'success', result })
    } catch (err) {
      const code = err instanceof ApiError ? err.code : 'UNKNOWN'
      const message =
        err instanceof Error ? err.message : 'Something went wrong. Please try again.'
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
