'use client'

import { useTranslations } from 'next-intl';
import { useState } from 'react'
import { TriangleAlert } from 'lucide-react'
import { apiRequest } from '@/lib/api'
import { Brand } from '@/types'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface DeleteBrandDialogProps {
  brand: Pick<Brand, 'id' | 'name'>
  open: boolean
  onOpenChange: (open: boolean) => void
  onBrandDeleted: () => void
}

export function DeleteBrandDialog({
  brand,
  open,
  onOpenChange,
  onBrandDeleted,
}: DeleteBrandDialogProps) {
  const t = useTranslations('components.brand.delete-brand-dialog');
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDelete = async () => {
    setLoading(true)
    setError(null)
    try {
      
      await apiRequest(`/brands/${brand.id}`, {
        method: 'DELETE',
        body: JSON.stringify({ confirm_name: brand.name }),
      })
      onBrandDeleted()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('failed_to_delete_brand'))
    } finally {
      setLoading(false)
    }
  }

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) setError(null)
    onOpenChange(newOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-[360px] gap-0 rounded-2xl border-brand-accent/30 bg-white p-6 font-readex text-brand-headline sm:rounded-2xl">
        <DialogHeader className="gap-0 text-start sm:text-start">
          <span className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-primary/10 text-brand-primary">
            <TriangleAlert className="h-5 w-5" />
          </span>
          <DialogTitle className="text-[16px] font-bold leading-normal tracking-normal">
            {t('delete_title')}
          </DialogTitle>
          <DialogDescription className="mt-2 text-[13px] leading-relaxed text-brand-headline/60">
            {t('confirm_text', { name: brand.name })}
          </DialogDescription>
        </DialogHeader>

        {error && <p className="mt-3 text-[13px] text-destructive">{error}</p>}

    
        <div className="mt-8 flex items-center gap-2 ltr:flex-row-reverse">
          <Button type="button" onClick={handleDelete} disabled={loading} className="h-10 px-5">
            {loading ? t('deleting') : t('confirm_delete')}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="h-10 px-4"
            onClick={() => handleOpenChange(false)}
            disabled={loading}
          >
            {t('cancel')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}