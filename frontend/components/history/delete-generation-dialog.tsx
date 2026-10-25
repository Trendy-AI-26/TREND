'use client'

import { useTranslations } from 'next-intl';
import { ConfirmDialog } from '@/components/ui/confirm-dialog'

interface DeleteGenerationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  loading: boolean
  /** Optional inline message. Action failures are shown as toasts by the caller instead. */
  error?: string | null
}

export function DeleteGenerationDialog({
  open,
  onOpenChange,
  onConfirm,
  loading,
  error,
}: DeleteGenerationDialogProps) {
  const t = useTranslations('components.history.delete-generation-dialog');
  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      tone="danger"
      title={t('delete_generation')}
      description={
        <>
          {t('this_will_permanently_delete')}
          {error && <span className="mt-2 block text-destructive">{error}</span>}
        </>
      }
      confirmLabel={t('delete')}
      loadingLabel={t('deleting')}
      cancelLabel={t('cancel')}
      loading={loading}
      onConfirm={onConfirm}
    />
  )
}