'use client'

import { useTranslations } from 'next-intl';
import { useCallback } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useGenerationDetail } from '@/hooks/use-generation-detail'
import { useDeleteGeneration } from '@/hooks/use-delete-generation'
import { HistoryDetail } from '@/components/history/history-detail'
import { Loader2 } from 'lucide-react'

interface GenerationDetailPageProps {
  params: { brandId: string; generationId: string }
}

export default function GenerationDetailPage({ params }: GenerationDetailPageProps) {
  const t = useTranslations('app.(dashboard).[brandId].history.[generationId].page');
  const { brandId, generationId } = params
  const router = useRouter()
  const searchParams = useSearchParams()
  const backSearch = searchParams.toString() || undefined

  const { detail, loading, error, notFound } = useGenerationDetail(brandId, generationId)
  const { deleteGeneration } = useDeleteGeneration(brandId)

  const handleDelete = useCallback(
    () => deleteGeneration(generationId),
    [deleteGeneration, generationId],
  )

  const handleDeleted = useCallback(() => {
    router.push(`/${brandId}/history${backSearch ? `?${backSearch}` : ''}`)
  }, [brandId, backSearch, router])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <p className="text-lg font-medium">{t('generation_not_found')}</p>
        <p className="mt-2 text-sm text-muted-foreground">{t('this_generation_may_have')}</p>
        <Link
          href={`/${brandId}/history${backSearch ? `?${backSearch}` : ''}`}
          className="mt-4 text-sm text-primary underline underline-offset-2"
        >
          {t('back_to_history')}
        </Link>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-center">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    )
  }

  if (!detail) return null

  return (
    <HistoryDetail
      detail={detail}
      brandId={brandId}
      backSearch={backSearch}
      onDelete={handleDelete}
      onDeleted={handleDeleted}
    />
  )
}
