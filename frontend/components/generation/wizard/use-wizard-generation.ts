'use client'

import { useMemo, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'
import { apiRequest, ApiError } from '@/lib/api'
import { errorMessage } from '@/lib/errors'
import { GenerationIntent, isDefiniteFailure } from '@/lib/generation-intent'
import type { GenerationResponse, ProductAssetUploadResponse } from '@/types'
import type { WizardGenerateRequest } from './build-request'

export type WizardGenerationState =
  | { status: 'idle' }
  | { status: 'uploading' }
  | { status: 'generating' }
  | { status: 'success'; result: GenerationResponse }
  | { status: 'error'; code: string; message: string }

export function useWizardGeneration(brandId: string) {
  const te = useTranslations('errors')
  const [state, setState] = useState<WizardGenerationState>({ status: 'idle' })

  // نتذكر آخر صورة رفعناها، حتى ما نرفعها مرة ثانية لما يطلب "نسخة جديدة"
  const lastUpload = useRef<{ file: File; assetId: string } | null>(null)
  // طلب واحد في كل مرة، ومفتاح Idempotency ثابت لكل طلب لم يُحسم بعد
  const inFlight = useRef(false)
  const intent = useMemo(() => new GenerationIntent(brandId), [brandId])

  async function run(
    productImage: File | null,
    buildRequest: (productAssetId: string | null) => WizardGenerateRequest,
    newIntent = false,
  ) {
    if (inFlight.current) return
    inFlight.current = true
    let sent = false
    try {
      // "نسخة جديدة" بعد نجاح: نية جديدة ومفتاح جديد
      if (newIntent) intent.newIntent()

      // 1. نرفع صورة المنتج (إذا موجودة)
      let productAssetId: string | null = null
      if (productImage) {
        if (lastUpload.current?.file === productImage) {
          productAssetId = lastUpload.current.assetId
        } else {
          setState({ status: 'uploading' })
          const body = new FormData()
          body.append('file', productImage)
          const asset = await apiRequest<ProductAssetUploadResponse>(
            `/brands/${brandId}/product-assets`,
            { method: 'POST', body },
          )
          lastUpload.current = { file: productImage, assetId: asset.id }
          productAssetId = asset.id
        }
      }

      // 2. نطلب التوليد
      setState({ status: 'generating' })
      const body = buildRequest(productAssetId)
      const key = intent.key(body)
      sent = true
      const result = await apiRequest<GenerationResponse>(`/brands/${brandId}/generate`, {
        method: 'POST',
        headers: { 'Idempotency-Key': key },
        body: JSON.stringify(body),
      })

      // 3. السيرفر ممكن يرجع نجاح بس التوليد نفسه فشل
      if (result.status === 'failed' || !result.image_url) {
        intent.abandon()
        const code = result.error_code ?? 'GENERATION_FAILED'
        // The stored provider message is not translated: only a known code is shown as-is.
        const message = errorMessage({ code }, te)
        toast.error(message)
        setState({ status: 'error', code, message })
        return
      }

      intent.succeed()
      setState({ status: 'success', result })
    } catch (err) {
      // A definite server answer settles the intent; ambiguous failures keep the key.
      if (sent && isDefiniteFailure(err)) intent.abandon()
      const message = errorMessage(err, te)
      toast.error(message)
      setState({
        status: 'error',
        code: err instanceof ApiError ? err.code : 'UNKNOWN',
        message,
      })
    } finally {
      inFlight.current = false
    }
  }

  function reset() {
    intent.editAfterSuccess()
    setState({ status: 'idle' })
  }

  return { state, run, reset }
}
