'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'
import { apiRequest } from '@/lib/api'
import { errorMessage } from '@/lib/errors'
import { useConfirm } from '@/components/ui/confirm-dialog'

export type UserAction = 'verify-email' | 'disable' | 'enable' | 'grant-generations' | 'extend-trial' | 'reset-daily-usage' | 'delete'
export function useUserActions(id: string, onSuccess: (deleted: boolean) => void) {
  const confirm = useConfirm(); const t = useTranslations('adminUI'); const errors = useTranslations('errors'); const [busy, setBusy] = useState(false)
  async function run(action: UserAction, body?: object) {
    if (busy) return
    setBusy(true)
    try {
      if (['disable', 'delete', 'reset-daily-usage'].includes(action) && !await confirm({ title: t(`actions.${action}`), description: t('confirmUserAction'), tone: 'danger' })) return
      await apiRequest(`/admin/users/${encodeURIComponent(id)}${action === 'delete' ? '' : `/${action}`}`, { method: action === 'delete' ? 'DELETE' : 'POST', ...(body ? { body: JSON.stringify(body) } : {}) })
      toast.success(t('actionSuccess'))
      onSuccess(action === 'delete')
    } catch (err) { toast.error(errorMessage(err, errors)) } finally { setBusy(false) }
  }
  return { run, busy }
}
