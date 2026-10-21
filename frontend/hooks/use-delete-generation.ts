'use client'

import { useCallback } from 'react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'
import { apiRequest } from '@/lib/api'
import { errorMessage } from '@/lib/errors'

export interface DeleteGenerationOutcome {
  ok: boolean
  message?: string
}

export function useDeleteGeneration(brandId: string) {
  const tt = useTranslations('toasts')
  const te = useTranslations('errors')
  const deleteGeneration = useCallback(
    async (generationId: string): Promise<DeleteGenerationOutcome> => {
      try {
        await apiRequest(`/brands/${brandId}/generations/${generationId}`, {
          method: 'DELETE',
        })
        toast.success(tt('generationDeleted'))
        return { ok: true }
      } catch (err) {
        const message = errorMessage(err, te)
        toast.error(message)
        return { ok: false, message }
      }
    },
    [brandId, tt, te],
  )

  return { deleteGeneration }
}
