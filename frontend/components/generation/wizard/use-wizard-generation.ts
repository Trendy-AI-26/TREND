'use client'

import { useMemo, useRef, useState } from 'react'
import { apiRequest, ApiError } from '@/lib/api'
import { GenerationIntent } from '@/lib/generation-intent'
import type { GenerationResponse, ProductAssetUploadResponse } from '@/types'
import type { WizardGenerateRequest } from './build-request'

export type WizardGenerationState =
  | { status: 'idle' }
  | { status: 'uploading' }
  | { status: 'generating' }
  | { status: 'success'; result: GenerationResponse }
  | { status: 'error'; code: string; message: string }

export function useWizardGeneration(brandId: string) {
  const [state, setState] = useState<WizardGenerationState>({ status: 'idle' })

  // نتذكر آخر صورة رفعناها، حتى ما نرفعها مرة ثانية لما يطلب "نسخة جديدة"
  const lastUpload = useRef<{ file: File; assetId: string } | null>(null)
  const inFlight = useRef(false)
  const intent = useMemo(() => new GenerationIntent(brandId), [brandId])

  async function run(
    productImage: File | null,
    buildRequest: (productAssetId: string | null) => WizardGenerateRequest,
    newIntent = false,
  ) {
    if (inFlight.current) return
    inFlight.current = true
    try {
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
      const result = await apiRequest<GenerationResponse>(`/brands/${brandId}/generate`, {
        method: 'POST',
        headers: { 'Idempotency-Key': key },
        body: JSON.stringify(body),
      })

      // 3. السيرفر ممكن يرجع نجاح بس التوليد نفسه فشل
      if (result.status === 'failed' || !result.image_url) {
        setState({
          status: 'error',
          code: result.error_code ?? 'GENERATION_FAILED',
          message: result.error_message ?? '',
        })
        return
      }

      intent.succeed()
      setState({ status: 'success', result })
    } catch (err) {
      setState({
        status: 'error',
        code: err instanceof ApiError ? err.code : 'UNKNOWN',
        message: err instanceof Error ? err.message : '',
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
