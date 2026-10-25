'use client'

import { useTranslations } from 'next-intl';
import { useState } from 'react'
import { toast } from 'sonner'
import { apiRequest } from '@/lib/api'
import { errorMessage } from '@/lib/errors'
import { Brand } from '@/types'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'

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
  const tt = useTranslations('toasts');
  const te = useTranslations('errors');
  const [loading, setLoading] = useState(false)

  const handleDelete = async () => {
    setLoading(true)
    try {
      await apiRequest(`/brands/${brand.id}`, {
        method: 'DELETE',
        body: JSON.stringify({ confirm_name: brand.name }),
      })
      onBrandDeleted()
      onOpenChange(false)
      toast.success(tt('brandDeleted'))
    } catch (err) {
      toast.error(errorMessage(err, te))
    } finally {
      setLoading(false)
    }
  }

  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      tone="danger"
      title={t('delete_title')}
      description={t.rich('confirm_text', {
        name: brand.name,
        b: (chunks) => <span className="font-bold text-brand-headline">{chunks}</span>,
      })}
      confirmLabel={t('confirm_delete')}
      loadingLabel={t('deleting')}
      cancelLabel={t('cancel')}
      loading={loading}
      onConfirm={handleDelete}
    />
  )
}